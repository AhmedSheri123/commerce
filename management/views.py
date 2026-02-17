from django.shortcuts import redirect, render, get_object_or_404
from django.contrib.auth.models import User
from django.db.models import Q, Sum
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from django.contrib import messages
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from products.forms import PlatformForm, CategoryForm, ProductForm
from products.models import ProductModel, CategoryModel, PlatformModel
from accounts.models import (
    UserProfile,
    Transaction,
    Wallet,
    Deposit,
    SurveyQuestion,
    SurveyOption,
    UserSurveyAnswer,
    Notification,
)
from management.models import SupportContact
from products.models import UserProgress
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
        'products_profit_total': ProductModel.objects.aggregate(total=Sum('profit'))['total'] or 0,

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

def ViewUsers(request):
    users = User.objects.select_related(
        'profile',
        'wallet',
        'progress',
        'progress__product',
        'progress__product__category',
        'progress__product__category__platform',
    ).annotate(
        deposited_total=Sum('wallet__deposits__amount')
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
    progress = UserProgress.objects.select_related(
        'product',
        'product__category',
        'product__category__platform',
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
            product = form.cleaned_data['product']
            if progress:
                progress.product = product
                progress.save()
            else:
                UserProgress.objects.create(user=user, product=product)
            return redirect('management:user_analytics', user_id=user.id)
    else:
        if progress:
            form = UserProgressForm(initial={
                'platform': progress.product.category.platform,
                'category': progress.product.category,
                'product': progress.product,
            })
        else:
            form = UserProgressForm()

    return render(request, 'management/user/user_analytics.html', {
        'user_obj': user,
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

    profile.balance -= tx.amount
    profile.save()

    tx.status = 'approved'
    tx.processed_at = timezone.now()
    tx.save()
    messages.success(request, "تمت الموافقة على السحب.")
    return redirect('management:withdrawals')


@require_POST
def rejectWithdrawal(request, tx_id):
    tx = get_object_or_404(Transaction, id=tx_id, transaction_type='withdraw')
    if tx.status != 'pending':
        messages.info(request, "هذه العملية تمت معالجتها مسبقًا.")
        return redirect('management:withdrawals')

    tx.status = 'rejected'
    tx.processed_at = timezone.now()
    tx.save()
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

def ViewWallets(request):
    wallets = Wallet.objects.select_related('user').all()

    q = request.GET.get('q', '').strip()
    order = request.GET.get('order', '').strip()

    if q:
        wallets = wallets.filter(
            Q(user__username__icontains=q) |
            Q(user__email__icontains=q) |
            Q(address__icontains=q)
        )

    if order == 'oldest':
        wallets = wallets.order_by('created_at')
    else:
        wallets = wallets.order_by('-created_at')

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
    products = ProductModel.objects.filter(category_id=category_id).order_by('name')
    data = [{'id': p.id, 'name': p.name} for p in products]
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
