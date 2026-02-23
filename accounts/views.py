from decimal import Decimal
import ipaddress
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.models import User

from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from django.utils import timezone
from django.shortcuts import get_object_or_404
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
from accounts.models import Transaction
from django.db import models
from management.models import SupportContact
# Create your views here.


def _get_client_ip(request):
    candidates = []

    cf_ip = str(request.META.get("HTTP_CF_CONNECTING_IP", "") or "").strip()
    if cf_ip:
        candidates.append(cf_ip)

    forwarded_for = str(request.META.get("HTTP_X_FORWARDED_FOR", "") or "").strip()
    if forwarded_for:
        candidates.extend([item.strip() for item in forwarded_for.split(",") if item.strip()])

    real_ip = str(request.META.get("HTTP_X_REAL_IP", "") or "").strip()
    if real_ip:
        candidates.append(real_ip)

    remote_addr = str(request.META.get("REMOTE_ADDR", "") or "").strip()
    if remote_addr:
        candidates.append(remote_addr)

    for candidate in candidates:
        try:
            ipaddress.ip_address(candidate)
            return candidate
        except ValueError:
            continue
    return None


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
            login_ip = _get_client_ip(request)
            if login_ip:
                profile, _ = UserProfile.objects.get_or_create(user=user)
                profile.last_login_ip = login_ip
                profile.save(update_fields=["last_login_ip"])
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
        username = (request.POST.get('username') or '').strip()
        invite_code = (request.POST.get('invite_code') or '').strip()
        password = request.POST.get('password') or ''
        confirm_password = request.POST.get('confirm_password') or ''
        referrer_profiles = UserProfile.objects.filter(invite_code=invite_code)

        if not username.isdigit() or not (8 <= len(username) <= 15):
            messages.error(request, "Phone number must contain digits only and be 8 to 15 digits.")
            return redirect('accounts:signup')

        if len(password) < 6:
            messages.error(request, "Password must be at least 6 characters.")
            return redirect('accounts:signup')

        if password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return redirect('accounts:signup')

        # Check if the invite code is valid (this is a simplified check)
        if not referrer_profiles.exists():
            messages.error(request, 'Invalid invite code')
            return redirect('accounts:signup')

        # Check if the username is already taken
        if User.objects.filter(username=username).exists():
            messages.error(request, "Username is already taken.")
            return redirect('accounts:signup')

        # Create the user (in a real app, you'd use User.objects.create_user())
        user = User.objects.create_user(username=username, password=password)
        user.save()

        referrer_profile = referrer_profiles.first()
        user.profile.referred_by = referrer_profile.user
        user.profile.signup_ip = _get_client_ip(request)


        if referrer_profile.user.profile.is_verified:
            referrer_profile.invite_code = referrer_profile.get_new_invite_code
            referrer_profile.save()
            user.profile.from_verified_source = True

        user.profile.save()
        # For simplicity, we will just redirect to login after "signup"
        messages.success(request, "Account created successfully. You can now log in.")
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
        # Replace previous answers before saving the new submission
        UserSurveyAnswer.objects.filter(user=request.user, question__in=questions).delete()

        for q in questions:
            field_name = f"q_{q.id}"
            if q.field_type == 'multi':
                values = request.POST.getlist(field_name)
                if q.is_required and not values:
                    errors[q.id] = "This question is required."
                    continue
                for val in values:
                    option = SurveyOption.objects.filter(id=val, question=q).first()
                    if option:
                        UserSurveyAnswer.objects.create(user=request.user, question=q, option=option)
            elif q.field_type == 'single':
                val = request.POST.get(field_name, '').strip()
                if q.is_required and not val:
                    errors[q.id] = "This question is required."
                    continue
                option = SurveyOption.objects.filter(id=val, question=q).first()
                if option:
                    UserSurveyAnswer.objects.create(user=request.user, question=q, option=option)
            elif q.field_type == 'boolean':
                val = request.POST.get(field_name, '').strip()
                if q.is_required and val == '':
                    errors[q.id] = "This question is required."
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
                    errors[q.id] = "This question is required."
                    continue
                if val:
                    UserSurveyAnswer.objects.create(user=request.user, question=q, number_answer=val)
            else:  # text
                val = request.POST.get(field_name, '').strip()
                if q.is_required and not val:
                    errors[q.id] = "This question is required."
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
            messages.error(request, "Current password is incorrect.")
            return redirect('accounts:profile')

        if new_password != confirm_new_password:
            messages.error(request, "New password and confirmation do not match.")
            return redirect('accounts:profile')

        request.user.set_password(new_password)
        request.user.save()
        messages.success(request, "Password changed successfully.")
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
    profile = user.profile
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
                        if profile.balance >= amount:  # Ensure enough balance before creating withdrawal
                            # Create pending withdrawal and deduct balance immediately
                            Transaction.objects.create(
                                user=user,
                                transaction_type='withdraw',
                                amount=amount,
                                wallet_address=wallet_address,
                                status='pending'
                            )
                            profile.balance -= amount
                            profile.save()
                            messages.success(request, f"Withdrawal request for {amount} USDT submitted successfully.")
                            return redirect('accounts:transactions')
                        else:
                            messages.error(request, "Insufficient balance.")
                    else:
                        messages.error(request, "Please enter a valid amount and wallet address.")
                else:
                    messages.error(request, "You must complete the required steps before making a withdrawal.")
        elif action == 'cancel_withdraw':
            tx_id = request.POST.get('tx_id')
            tx = Transaction.objects.filter(
                id=tx_id,
                user=user,
                transaction_type='withdraw',
            ).first()

            if not tx:
                messages.error(request, "Withdrawal request not found.")
            elif tx.status != 'pending':
                messages.error(request, "Only pending withdrawal can be canceled.")
            else:
                tx.status = 'canceled'
                tx.processed_at = timezone.now()
                tx.save(update_fields=['status', 'processed_at', 'updated_at'])

                profile.balance += tx.amount
                profile.save(update_fields=['balance'])
                messages.success(request, f"Withdrawal canceled and {tx.amount} USDT returned to your balance.")
                return redirect('accounts:transactions')
        elif action == 'transfer':
            recipient_username = request.POST.get('recipient')
            try:
                recipient = User.objects.get(username=recipient_username)
                if recipient != user:
                    if amount > 0 and user.profile.balance >= amount:
                        # Create transfer transaction record
                        Transaction.objects.create(
                            user=user,
                            transaction_type='transfer',
                            amount=amount,
                            to_user=recipient,
                            status='approved'
                        )
                        # Move balance from sender to recipient
                        user.profile.balance -= amount
                        recipient.profile.balance += amount
                        user.profile.save()
                        recipient.profile.save()
                        messages.success(request, f"Transferred {amount} USDT to {recipient.username} successfully.")
                        return redirect('accounts:transactions')
                    else:
                        messages.error(request, "Insufficient balance or invalid transfer amount.")
                else:messages.error(request, "You cannot transfer to yourself.")
            except User.DoesNotExist:
                messages.error(request, "Recipient user not found.")

    context = {
        "transactions": transactions,
        "balance": user.profile.balance,
    }
    return render(request, "dashboard/accounts/transactions/transactions.html", context)



@login_required
def referral_dashboard(request):
    # Referral dashboard data for the current user
    profile = request.user.profile

    # Referral bonus records ordered by newest
    referral_bonuses = ReferralBonus.objects.filter(referrer=request.user).order_by('-created_at')

    # Total referral bonus amount
    total_bonus = referral_bonuses.aggregate(total=models.Sum('amount'))['total'] or 0

    # Total number of referrals
    total_referrals = referral_bonuses.count()

    context = {
        'profile': profile,
        'referral_bonuses': referral_bonuses,
        'total_bonus': total_bonus,
        'total_referrals': total_referrals,
    }

    return render(request, 'dashboard/accounts/transactions/ReferralBonus.html', context)
