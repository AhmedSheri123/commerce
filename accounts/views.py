from decimal import Decimal
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.models import User

from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from django.utils import timezone
from django.shortcuts import get_object_or_404
import qrcode
import base64
from io import BytesIO
import json
from .models import (
    ReferralBonus,
    UserProfile,
    SurveyQuestion,
    SurveyOption,
    UserSurveyAnswer,
    Notification,
    NotificationRead,
    ActiveUsersCounter,
)
from accounts.models import Transaction, Wallet, Deposit
from django.db import models
from .wallet import transfer_to_master, USDT_CONTRACT
import requests
from management.models import SupportContact
# Create your views here.

@login_required
def index(request):
    notifications_qs = Notification.objects.filter(is_active=True).filter(
        models.Q(target_all=True) | models.Q(target_user=request.user)
    )
    unread_count = notifications_qs.exclude(read_events__user=request.user).count()

    return render(
        request,
        "dashboard/accounts/index.html",
        {
            "unread_count": unread_count,
        },
    )


@login_required
def notifications_page(request):
    notifications_qs = Notification.objects.filter(is_active=True).filter(
        models.Q(target_all=True) | models.Q(target_user=request.user)
    ).order_by("-created_at")

    read_ids = set(
        NotificationRead.objects.filter(
            user=request.user,
            notification__in=notifications_qs,
        ).values_list("notification_id", flat=True)
    )

    notifications = [
        {
            "obj": item,
            "is_read": item.id in read_ids,
        }
        for item in notifications_qs
    ]
    unread_count = sum(1 for n in notifications if not n["is_read"])

    return render(
        request,
        "dashboard/accounts/notifications.html",
        {
            "notifications": notifications,
            "unread_count": unread_count,
        },
    )


@login_required
def support_page(request):
    contacts = SupportContact.objects.filter(is_active=True).order_by("order", "id")
    return render(
        request,
        "dashboard/accounts/support.html",
        {
            "contacts": contacts,
        },
    )

def Login(request):
    if request.user.is_authenticated:
        return redirect('home:index')
    next_page = request.GET.get('next', None)
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            if not _survey_completed(user):
                return redirect('accounts:survey')
            if next_page:
                return redirect(next_page)
            return redirect('home:index')
        else:
            # If authentication fails, return an error message
            messages.error(request, 'Invalid username or password')
            return redirect('accounts:login')

    return render(request, 'dashboard/accounts/login.html')

def signup(request):
    if request.user.is_authenticated:
        return redirect('home:index')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        invite_code = request.POST.get('invite_code')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')
        referrer_profiles = UserProfile.objects.filter(invite_code=invite_code)

        if password != confirm_password:
            messages.error(request, 'كلمات المرور غير متطابقة')
            return redirect('accounts:signup')
        
        # Check if the invite code is valid (this is a simplified check)
        if not referrer_profiles.exists():
            messages.error(request, 'Invalid invite code')
            return redirect('accounts:signup')
        
        # Check if the username is already taken
        if User.objects.filter(username=username).exists():
            messages.error(request, 'اسم المستخدم مستخدم بالفعل')
            return redirect('accounts:signup')
        
        # Create the user (in a real app, you'd use User.objects.create_user())
        user = User.objects.create_user(username=username, password=password)
        user.save()

        referrer_profile = referrer_profiles.first()
        user.profile.referred_by = referrer_profile.user
        

        if referrer_profile.user.profile.is_verified:
            referrer_profile.invite_code = referrer_profile.get_new_invite_code
            referrer_profile.save()
            user.profile.from_verified_source = True

        user.profile.save()
        # For simplicity, we will just redirect to login after "signup"
        messages.success(request, 'تم إنشاء الحساب بنجاح. يرجى تسجيل الدخول.')
        return redirect('accounts:login')
    return render(request, 'dashboard/accounts/signup.html')


def Logout(request):
    logout(request)
    return redirect('accounts:login')


def _survey_completed(user):
    required_questions = SurveyQuestion.objects.filter(is_active=True, is_required=True)
    if not required_questions.exists():
        return True
    for q in required_questions:
        has_answer = UserSurveyAnswer.objects.filter(user=user, question=q).exists()
        if not has_answer:
            return False
    return True


