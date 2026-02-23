from django.shortcuts import redirect, render, get_object_or_404
from django.contrib.auth.models import User
from django.db.models import Q, Sum
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from django.contrib import messages
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from decimal import Decimal
from products.forms import PlatformForm, CategoryForm, ProductForm, ProductGroupForm
from products.models import ProductModel, CategoryModel, PlatformModel, ProductGroupModel
from accounts.models import (
    UserProfile,
    Transaction,
    SurveyQuestion,
    SurveyOption,
    UserSurveyAnswer,
    Notification,
)
from management.models import SupportContact
from products.models import UserProgress
from wallet.models import Wallet, Deposit, Relayer, MainWallet, WalletServiceSetting
from wallet.services import ensure_all_users_wallets, get_relayer_balance_snapshot, sweep_wallet_to_main
from .forms import (
    UserCreateForm,
    UserUpdateForm,
    UserProfileForm,
    UserProgressForm,
    SurveyQuestionForm,
    SurveyOptionForm,
    NotificationForm,
    SupportContactForm,
)
# Create your views here.

def index(request):
    users_qs = User.objects.all()
    withdrawals_qs = Transaction.objects.filter(transaction_type='withdraw')
    transfers_qs = Transaction.objects.filter(transaction_type='transfer')

    context = {
        'users_total': users_qs.count(),
        'users_active': users_qs.filter(is_active=True).count(),
        'users_verified': UserProfile.objects.filter(is_verified=True).count(),
        'users_subscribed': UserProgress.objects.count(),

        'platforms_total': PlatformModel.objects.count(),
        'categories_total': CategoryModel.objects.count(),
        'products_total': ProductModel.objects.count(),

        'wallets_total': Wallet.objects.count(),
        'wallets_balance_total': Wallet.objects.aggregate(total=Sum('balance'))['total'] or 0,
        'wallets_total_balance': Wallet.objects.aggregate(total=Sum('total_balance'))['total'] or 0,

        'deposits_total': Deposit.objects.count(),
        'deposits_amount_total': Deposit.objects.aggregate(total=Sum('amount'))['total'] or 0,
        'deposits_amount_confirmed': Deposit.objects.filter(status='confirmed').aggregate(total=Sum('amount'))['total'] or 0,
        'deposits_pending': Deposit.objects.filter(status='pending').count(),
        'deposits_rejected': Deposit.objects.filter(status='rejected').count(),

        'withdrawals_total': withdrawals_qs.count(),
        'withdrawals_amount_total': withdrawals_qs.aggregate(total=Sum('amount'))['total'] or 0,
        'withdrawals_pending': withdrawals_qs.filter(status='pending').count(),
        'withdrawals_approved': withdrawals_qs.filter(status='approved').count(),
        'withdrawals_rejected': withdrawals_qs.filter(status='rejected').count(),

        'transfers_total': transfers_qs.count(),
        'transfers_amount_total': transfers_qs.aggregate(total=Sum('amount'))['total'] or 0,

        'progress_earned_total': UserProgress.objects.aggregate(total=Sum('total_earned'))['total'] or 0,
        'products_price_total': ProductModel.objects.aggregate(total=Sum('price'))['total'] or 0,
        'products_profit_total': ProductGroupModel.objects.aggregate(total=Sum('profit'))['total'] or 0,

        'recent_users': users_qs.order_by('-date_joined')[:5],
        'recent_deposits': Deposit.objects.select_related('wallet', 'wallet__user').order_by('-created_at')[:5],
        'recent_withdrawals': withdrawals_qs.select_related('user').order_by('-created_at')[:5],
        'recent_transfers': transfers_qs.select_related('user', 'to_user').order_by('-created_at')[:5],
    }

    return render(request, 'management/index.html', context)


@login_required
def ViewNotifications(request):
    if not request.user.is_superuser:
        messages.error(request, "Only admin users can manage notifications.")
        return redirect("home:index")

    if request.method == "POST":
        form = NotificationForm(request.POST)
        if form.is_valid():
            notification = form.save(commit=False)
            notification.created_by = request.user
            if notification.target_all:
                notification.target_user = None
            notification.save()
            messages.success(request, "Notification created successfully.")
            return redirect("management:notifications")
    else:
        form = NotificationForm()

    notifications = Notification.objects.select_related("target_user", "created_by").all()
    return render(
        request,
        "management/notifications/index.html",
        {
            "form": form,
            "notifications": notifications,
        },
    )


@login_required
def ViewSupportContacts(request):
    if not request.user.is_superuser:
        messages.error(request, "Only admin users can manage support links.")
        return redirect("home:index")

    if request.method == "POST":
        form = SupportContactForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, "Support link added successfully.")
            return redirect("management:support_contacts")
    else:
        form = SupportContactForm()

    contacts = SupportContact.objects.all()
    return render(
        request,
        "management/support/contacts.html",
        {
            "form": form,
            "contacts": contacts,
        },
    )


@require_POST
@login_required
def toggleSupportContact(request, contact_id):
    if not request.user.is_superuser:
        messages.error(request, "Only admin users can manage support links.")
        return redirect("home:index")

    contact = get_object_or_404(SupportContact, id=contact_id)
    contact.is_active = not contact.is_active
    contact.save(update_fields=["is_active"])
    return redirect("management:support_contacts")


