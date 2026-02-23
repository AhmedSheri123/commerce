# users/models.py
import random
import uuid

from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone


def uidGenerator():
    uid = random.randint(10000, 99999)
    return str(uid)


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    balance = models.DecimalField(max_digits=12, decimal_places=4, default=0)
    total_earned = models.DecimalField(max_digits=12, decimal_places=4, default=0)
    img_base64 = models.TextField(null=True, blank=True)
    invite_code = models.CharField(max_length=12, unique=True, blank=True)

    # The user who referred this account (if any).
    referred_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name="referrals"
    )

    from_verified_source = models.BooleanField(
        default=False,
        help_text="Whether the user came from a trusted referral source.",
    )
    is_verified = models.BooleanField(
        default=False,
        help_text="Whether this user is marked as verified.",
    )
    is_enabled = models.BooleanField(
        default=False,
        help_text="Whether the account is enabled.",
    )
    forced_withdrawal = models.BooleanField(
        default=True,
        help_text="Require withdrawal before allowing additional actions.",
    )
    disable_ordering_unitl_withdrawal = models.BooleanField(
        default=False,
        help_text="Disable product ordering until the first withdrawal is completed.",
    )
    has_withdrawn = models.BooleanField(
        default=False,
        help_text="Whether the user has already withdrawn at least once.",
    )

    uid = models.CharField(max_length=12, unique=True, default=uidGenerator)
    wallet_password = models.CharField(max_length=255, null=True, blank=True)
    signup_ip = models.GenericIPAddressField(null=True, blank=True)
    last_login_ip = models.GenericIPAddressField(null=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.invite_code:
            # Generate an invite code automatically for new profiles.
            self.invite_code = self.get_new_invite_code
        super().save(*args, **kwargs)

    @property
    def get_new_invite_code(self):
        return str(uuid.uuid4()).replace("-", "")[:6].upper()

    @property
    def get_full_name(self):
        return f"{self.user.first_name} {self.user.last_name}"

    def __str__(self):
        return f"{self.user.id} - {self.user.username} - {self.get_full_name}"


class DailyEarning(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    date = models.DateField()
    earned = models.DecimalField(max_digits=12, decimal_places=4, default=0)

    class Meta:
        unique_together = ("user", "date")

    def __str__(self):
        return f"{self.user.username} - {self.date} : {self.earned}"


class Transaction(models.Model):
    TRANSACTION_TYPES = (
        ("withdraw", "Withdrawal to external wallet (USDT)"),
        ("transfer", "Internal transfer"),
    )

    STATUS_CHOICES = (
        ("pending", "Pending"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
        ("canceled", "Canceled by user"),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="transactions")
    transaction_type = models.CharField(max_length=10, choices=TRANSACTION_TYPES)
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    # Recipient for internal transfer transactions.
    to_user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="received_transfers",
    )

    # Destination wallet for withdrawal transactions.
    wallet_address = models.CharField(max_length=255, null=True, blank=True)

    # Processing status for withdraw/transfer requests.
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="pending")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        if self.transaction_type == "transfer" and self.to_user:
            return f"{self.user.username} -> {self.to_user.username} : {self.amount} USDT"
        if self.transaction_type == "withdraw" and self.wallet_address:
            return (
                f"{self.user.username} -> external {self.wallet_address} : "
                f"{self.amount} USDT ({self.get_status_display()})"
            )
        return f"{self.user.username} {self.transaction_type} : {self.amount} USDT ({self.get_status_display()})"


class Wallet(models.Model):
    user = models.OneToOneField(User, on_delete=models.SET_NULL, related_name="wallet", null=True)
    balance = models.DecimalField(max_digits=20, decimal_places=8, default=0)
    total_balance = models.DecimalField(max_digits=20, decimal_places=8, default=0)
    address = models.CharField(max_length=255, unique=True)
    private_key = models.TextField()  # Imported private key (sensitive).
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.balance} USDT"

    def get_blockchain_balance(self):
        from wallet.services import get_public_usdt_balance

        return get_public_usdt_balance("tron", self.address)