@login_required
def survey(request):
    questions = SurveyQuestion.objects.filter(is_active=True).prefetch_related('options').order_by('order', 'id')
    errors = {}

    if request.method == 'POST':
        # حذف إجابات المستخدم السابقة للأسئلة النشطة
        UserSurveyAnswer.objects.filter(user=request.user, question__in=questions).delete()

        for q in questions:
            field_name = f"q_{q.id}"
            if q.field_type == 'multi':
                values = request.POST.getlist(field_name)
                if q.is_required and not values:
                    errors[q.id] = "هذا السؤال مطلوب."
                    continue
                for val in values:
                    option = SurveyOption.objects.filter(id=val, question=q).first()
                    if option:
                        UserSurveyAnswer.objects.create(user=request.user, question=q, option=option)
            elif q.field_type == 'single':
                val = request.POST.get(field_name, '').strip()
                if q.is_required and not val:
                    errors[q.id] = "هذا السؤال مطلوب."
                    continue
                option = SurveyOption.objects.filter(id=val, question=q).first()
                if option:
                    UserSurveyAnswer.objects.create(user=request.user, question=q, option=option)
            elif q.field_type == 'boolean':
                val = request.POST.get(field_name, '').strip()
                if q.is_required and val == '':
                    errors[q.id] = "هذا السؤال مطلوب."
                    continue
                if val in ['yes', 'no']:
                    UserSurveyAnswer.objects.create(
                        user=request.user,
                        question=q,
                        bool_answer=True if val == 'yes' else False
                    )
            elif q.field_type == 'number':
                val = request.POST.get(field_name, '').strip()
                if q.is_required and val == '':
                    errors[q.id] = "هذا السؤال مطلوب."
                    continue
                if val:
                    UserSurveyAnswer.objects.create(user=request.user, question=q, number_answer=val)
            else:  # text
                val = request.POST.get(field_name, '').strip()
                if q.is_required and not val:
                    errors[q.id] = "هذا السؤال مطلوب."
                    continue
                if val:
                    UserSurveyAnswer.objects.create(user=request.user, question=q, text_answer=val)

        if not errors:
            next_url = request.GET.get('next') or 'home:index'
            return redirect(next_url)

    return render(request, 'dashboard/accounts/survey.html', {
        'questions': questions,
        'errors': errors,
    })

@login_required
def change_password(request):
    if not request.user.is_authenticated:
        return redirect('accounts:login')
    
    if request.method == 'POST':
        old_password = request.POST.get('old_password')
        new_password = request.POST.get('new_password')
        confirm_new_password = request.POST.get('confirm_new_password')
        
        if not request.user.check_password(old_password):
            messages.error(request, 'كلمة المرور القديمة غير صحيحة')
            return redirect('accounts:profile')
        
        if new_password != confirm_new_password:
            messages.error(request, 'كلمات المرور الجديدة لا تتطابق')
            return redirect('accounts:profile')
        
        request.user.set_password(new_password)
        request.user.save()
        messages.success(request, 'تم تغيير كلمة المرور بنجاح')
        return redirect('accounts:login')
    
    return redirect('accounts:profile')


@login_required
@require_POST
def mark_notification_read(request, notification_id):
    notification = get_object_or_404(Notification, id=notification_id, is_active=True)

    if not notification.target_all and notification.target_user_id != request.user.id:
        messages.error(request, "You cannot read this notification.")
        return redirect("accounts:profile")

    NotificationRead.objects.get_or_create(notification=notification, user=request.user)

    next_url = request.POST.get("next") or "accounts:notifications"
    return redirect(next_url)


@login_required
def active_users_count_api(request):
    return JsonResponse({"count": ActiveUsersCounter.get_next_value()})



















@login_required
def transactions(request):
    user = request.user
    user_progress = user.progress if hasattr(user, 'progress') else None
    transactions = user.transactions.all().order_by('-created_at')
    

    if request.method == 'POST':
        action = request.POST.get('action')
        amount = Decimal(request.POST.get('amount', '0'))
        
        if action == 'withdraw':
            wallet_address = request.POST.get('wallet_address', '').strip()
            if user_progress:
                if user_progress.is_done:
                    if amount > 0 and wallet_address:
                        if user.profile.balance >= amount:  # تحقق من الرصيد
                            # إنشاء طلب سحب جديد (معلق)
                            Transaction.objects.create(
                                user=user,
                                transaction_type='withdraw',
                                amount=amount,
                                wallet_address=wallet_address,
                                status='pending'
                            )
                            messages.success(request, f"تم تقديم طلب سحب {amount} USDT، في انتظار الموافقة")
                        else:
                            messages.error(request, "الرصيد غير كافٍ")
                    else:
                        messages.error(request, "الرجاء إدخال المبلغ وعنوان المحفظة بشكل صحيح")
                else:
                    messages.error(request, "يرجى اكمال المهمات الموجودة لتتمكن من السحب")
        elif action == 'transfer':
            recipient_username = request.POST.get('recipient')
            try:
                recipient = User.objects.get(username=recipient_username)
                if recipient != user:
                    if amount > 0 and user.profile.balance >= amount:
                        # تحويل داخلي مباشر
                        Transaction.objects.create(
                            user=user,
                            transaction_type='transfer',
                            amount=amount,
                            to_user=recipient,
                            status='approved'
                        )
                        # تحديث الأرصدة
                        user.profile.balance -= amount
                        recipient.profile.balance += amount
                        user.profile.save()
                        recipient.profile.save()
                        messages.success(request, f"تم تحويل {amount} USDT إلى {recipient.username}")
                    else:
                        messages.error(request, "الرصيد غير كافٍ أو المبلغ غير صحيح")
                else:messages.error(request, "المستخدم المستلم غير موجود")
            except User.DoesNotExist:
                messages.error(request, "المستخدم المستلم غير موجود")

    context = {
        "transactions": transactions,
        "balance": user.profile.balance,
    }
    return render(request, "dashboard/accounts/transactions/transactions.html", context)