@require_POST
@login_required
def deleteSupportContact(request, contact_id):
    if not request.user.is_superuser:
        messages.error(request, "Only admin users can manage support links.")
        return redirect("home:index")

    contact = get_object_or_404(SupportContact, id=contact_id)
    contact.delete()
    return redirect("management:support_contacts")

def ViewPlateforms(request):
    plateforms = PlatformModel.objects.all()
    q = request.GET.get('q', '').strip()
    if q:
        plateforms = plateforms.filter(Q(name__icontains=q) | Q(description__icontains=q))
    return render(request, 'management/plateform/plateforms.html', {
        'plateforms': plateforms,
        'q': q,
    })

def addPlateform(request):
    if request.method == 'POST':
        form = PlatformForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect('management:platforms')
    else:
        form = PlatformForm()
    return render(request, 'management/plateform/add_plateform.html', {'form': form})

def editPlateform(request, plateform_id):
    plateform = PlatformModel.objects.get(id=plateform_id)
    if request.method == 'POST':
        form = PlatformForm(request.POST, request.FILES, instance=plateform)
        if form.is_valid():
            form.save()
            return redirect('management:platforms')
    else:
        form = PlatformForm(instance=plateform)
    return render(request, 'management/plateform/add_plateform.html', {'form': form, 'plateform': plateform})

def DeletePlateform(request, plateform_id):
    plateform = PlatformModel.objects.get(id=plateform_id)
    plateform.delete()
    return redirect('management:platforms')


#=======================================

def ViewCategories(request, plateform_id):
    categories = CategoryModel.objects.filter(platform__id=plateform_id)
    q = request.GET.get('q', '').strip()

    if q:
        categories = categories.filter(Q(name__icontains=q) | Q(platform__name__icontains=q))

    return render(request, 'management/category/categories.html', {
        'categories': categories,
        'plateform_id': plateform_id,
        'q': q,
    })

def addCategory(request, plateform_id):
    if request.method == 'POST':
        form = CategoryForm(request.POST, request.FILES, plateform_id=plateform_id)
        if form.is_valid():
            form.save()
            return redirect('management:categories', plateform_id)
    else:
        form = CategoryForm(plateform_id=plateform_id)
    return render(request, 'management/category/add_category.html', {'form': form})

def editCategory(request, category_id):
    plateform = CategoryModel.objects.get(id=category_id)
    if request.method == 'POST':
        form = CategoryForm(request.POST, request.FILES, instance=plateform)
        if form.is_valid():
            form.save()
            return redirect('management:categories', plateform.platform.id)
    else:
        form = CategoryForm(instance=plateform)
    return render(request, 'management/category/add_category.html', {'form': form, 'plateform': plateform})

def DeleteCategory(request, category_id):
    plateform = CategoryForm.objects.get(id=category_id)
    plateform_id = plateform.platform.id
    plateform.delete()
    return redirect('management:categories', plateform_id)


#=======================================

def ViewProducts(request, category_id):
    categories = ProductModel.objects.filter(category_id=category_id).order_by('stage')
    q = request.GET.get('q', '').strip()

    if q:
        categories = categories.filter(
            Q(name__icontains=q) |
            Q(category__name__icontains=q) |
            Q(category__platform__name__icontains=q)
        )

    return render(request, 'management/product/products.html', {
        'categories': categories,
        'category_id': category_id,
        'q': q,
    })

def addProduct(request, category_id):
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, category_id=category_id)
        if form.is_valid():
            form.save()
            return redirect('management:products', category_id)
    else:
        form = ProductForm(category_id=category_id)
    return render(request, 'management/product/add_product.html', {'form': form})

def editProduct(request, product_id):
    plateform = ProductModel.objects.get(id=product_id)
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, instance=plateform)
        if form.is_valid():
            form.save()
            return redirect('management:products', plateform.category.id)
    else:
        form = ProductForm(instance=plateform)
    return render(request, 'management/product/add_product.html', {'form': form, 'plateform': plateform})

def DeleteProduct(request, product_id):
    plateform = ProductModel.objects.get(id=product_id)
    plateform_id = plateform.category.id
    plateform.delete()
    return redirect('management:products', plateform_id)


#=======================================
def ViewProductGroups(request, category_id):
    category = get_object_or_404(CategoryModel, id=category_id)
    groups = ProductGroupModel.objects.filter(category_id=category_id).order_by('-created_at')
    q = request.GET.get('q', '').strip()

    if q:
        groups = groups.filter(Q(name__icontains=q) | Q(description__icontains=q))

    return render(request, 'management/group/groups.html', {
        'category': category,
        'groups': groups,
        'q': q,
    })


