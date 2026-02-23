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


class WalletServiceSetting(models.Model):
    class DepositSource(models.TextChoices):
        AUTO = "auto", "Auto (RPC preferred)"
        RPC = "rpc", "RPC only"
        BSCSCAN = "bscscan", "BscScan only"

    tron_endpoint_uri = models.CharField(max_length=500, default="https://api.trongrid.io")
    tron_usdt_contract = models.CharField(max_length=255, default="TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t")
    tron_usdt_decimals = models.PositiveIntegerField(default=6)
    tron_api_timeout_seconds = models.PositiveIntegerField(default=20)

    bep20_usdt_contract = models.CharField(max_length=255, default="55d398326f99059fF775485246999027B3197955")
    bep20_usdt_decimals = models.PositiveIntegerField(default=18)
    bep20_explorer_chain_id = models.PositiveIntegerField(default=56)

    bep20_rpc_url = models.CharField(max_length=500, blank=True)
    fallback_bep20_rpc_url = models.CharField(max_length=500, blank=True)
    bep20_rpc_fallback_urls = models.TextField(blank=True)
    bep20_rpc_timeout_seconds = models.PositiveIntegerField(default=15)

    bep20_autocheck_lookback_blocks = models.PositiveIntegerField(default=1000)
    bep20_initial_lookback_blocks = models.PositiveIntegerField(default=10000)
    bep20_autocheck_chunk_size = models.PositiveIntegerField(default=200)
    bep20_relayer_reserve_bnb = models.DecimalField(max_digits=20, decimal_places=8, default=Decimal("0.01"))
    bep20_topup_receipt_timeout_seconds = models.PositiveIntegerField(default=180)
    bep20_sweep_receipt_timeout_seconds = models.PositiveIntegerField(default=300)

    bscscan_api_url = models.CharField(max_length=500, default="https://api.etherscan.io/v2/api")
    bscscan_v2_api_url = models.CharField(max_length=500, default="https://api.etherscan.io/v2/api")
    bscscan_api_key = models.CharField(max_length=255, blank=True)
    explorer_timeout_seconds = models.PositiveIntegerField(default=20)
    bep20_deposit_source = models.CharField(
        max_length=20,
        choices=DepositSource.choices,
        default=DepositSource.RPC,
    )
    bep20_bscscan_offset = models.PositiveIntegerField(default=200)
    bep20_bscscan_max_pages = models.PositiveIntegerField(default=5)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Wallet Service Setting"
        verbose_name_plural = "Wallet Service Settings"

    def __str__(self):
        return "Wallet Service Settings"

    @classmethod
    def get_solo(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


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
