
from django.urls import path

from wallet import views

app_name = "wallet"

urlpatterns = [
    path("deposit/", views.deposit_view, name="deposit"),
    path("deposit/network/", views.deposit_network_api, name="deposit_network_api"),
    path("deposit/check/", views.deposit_check_api, name="deposit_check_api"),
    path("relayer/topup/", views.relayer_topup_view, name="relayer_topup"),
    path("deposit/sweep/", views.sweep_to_main_view, name="sweep_to_main"),
    path("webhook/deposit/", views.deposit_webhook, name="deposit_webhook"),
    path("transfer_to_master/<int:wallet_id>/", views.transfer_to_master_view, name="transfer_to_master"),
]