def addProductGroup(request, category_id):
    category = get_object_or_404(CategoryModel, id=category_id)
    products = ProductModel.objects.filter().order_by('name')
    suggestion = []
    suggested_total = None
    suggested_sell_total = None

    if request.method == 'POST':
        form = ProductGroupForm(request.POST)
        action = request.POST.get('action', 'preview')

        target_total = form.data.get('target_total_price')
        products_count = form.data.get('products_count')
        profit = form.data.get('profit')

        try:
            target_total_decimal = Decimal(str(target_total))
        except Exception:
            target_total_decimal = None
            form.add_error('target_total_price', 'Target total price is invalid.')

        try:
            products_count_int = int(products_count)
        except Exception:
            products_count_int = None
            form.add_error('products_count', 'Products count must be a valid integer.')

        try:
            profit_decimal = Decimal(str(profit))
        except Exception:
            profit_decimal = None
            form.add_error('profit', 'Profit is invalid.')

        if target_total_decimal is not None and target_total_decimal <= 0:
            form.add_error('target_total_price', 'Target total price must be greater than 0.')
        if products_count_int is not None and products_count_int <= 0:
            form.add_error('products_count', 'Products count must be greater than 0.')
        if profit_decimal is not None and profit_decimal < 0:
            form.add_error('profit', 'Profit must be 0 or greater.')

        if not form.errors:
            suggestion, suggested_total = ProductGroupModel.suggest_items_for_target(
                target_total=target_total_decimal,
                products_count=products_count_int,
            )
            if not suggestion:
                form.add_error(None, 'No suggestion found for this category.')
            else:
                suggested_sell_total = suggested_total + profit_decimal

        if action == 'save' and not form.errors and form.is_valid():
            group = form.save(commit=False)
            group.category = category
            if group.stage is None:
                group.stage = category.stage
            group.save()
            return redirect('management:product_groups', category_id=category.id)
    else:
        form = ProductGroupForm()

    return render(request, 'management/group/add_group.html', {
        'form': form,
        'category': category,
        'products': products,
        'suggestion': suggestion,
        'mode': 'add',
        'suggested_total': suggested_total,
        'suggested_sell_total': suggested_sell_total,
    })


def editProductGroup(request, category_id, group_id):
    category = get_object_or_404(CategoryModel, id=category_id)
    group = get_object_or_404(ProductGroupModel, id=group_id, category_id=category_id)
    products = ProductModel.objects.filter().order_by('name')
    suggestion = []
    suggested_total = None
    suggested_sell_total = None

    if request.method == 'POST':
        form = ProductGroupForm(request.POST, instance=group)
        action = request.POST.get('action', 'preview')

        target_total = form.data.get('target_total_price')
        products_count = form.data.get('products_count')
        profit = form.data.get('profit')

        try:
            target_total_decimal = Decimal(str(target_total))
        except Exception:
            target_total_decimal = None
            form.add_error('target_total_price', 'Target total price is invalid.')

        try:
            products_count_int = int(products_count)
        except Exception:
            products_count_int = None
            form.add_error('products_count', 'Products count must be a valid integer.')

        try:
            profit_decimal = Decimal(str(profit))
        except Exception:
            profit_decimal = None
            form.add_error('profit', 'Profit is invalid.')

        if target_total_decimal is not None and target_total_decimal <= 0:
            form.add_error('target_total_price', 'Target total price must be greater than 0.')
        if products_count_int is not None and products_count_int <= 0:
            form.add_error('products_count', 'Products count must be greater than 0.')
        if profit_decimal is not None and profit_decimal < 0:
            form.add_error('profit', 'Profit must be 0 or greater.')

        if not form.errors:
            suggestion, suggested_total = ProductGroupModel.suggest_items_for_target(
                target_total=target_total_decimal,
                products_count=products_count_int,
            )
            if not suggestion:
                form.add_error(None, 'No suggestion found for this category.')
            else:
                suggested_sell_total = suggested_total + profit_decimal

        if action == 'save' and not form.errors and form.is_valid():
            group = form.save(commit=False)
            group.category = category
            if group.stage is None:
                group.stage = category.stage
            group.save()
            return redirect('management:product_groups', category_id=category.id)
    else:
        form = ProductGroupForm(instance=group)
        if group.target_total_price and group.products_count:
            suggestion, suggested_total = ProductGroupModel.suggest_items_for_target(
                target_total=group.target_total_price,
                products_count=group.products_count,
            )
            suggested_sell_total = suggested_total + (group.profit or Decimal('0'))

    return render(request, 'management/group/add_group.html', {
        'form': form,
        'category': category,
        'group': group,
        'products': products,
        'mode': 'edit',
        'suggestion': suggestion,
        'suggested_total': suggested_total,
        'suggested_sell_total': suggested_sell_total,
    })

@require_POST
def deleteProductGroup(request, category_id, group_id):
    group = get_object_or_404(ProductGroupModel, id=group_id, category_id=category_id)
    group.delete()
    return redirect('management:product_groups', category_id=category_id)


#=======================================

def ViewUsers(request):
    users = User.objects.select_related(
        'profile',
        'progress',
        'progress__product_group',
        'progress__product_group__category',
        'progress__product_group__category__platform',
    ).annotate(
        deposited_total=Sum('wallets__deposits__amount')
    ).all()

    q = request.GET.get('q', '').strip()
    status = request.GET.get('status', '').strip()
    verified = request.GET.get('verified', '').strip()
    order = request.GET.get('order', '').strip()

    if q:
        users = users.filter(
            Q(username__icontains=q) |
            Q(email__icontains=q) |
            Q(first_name__icontains=q) |
            Q(last_name__icontains=q) |
            Q(profile__uid__icontains=q)
        )

    if status == 'active':
        users = users.filter(is_active=True)
    elif status == 'inactive':
        users = users.filter(is_active=False)

    if verified == 'yes':
        users = users.filter(profile__is_verified=True)
    elif verified == 'no':
        users = users.filter(profile__is_verified=False)

    if order == 'oldest':
        users = users.order_by('date_joined')
    else:
        users = users.order_by('-date_joined')

    return render(request, 'management/user/users.html', {
        'users': users,
        'q': q,
        'status': status,
        'verified': verified,
        'order': order,
    })


