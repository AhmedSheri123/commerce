from decimal import Decimal

from django.contrib.auth.models import User
from django.db import models


class Wallet(models.Model):
    class Network(models.TextChoices):
        TRON = "tron", "TRON (TRC20)"
        BEP20 = "bep20", "BNB Chain (BEP20)"

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="wallets",
    )
    profile = models.ForeignKey(
        "accounts.UserProfile",
        on_delete=models.CASCADE,
        related_name="wallets",
    )
    network = models.CharField(max_length=12, choices=Network.choices)
    balance = models.DecimalField(max_digits=20, decimal_places=8, default=0)
    total_balance = models.DecimalField(max_digits=20, decimal_places=8, default=0)
    address = models.CharField(max_length=255, unique=True)
    private_key = models.TextField()
    last_scanned_block = models.BigIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)
        constraints = [
            models.UniqueConstraint(fields=("user", "network"), name="uniq_wallet_user_network"),
            models.UniqueConstraint(fields=("profile", "network"), name="uniq_wallet_profile_network"),
        ]
        indexes = [
            models.Index(fields=("network", "address")),
            models.Index(fields=("user", "network")),
        ]

    def save(self, *args, **kwargs):
        if self.profile_id and not self.user_id:
            self.user = self.profile.user
        if self.user_id and not self.profile_id:
            self.profile = self.user.profile
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user.username} | {self.get_network_display()} | {self.address}"


class Deposit(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        CONFIRMED = "confirmed", "Confirmed"
        REJECTED = "rejected", "Rejected"

    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name="deposits")
    network = models.CharField(max_length=12, choices=Wallet.Network.choices)
    amount = models.DecimalField(max_digits=20, decimal_places=8)
    txid = models.CharField(max_length=120, unique=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    raw_payload = models.JSONField(null=True, blank=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=("network", "status")),
            models.Index(fields=("wallet", "created_at")),
        ]

    def save(self, *args, **kwargs):
        if self.wallet_id and not self.network:
            self.network = self.wallet.network
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.wallet.user.username} | {self.network} | {self.amount} | {self.status}"


class Relayer(models.Model):
    network = models.CharField(max_length=12, choices=Wallet.Network.choices, unique=True)
    address = models.CharField(max_length=255, blank=True)
    private_key = models.TextField(blank=True)
    rpc_url = models.CharField(max_length=500, blank=True)
    bscscan_api_key = models.CharField(max_length=255, blank=True)
    trongrid_api_key = models.CharField(max_length=255, blank=True)
    min_native_balance = models.DecimalField(max_digits=20, decimal_places=8, default=Decimal("1"))
    topup_amount = models.DecimalField(max_digits=20, decimal_places=8, default=Decimal("3"))
    reserve_native_balance = models.DecimalField(max_digits=20, decimal_places=8, default=Decimal("0.01"))
    is_enabled = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("network",)

    def __str__(self):
        return f"{self.get_network_display()} Relayer"

    @property
    def is_configured(self):
        return bool(self.address and self.private_key and self.is_enabled)


class MainWallet(models.Model):
    network = models.CharField(max_length=12, choices=Wallet.Network.choices, unique=True)
    address = models.CharField(max_length=255, blank=True)
    private_key = models.TextField(blank=True)
    is_enabled = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("network",)

    def __str__(self):
        return f"{self.get_network_display()} Main Wallet"

    @property
    def is_configured(self):
        return bool(self.address and self.is_enabled)


class Sweep(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        SUCCESS = "success", "Success"
        FAILED = "failed", "Failed"

    class FeePayer(models.TextChoices):
        RELAYER = "relayer", "Relayer"
        USER = "user", "User"

    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name="sweeps")
    network = models.CharField(max_length=12, choices=Wallet.Network.choices)
    amount = models.DecimalField(max_digits=20, decimal_places=8)
    destination_address = models.CharField(max_length=255)
    txid = models.CharField(max_length=120, blank=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PENDING)
    fee_payer = models.CharField(max_length=12, choices=FeePayer.choices, default=FeePayer.RELAYER)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=("wallet", "status")),
            models.Index(fields=("network", "created_at")),
        ]

    def save(self, *args, **kwargs):
        if self.wallet_id and not self.network:
            self.network = self.wallet.network
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Sweep {self.wallet.user.username} | {self.network} | {self.amount} | {self.status}"