@login_required
def referral_dashboard(request):
    # استدعاء الملف الشخصي للمستخدم
    profile = request.user.profile

    # جميع المكافآت الخاصة بالمستخدم
    referral_bonuses = ReferralBonus.objects.filter(referrer=request.user).order_by('-created_at')

    # إجمالي المكافآت المكتسبة
    total_bonus = referral_bonuses.aggregate(total=models.Sum('amount'))['total'] or 0

    # عدد الدعوات
    total_referrals = referral_bonuses.count()

    context = {
        'profile': profile,
        'referral_bonuses': referral_bonuses,
        'total_bonus': total_bonus,
        'total_referrals': total_referrals,
    }

    return render(request, 'dashboard/accounts/transactions/ReferralBonus.html', context)


@login_required
def check_deposits(wallet, request):
    try:
        url = f"https://api.trongrid.io/v1/accounts/{wallet.address}/transactions/trc20"
        resp = requests.get(url).json()
    except Exception as e:
        print(f"خطأ عند جلب المعاملات: {e}")
        return

    for tx in resp.get("data", []):
        try:
            to_address = tx.get("to")
            token_address = tx.get("token_info", {}).get("address")
            if to_address != wallet.address or token_address != USDT_CONTRACT:
                continue

            txid = tx["transaction_id"]
            amount = Decimal(tx["value"]) / Decimal(10**6)

            deposit, created = Deposit.objects.get_or_create(
                wallet=wallet,
                txid=txid,
                defaults={"amount": amount, "status": "confirmed"}
            )

            if created:
                print(f"إيداع جديد: {amount} USDT")

                wallet.user.profile.balance += amount
                wallet.user.profile.save()

                wallet.balance += amount
                wallet.save()

                referrer_user = wallet.user.profile.referred_by
                if referrer_user:
                    try:
                        referral_bonus = ReferralBonus.objects.get(
                            referrer=referrer_user,
                            referred_user=wallet.user
                        )
                        bonus_amount = amount * Decimal('0.05')
                        referral_bonus.amount += bonus_amount
                        referral_bonus.save()

                        referrer_user.profile.balance += bonus_amount
                        referrer_user.profile.save()
                    except ReferralBonus.DoesNotExist:
                        pass

                messages.success(request, f"تم الإيداع بنجاح. الرصيد الحالي: {amount} USDT")
        except Exception as e:
            print(f"خطأ في معالجة المعاملة: {e}")


@login_required
def deposit_view(request):
    wallet = request.user.wallet
    deposits = wallet.deposits.all()

    # توليد QR code
    qr = qrcode.make(wallet.address)
    buffer = BytesIO()
    qr.save(buffer, format="PNG")
    qr_base64 = base64.b64encode(buffer.getvalue()).decode()
    check_deposits(wallet, request)
    return render(request, "dashboard/accounts/transactions/deposit.html", {
        "wallet": wallet,
        "deposits": deposits,
        "qr_code": qr_base64,
    })


@login_required
@csrf_exempt
def tron_webhook(request):
    if request.method == "POST":
        data = json.loads(request.body)

        # مثال لبيانات مرسلة من المزود
        tx_id = data.get("txID")
        to_address = data.get("to")
        from_address = data.get("from")
        amount = Decimal(data.get("amount", "0"))
        token = data.get("token", "").upper()

        # نتأكد أنه USDT و العملية تخص عنوان مستخدم
        if token == "USDT":
            try:
                wallet = Wallet.objects.get(address=to_address)

                # نتأكد أن الإيداع غير مسجل من قبل
                if not Deposit.objects.filter(wallet=wallet, amount=amount, status="confirmed").exists():
                    Deposit.objects.create(
                        wallet=wallet,
                        amount=amount,
                        status="confirmed",
                        confirmed_at=timezone.now()
                    )
                    wallet.balance += amount
                    wallet.total_balance += amount
                    wallet.save()

            except Wallet.DoesNotExist:
                pass

        return JsonResponse({"status": "ok"})

    return JsonResponse({"error": "Invalid request"}, status=400)

@login_required
def transfer_to_master_view(request, wallet_id):
    wallet = get_object_or_404(Wallet, id=wallet_id)
    r = transfer_to_master(wallet, request)
    # print(r)
    # r2 = transfer_trx(wallet, 7)
    # print(r2)
    return redirect('wallets_list')