def addUser(request):
    if request.method == 'POST':
        user_form = UserCreateForm(request.POST)
        profile_form = UserProfileForm(request.POST)
        if user_form.is_valid() and profile_form.is_valid():
            user = user_form.save()
            profile = profile_form.save(commit=False)
            profile.user = user
            profile.save()
            return redirect('management:users')
    else:
        user_form = UserCreateForm()
        profile_form = UserProfileForm()

    return render(request, 'management/user/user_form.html', {
        'user_form': user_form,
        'profile_form': profile_form,
        'mode': 'add',
    })


def editUser(request, user_id):
    user = get_object_or_404(User, id=user_id)
    profile, _ = UserProfile.objects.get_or_create(user=user)

    if request.method == 'POST':
        user_form = UserUpdateForm(request.POST, instance=user)
        profile_form = UserProfileForm(request.POST, instance=profile)
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            return redirect('management:users')
    else:
        user_form = UserUpdateForm(instance=user)
        profile_form = UserProfileForm(instance=profile)

    return render(request, 'management/user/user_form.html', {
        'user_form': user_form,
        'profile_form': profile_form,
        'mode': 'edit',
        'user_obj': user,
    })


@require_POST
def deleteUser(request, user_id):
    user = get_object_or_404(User, id=user_id)
    user.delete()
    return redirect('management:users')


@require_POST
def toggleUserEnabled(request, user_id):
    user = get_object_or_404(User, id=user_id)
    profile, _ = UserProfile.objects.get_or_create(user=user)
    profile.is_enabled = not profile.is_enabled
    profile.save()
    return redirect('management:users')


def UserAnalytics(request, user_id):
    user = get_object_or_404(User, id=user_id)
    profile, _ = UserProfile.objects.get_or_create(user=user)
    progress = UserProgress.objects.select_related(
        'product_group',
        'product_group__category',
        'product_group__category__platform',
    ).filter(user=user).first()
    deposits = Deposit.objects.select_related('wallet').filter(wallet__user=user).order_by('-created_at')
    withdrawals = Transaction.objects.filter(user=user, transaction_type='withdraw').order_by('-created_at')
    survey_answers = UserSurveyAnswer.objects.select_related(
        'question',
        'option',
    ).filter(user=user).order_by('question__order', 'question__id')

    if request.method == 'POST':
        form = UserProgressForm(request.POST)
        if form.is_valid():
            product_group = form.cleaned_data['product_group']
            if progress:
                progress.product_group = product_group
                progress.save()
            else:
                UserProgress.objects.create(user=user, product_group=product_group)
            return redirect('management:user_analytics', user_id=user.id)
    else:
        if progress:
            form = UserProgressForm(initial={
                'platform': progress.product_group.category.platform,
                'category': progress.product_group.category,
                'product_group': progress.product_group,
            })
        else:
            form = UserProgressForm()

    return render(request, 'management/user/user_analytics.html', {
        'user_obj': user,
        'user_profile': profile,
        'progress': progress,
        'progress_form': form,
        'deposits': deposits,
        'withdrawals': withdrawals,
        'survey_answers': survey_answers,
    })


@require_POST
def deleteUserProgress(request, user_id):
    user = get_object_or_404(User, id=user_id)
    UserProgress.objects.filter(user=user).delete()
    return redirect('management:user_analytics', user_id=user.id)


#=======================================

def ViewWithdrawals(request):
    withdrawals = Transaction.objects.select_related('user').filter(transaction_type='withdraw')

    q = request.GET.get('q', '').strip()
    status = request.GET.get('status', '').strip()
    order = request.GET.get('order', '').strip()

    if q:
        withdrawals = withdrawals.filter(
            Q(user__username__icontains=q) |
            Q(user__email__icontains=q) |
            Q(wallet_address__icontains=q)
        )

    if status in {'pending', 'approved', 'rejected'}:
        withdrawals = withdrawals.filter(status=status)

    if order == 'oldest':
        withdrawals = withdrawals.order_by('created_at')
    else:
        withdrawals = withdrawals.order_by('-created_at')

    return render(request, 'management/transactions/withdrawals.html', {
        'withdrawals': withdrawals,
        'q': q,
        'status': status,
        'order': order,
    })


@require_POST
def approveWithdrawal(request, tx_id):
    tx = get_object_or_404(Transaction, id=tx_id, transaction_type='withdraw')
    if tx.status != 'pending':
        messages.info(request, "هذه العملية تمت معالجتها مسبقًا.")
        return redirect('management:withdrawals')

    profile = tx.user.profile
    if profile.balance < tx.amount:
        messages.error(request, "الرصيد غير كافٍ لاعتماد السحب.")
        return redirect('management:withdrawals')

    profile.disable_ordering_unitl_withdrawal = False
    profile.has_withdrawn = True
    profile.save()

    tx.status = 'approved'
    tx.processed_at = timezone.now()
    tx.save()
    messages.success(request, "تمت الموافقة على السحب.")
    return redirect('management:withdrawals')