class Deposit(models.Model):
    NETWORK_CHOICES = [
        ("tron", "TRON (TRC20)"),
        ("ton", "TON"),
        ("polygon", "Polygon (ERC20)"),
        ("bep", "BNB Chain (BEP20)"),
    ]

    STATUS_CHOICES = [
        ("pending", "Pending confirmation"),
        ("confirmed", "Confirmed"),
        ("rejected", "Rejected"),
    ]

    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name="deposits")
    network = models.CharField(max_length=20, choices=NETWORK_CHOICES, default="tron")
    amount = models.DecimalField(max_digits=20, decimal_places=8)
    txid = models.CharField(max_length=100, unique=True)  # Unique blockchain transaction hash.
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="pending")
    created_at = models.DateTimeField(auto_now_add=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.wallet.user.username} - {self.amount} USDT - {self.network} - {self.status}"


class ReferralBonus(models.Model):
    referrer = models.ForeignKey(User, on_delete=models.CASCADE, related_name="referral_bonuses")
    referred_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="earned_from_referral")
    amount = models.DecimalField(max_digits=12, decimal_places=4)
    created_at = models.DateTimeField(auto_now_add=True)
    description = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return f"{self.referrer.username} earned {self.amount} from {self.referred_user.username}"


class SurveyQuestion(models.Model):
    FIELD_TYPES = (
        ("single", "Single Choice"),
        ("multi", "Multi Choice"),
        ("boolean", "Yes/No"),
        ("text", "Text"),
        ("number", "Number"),
    )

    text = models.CharField(max_length=255)
    field_type = models.CharField(max_length=10, choices=FIELD_TYPES, default="single")
    is_required = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)

    def __str__(self):
        return self.text


class SurveyOption(models.Model):
    question = models.ForeignKey(SurveyQuestion, on_delete=models.CASCADE, related_name="options")
    text = models.CharField(max_length=255)
    value = models.CharField(max_length=255, blank=True)
    order = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.question.text} - {self.text}"


class UserSurveyAnswer(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="survey_answers")
    question = models.ForeignKey(SurveyQuestion, on_delete=models.CASCADE, related_name="answers")
    option = models.ForeignKey(SurveyOption, null=True, blank=True, on_delete=models.SET_NULL)
    text_answer = models.TextField(null=True, blank=True)
    bool_answer = models.BooleanField(null=True, blank=True)
    number_answer = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "question", "option")

    def __str__(self):
        return f"{self.user.username} - {self.question.text}"


class Notification(models.Model):
    title = models.CharField(max_length=150)
    message = models.TextField()
    target_all = models.BooleanField(default=False)
    target_user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="targeted_notifications",
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_notifications",
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self):
        scope = "all users" if self.target_all else f"user:{self.target_user_id}"
        return f"{self.title} ({scope})"


class NotificationRead(models.Model):
    notification = models.ForeignKey(
        Notification,
        on_delete=models.CASCADE,
        related_name="read_events",
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="notification_reads",
    )
    read_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("notification", "user")
        ordering = ("-read_at",)

    def __str__(self):
        return f"{self.user.username} read {self.notification_id}"


class ActiveUsersCounter(models.Model):
    value = models.PositiveIntegerField(default=200)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Active users: {self.value}"

    @classmethod
    def get_next_value(cls):
        """
        Return a simulated active-users number that changes gradually every few seconds.
        """
        min_count = 100
        max_count = 800
        step_min = 1
        step_max = 5
        interval_seconds = 5  # Minimum update interval in seconds.

        obj, created = cls.objects.get_or_create(
            pk=1,
            defaults={"value": random.randint(200, 800)},
        )

        now = timezone.now()
        # If updated recently, return current value without changes.
        if not created and (now - obj.updated_at).total_seconds() < interval_seconds:
            return obj.value

        # Random walk within defined bounds.
        step = random.randint(step_min, step_max)
        direction = -1 if random.random() < 0.5 else 1
        new_value = obj.value + (direction * step)
        new_value = max(min_count, min(max_count, new_value))

        # Save only when value actually changes.
        if new_value != obj.value:
            obj.value = new_value
            obj.save(update_fields=["value", "updated_at"])

        return obj.value
