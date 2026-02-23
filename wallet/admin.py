from django.contrib import admin

from wallet.models import Deposit, MainWallet, Relayer, Sweep, Wallet


@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "network", "address", "balance", "total_balance", "is_active", "created_at")
    list_filter = ("network", "is_active", "created_at")
    search_fields = ("user__username", "user__email", "address")


@admin.register(Deposit)
class DepositAdmin(admin.ModelAdmin):
    list_display = ("id", "wallet", "network", "amount", "txid", "status", "created_at")
    list_filter = ("network", "status", "created_at")
    search_fields = ("wallet__user__username", "wallet__address", "txid")


@admin.register(Relayer)
class RelayerAdmin(admin.ModelAdmin):
    list_display = ("network", "address", "min_native_balance", "topup_amount", "reserve_native_balance", "is_enabled", "updated_at")
    list_filter = ("network", "is_enabled")
    search_fields = ("address",)


@admin.register(MainWallet)
class MainWalletAdmin(admin.ModelAdmin):
    list_display = ("network", "address", "is_enabled", "updated_at")
    list_filter = ("network", "is_enabled")
    search_fields = ("address",)


@admin.register(Sweep)
class SweepAdmin(admin.ModelAdmin):
    list_display = ("id", "wallet", "network", "amount", "status", "txid", "created_at", "completed_at")
    list_filter = ("network", "status", "fee_payer", "created_at")
    search_fields = ("wallet__user__username", "wallet__address", "txid", "destination_address")