@require_POST
def rejectWithdrawal(request, tx_id):
    tx = get_object_or_404(Transaction, id=tx_id, transaction_type='withdraw')
    profile = tx.user.profile
    if tx.status != 'pending':
        messages.info(request, "هذه العملية تمت معالجتها مسبقًا.")
        return redirect('management:withdrawals')

    tx.status = 'rejected'
    tx.processed_at = timezone.now()
    tx.save()
    profile.balance += tx.amount
    profile.save()
    messages.success(request, "تم رفض السحب.")
    return redirect('management:withdrawals')


def ViewTransfers(request):
    transfers = Transaction.objects.select_related('user', 'to_user').filter(transaction_type='transfer')

    q = request.GET.get('q', '').strip()
    order = request.GET.get('order', '').strip()

    if q:
        transfers = transfers.filter(
            Q(user__username__icontains=q) |
            Q(user__email__icontains=q) |
            Q(to_user__username__icontains=q)
        )

    if order == 'oldest':
        transfers = transfers.order_by('created_at')
    else:
        transfers = transfers.order_by('-created_at')

    return render(request, 'management/transactions/transfers.html', {
        'transfers': transfers,
        'q': q,
        'order': order,
    })


#=======================================

@login_required
def ViewWalletRelayerSettings(request):
    if not request.user.is_superuser:
        messages.error(request, "Only admin users can manage relayer settings.")
        return redirect("home:index")

    supported_networks = [Wallet.Network.TRON, Wallet.Network.BEP20]
    relayers = {}
    main_wallets = {}
    for network in supported_networks:
        relayer, _ = Relayer.objects.get_or_create(network=network)
        relayers[network] = relayer
        main_wallet, _ = MainWallet.objects.get_or_create(network=network)
        main_wallets[network] = main_wallet
    service_settings = WalletServiceSetting.get_solo()

    if request.method == "POST":
        config_type = (request.POST.get("config_type") or "relayer").strip().lower()
        network = (request.POST.get("network") or "").strip().lower()
        if config_type != "service_settings" and network not in supported_networks:
            messages.error(request, "Invalid wallet network.")
            return redirect("management:wallet_settings")

        if config_type == "service_settings":
            tron_endpoint_uri = (request.POST.get("tron_endpoint_uri") or "").strip()
            tron_usdt_contract = (request.POST.get("tron_usdt_contract") or "").strip()
            tron_usdt_decimals_raw = (request.POST.get("tron_usdt_decimals") or "").strip()
            bep20_usdt_contract = (request.POST.get("bep20_usdt_contract") or "").strip()
            bep20_rpc_url = (request.POST.get("bep20_rpc_url") or "").strip()
            fallback_bep20_rpc_url = (request.POST.get("fallback_bep20_rpc_url") or "").strip()
            bep20_rpc_fallback_urls = (request.POST.get("bep20_rpc_fallback_urls") or "").strip()
            bscscan_api_url = (request.POST.get("bscscan_api_url") or "").strip()
            bscscan_v2_api_url = (request.POST.get("bscscan_v2_api_url") or "").strip()
            bscscan_api_key = (request.POST.get("bscscan_api_key") or "").strip()
            deposit_source = (request.POST.get("bep20_deposit_source") or "").strip().lower()

            tron_timeout_raw = (request.POST.get("tron_api_timeout_seconds") or "").strip()
            bep20_decimals_raw = (request.POST.get("bep20_usdt_decimals") or "").strip()
            chain_id_raw = (request.POST.get("bep20_explorer_chain_id") or "").strip()
            bep20_rpc_timeout_raw = (request.POST.get("bep20_rpc_timeout_seconds") or "").strip()
            lookback_raw = (request.POST.get("bep20_autocheck_lookback_blocks") or "").strip()
            initial_raw = (request.POST.get("bep20_initial_lookback_blocks") or "").strip()
            chunk_raw = (request.POST.get("bep20_autocheck_chunk_size") or "").strip()
            reserve_raw = (request.POST.get("bep20_relayer_reserve_bnb") or "").strip()
            topup_receipt_timeout_raw = (request.POST.get("bep20_topup_receipt_timeout_seconds") or "").strip()
            sweep_receipt_timeout_raw = (request.POST.get("bep20_sweep_receipt_timeout_seconds") or "").strip()
            explorer_timeout_raw = (request.POST.get("explorer_timeout_seconds") or "").strip()
            offset_raw = (request.POST.get("bep20_bscscan_offset") or "").strip()
            pages_raw = (request.POST.get("bep20_bscscan_max_pages") or "").strip()

            errors = []
            try:
                tron_usdt_decimals = int(tron_usdt_decimals_raw)
            except Exception:
                tron_usdt_decimals = None
                errors.append("TRON USDT decimals must be an integer.")

            try:
                tron_api_timeout_seconds = int(tron_timeout_raw)
            except Exception:
                tron_api_timeout_seconds = None
                errors.append("TRON API timeout must be an integer.")

            try:
                bep20_usdt_decimals = int(bep20_decimals_raw)
            except Exception:
                bep20_usdt_decimals = None
                errors.append("BEP20 USDT decimals must be an integer.")

            try:
                bep20_explorer_chain_id = int(chain_id_raw)
            except Exception:
                bep20_explorer_chain_id = None
                errors.append("BEP20 explorer chain ID must be an integer.")

            try:
                bep20_rpc_timeout_seconds = int(bep20_rpc_timeout_raw)
            except Exception:
                bep20_rpc_timeout_seconds = None
                errors.append("BEP20 RPC timeout must be an integer.")

            try:
                lookback_blocks = int(lookback_raw)
            except Exception:
                lookback_blocks = None
                errors.append("Auto-check lookback blocks must be an integer.")

            try:
                initial_blocks = int(initial_raw)
            except Exception:
                initial_blocks = None
                errors.append("Initial lookback blocks must be an integer.")

            try:
                chunk_size = int(chunk_raw)
            except Exception:
                chunk_size = None
                errors.append("Auto-check chunk size must be an integer.")

            try:
                reserve_bnb = Decimal(reserve_raw)
            except Exception:
                reserve_bnb = None
                errors.append("Relayer reserve (BNB) must be a valid number.")

            try:
                bep20_topup_receipt_timeout_seconds = int(topup_receipt_timeout_raw)
            except Exception:
                bep20_topup_receipt_timeout_seconds = None
                errors.append("BEP20 top-up receipt timeout must be an integer.")

            try:
                bep20_sweep_receipt_timeout_seconds = int(sweep_receipt_timeout_raw)
            except Exception:
                bep20_sweep_receipt_timeout_seconds = None
                errors.append("BEP20 sweep receipt timeout must be an integer.")

            try:
                explorer_timeout_seconds = int(explorer_timeout_raw)
            except Exception:
                explorer_timeout_seconds = None
                errors.append("Explorer timeout must be an integer.")

            try:
                bscscan_offset = int(offset_raw)
            except Exception:
                bscscan_offset = None
                errors.append("BscScan offset must be an integer.")

            try:
                bscscan_max_pages = int(pages_raw)
            except Exception:
                bscscan_max_pages = None
                errors.append("BscScan max pages must be an integer.")

            if not tron_endpoint_uri:
                errors.append("TRON endpoint URI cannot be empty.")
            if not tron_usdt_contract:
                errors.append("TRON USDT contract cannot be empty.")
            if tron_usdt_decimals is not None and tron_usdt_decimals <= 0:
                errors.append("TRON USDT decimals must be greater than 0.")
            if not bep20_usdt_contract:
                errors.append("BEP20 USDT contract cannot be empty.")
            if tron_api_timeout_seconds is not None and tron_api_timeout_seconds <= 0:
                errors.append("TRON API timeout must be greater than 0.")
            if bep20_usdt_decimals is not None and bep20_usdt_decimals <= 0:
                errors.append("BEP20 USDT decimals must be greater than 0.")
            if bep20_explorer_chain_id is not None and bep20_explorer_chain_id <= 0:
                errors.append("BEP20 explorer chain ID must be greater than 0.")
            if bep20_rpc_timeout_seconds is not None and bep20_rpc_timeout_seconds <= 0:
                errors.append("BEP20 RPC timeout must be greater than 0.")
            if lookback_blocks is not None and lookback_blocks <= 0:
                errors.append("Auto-check lookback blocks must be greater than 0.")
            if initial_blocks is not None and initial_blocks <= 0:
                errors.append("Initial lookback blocks must be greater than 0.")
            if chunk_size is not None and chunk_size <= 0:
                errors.append("Auto-check chunk size must be greater than 0.")
            if reserve_bnb is not None and reserve_bnb < 0:
                errors.append("Relayer reserve (BNB) cannot be negative.")
            if bep20_topup_receipt_timeout_seconds is not None and bep20_topup_receipt_timeout_seconds <= 0:
                errors.append("BEP20 top-up receipt timeout must be greater than 0.")
            if bep20_sweep_receipt_timeout_seconds is not None and bep20_sweep_receipt_timeout_seconds <= 0:
                errors.append("BEP20 sweep receipt timeout must be greater than 0.")
            if explorer_timeout_seconds is not None and explorer_timeout_seconds <= 0:
                errors.append("Explorer timeout must be greater than 0.")
            if bscscan_offset is not None and bscscan_offset <= 0:
                errors.append("BscScan offset must be greater than 0.")
            if bscscan_max_pages is not None and bscscan_max_pages <= 0:
                errors.append("BscScan max pages must be greater than 0.")
            if deposit_source not in {"auto", "rpc", "bscscan"}:
                errors.append("Deposit source must be one of: auto, rpc, bscscan.")
            if not bscscan_api_url:
                errors.append("BscScan API URL cannot be empty.")
            if not bscscan_v2_api_url:
                errors.append("BscScan V2 API URL cannot be empty.")

            if errors:
                messages.error(request, " ".join(errors))
                return redirect("management:wallet_settings")

            service_settings.tron_endpoint_uri = tron_endpoint_uri
            service_settings.tron_usdt_contract = tron_usdt_contract
            service_settings.tron_usdt_decimals = tron_usdt_decimals
            service_settings.tron_api_timeout_seconds = tron_api_timeout_seconds
            service_settings.bep20_usdt_contract = bep20_usdt_contract
            service_settings.bep20_usdt_decimals = bep20_usdt_decimals
            service_settings.bep20_explorer_chain_id = bep20_explorer_chain_id
            service_settings.bep20_rpc_url = bep20_rpc_url
            service_settings.fallback_bep20_rpc_url = fallback_bep20_rpc_url
            service_settings.bep20_rpc_fallback_urls = bep20_rpc_fallback_urls
            service_settings.bep20_rpc_timeout_seconds = bep20_rpc_timeout_seconds
            service_settings.bep20_autocheck_lookback_blocks = lookback_blocks
            service_settings.bep20_initial_lookback_blocks = initial_blocks
            service_settings.bep20_autocheck_chunk_size = chunk_size
            service_settings.bep20_relayer_reserve_bnb = reserve_bnb
            service_settings.bep20_topup_receipt_timeout_seconds = bep20_topup_receipt_timeout_seconds
            service_settings.bep20_sweep_receipt_timeout_seconds = bep20_sweep_receipt_timeout_seconds
            service_settings.bscscan_api_url = bscscan_api_url
            service_settings.bscscan_v2_api_url = bscscan_v2_api_url
            service_settings.bscscan_api_key = bscscan_api_key
            service_settings.explorer_timeout_seconds = explorer_timeout_seconds
            service_settings.bep20_deposit_source = deposit_source
            service_settings.bep20_bscscan_offset = bscscan_offset
            service_settings.bep20_bscscan_max_pages = bscscan_max_pages
            service_settings.save()

            messages.success(request, "BEP20 service settings updated.")
            return redirect("management:wallet_settings")

        if config_type == "main_wallet":
            main_wallet = main_wallets[network]
            address = (request.POST.get("address") or "").strip()
            private_key = (request.POST.get("private_key") or "").strip()
            is_enabled = request.POST.get("is_enabled") == "on"

            main_wallet.address = address
            if private_key:
                main_wallet.private_key = private_key
            main_wallet.is_enabled = is_enabled
            main_wallet.save()

            messages.success(request, f"{main_wallet.get_network_display()} main wallet settings updated.")
            return redirect("management:wallet_settings")

        relayer = relayers[network]
        address = (request.POST.get("address") or "").strip()
        private_key = (request.POST.get("private_key") or "").strip()
        trongrid_api_key = (request.POST.get("trongrid_api_key") or "").strip()
        min_native_raw = (request.POST.get("min_native_balance") or "").strip()
        topup_raw = (request.POST.get("topup_amount") or "").strip()
        is_enabled = request.POST.get("is_enabled") == "on"

        errors = []
        try:
            min_native_balance = Decimal(min_native_raw)
        except Exception:
            min_native_balance = None
            errors.append("Min native balance must be a valid number.")

        try:
            topup_amount = Decimal(topup_raw)
        except Exception:
            topup_amount = None
            errors.append("Top-up amount must be a valid number.")

        if min_native_balance is not None and min_native_balance < 0:
            errors.append("Min native balance cannot be negative.")
        if topup_amount is not None and topup_amount <= 0:
            errors.append("Top-up amount must be greater than zero.")

        if errors:
            messages.error(request, " ".join(errors))
            return redirect("management:wallet_settings")

        relayer.address = address
        if private_key:
            relayer.private_key = private_key
        if network == Wallet.Network.TRON:
            relayer.trongrid_api_key = trongrid_api_key
        relayer.min_native_balance = min_native_balance
        relayer.topup_amount = topup_amount
        relayer.is_enabled = is_enabled
        relayer.save()

        messages.success(request, f"{relayer.get_network_display()} relayer settings updated.")
        return redirect("management:wallet_settings")

    return render(
        request,
        "management/wallets/settings.html",
        {
            "tron_relayer": relayers[Wallet.Network.TRON],
            "bep20_relayer": relayers[Wallet.Network.BEP20],
            "tron_main_wallet": main_wallets[Wallet.Network.TRON],
            "bep20_main_wallet": main_wallets[Wallet.Network.BEP20],
            "service_settings": service_settings,
            "deposit_source_choices": WalletServiceSetting.DepositSource.choices,
        },
    )


@login_required
def WalletRelayerBalancesApi(request):
    if not request.user.is_superuser:
        return JsonResponse({"ok": False, "message": "Forbidden."}, status=403)

    balances = {}
    for network in (Wallet.Network.TRON, Wallet.Network.BEP20):
        balances[network] = get_relayer_balance_snapshot(network)

    return JsonResponse({"ok": True, "balances": balances})


#=======================================

def ViewWallets(request):
    if request.method == "POST":
        wallet_id = request.POST.get("wallet_id")
        if wallet_id:
            wallet = get_object_or_404(Wallet, id=wallet_id)
            result = sweep_wallet_to_main(wallet)
            if result.get("ok"):
                messages.success(request, result.get("message", "Sweep completed successfully."))
            else:
                messages.error(request, result.get("message", "Sweep failed."))
            return redirect("management:wallets")

        generated = ensure_all_users_wallets()
        messages.success(
            request,
            f"Wallet sync completed. Users scanned: {generated['users']}, new wallets created: {generated['created_wallets']}.",
        )
        return redirect("management:wallets")

    wallets = Wallet.objects.select_related('user').all()

    q = request.GET.get('q', '').strip()
    order = request.GET.get('order', '').strip()

    if q:
        wallets = wallets.filter(
            Q(user__username__icontains=q) |
            Q(user__email__icontains=q) |
            Q(address__icontains=q) |
            Q(network__icontains=q)
        )

    if order == 'oldest':
        wallets = wallets.order_by('created_at', 'network')
    else:
        wallets = wallets.order_by('-created_at', 'network')

    return render(request, 'management/wallets/wallets.html', {
        'wallets': wallets,
        'q': q,
        'order': order,
    })


def ViewWalletDeposits(request, wallet_id):
    wallet = get_object_or_404(Wallet, id=wallet_id)
    deposits = wallet.deposits.all().order_by('-created_at')

    status = request.GET.get('status', '').strip()
    if status in {'pending', 'confirmed', 'rejected'}:
        deposits = deposits.filter(status=status)

    return render(request, 'management/wallets/wallet_deposits.html', {
        'wallet': wallet,
        'deposits': deposits,
        'status': status,
    })


def ViewDeposits(request):
    deposits = Deposit.objects.select_related('wallet', 'wallet__user').all()

    q = request.GET.get('q', '').strip()
    status = request.GET.get('status', '').strip()
    order = request.GET.get('order', '').strip()

    if q:
        deposits = deposits.filter(
            Q(wallet__user__username__icontains=q) |
            Q(wallet__user__email__icontains=q) |
            Q(wallet__address__icontains=q) |
            Q(txid__icontains=q)
        )

    if status in {'pending', 'confirmed', 'rejected'}:
        deposits = deposits.filter(status=status)

    if order == 'oldest':
        deposits = deposits.order_by('created_at')
    else:
        deposits = deposits.order_by('-created_at')

    return render(request, 'management/wallets/deposits.html', {
        'deposits': deposits,
        'q': q,
        'status': status,
        'order': order,
    })


#=======================================

def api_categories_by_platform(request, platform_id):
    categories = CategoryModel.objects.filter(platform_id=platform_id).order_by('name')
    data = [{'id': c.id, 'name': c.name} for c in categories]
    return JsonResponse({'categories': data})


def api_products_by_category(request, category_id):
    groups = ProductGroupModel.objects.filter(category_id=category_id).order_by('stage', 'id')
    data = [{'id': g.id, 'name': g.name or f'Group {g.stage if g.stage is not None else g.id}'} for g in groups]
    return JsonResponse({'products': data})


#=======================================

def ViewSurveyQuestions(request):
    questions = SurveyQuestion.objects.all().order_by('order', 'id')
    return render(request, 'management/survey/questions.html', {'questions': questions})


def addSurveyQuestion(request):
    if request.method == 'POST':
        form = SurveyQuestionForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('management:survey_questions')
    else:
        form = SurveyQuestionForm()
    return render(request, 'management/survey/question_form.html', {'form': form, 'mode': 'add'})


def editSurveyQuestion(request, question_id):
    question = get_object_or_404(SurveyQuestion, id=question_id)
    if request.method == 'POST':
        form = SurveyQuestionForm(request.POST, instance=question)
        if form.is_valid():
            form.save()
            return redirect('management:survey_questions')
    else:
        form = SurveyQuestionForm(instance=question)
    return render(request, 'management/survey/question_form.html', {'form': form, 'mode': 'edit', 'question': question})


@require_POST
def deleteSurveyQuestion(request, question_id):
    question = get_object_or_404(SurveyQuestion, id=question_id)
    question.delete()
    return redirect('management:survey_questions')


def ViewSurveyOptions(request, question_id):
    question = get_object_or_404(SurveyQuestion, id=question_id)
    options = question.options.all().order_by('order', 'id')
    return render(request, 'management/survey/options.html', {'question': question, 'options': options})


def addSurveyOption(request, question_id):
    question = get_object_or_404(SurveyQuestion, id=question_id)
    if request.method == 'POST':
        form = SurveyOptionForm(request.POST)
        if form.is_valid():
            option = form.save(commit=False)
            option.question = question
            option.save()
            return redirect('management:survey_options', question_id=question.id)
    else:
        form = SurveyOptionForm()
    return render(request, 'management/survey/option_form.html', {'form': form, 'mode': 'add', 'question': question})


def editSurveyOption(request, option_id):
    option = get_object_or_404(SurveyOption, id=option_id)
    if request.method == 'POST':
        form = SurveyOptionForm(request.POST, instance=option)
        if form.is_valid():
            form.save()
            return redirect('management:survey_options', question_id=option.question.id)
    else:
        form = SurveyOptionForm(instance=option)
    return render(request, 'management/survey/option_form.html', {'form': form, 'mode': 'edit', 'question': option.question})


@require_POST
def deleteSurveyOption(request, option_id):
    option = get_object_or_404(SurveyOption, id=option_id)
    question_id = option.question.id
    option.delete()
    return redirect('management:survey_options', question_id=question_id)
