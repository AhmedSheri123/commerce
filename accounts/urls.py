from django.urls import path
from . import views
from wallet import views as wallet_views

app_name = 'accounts'

urlpatterns = [
    path('', views.index, name='profile'),
    path('login/', views.Login, name='login'),
    path('signup/', views.signup, name='signup'),
    path('logout/', views.Logout, name='logout'),
    path('change_password/', views.change_password, name='change_password'),
    path("support/", views.support_page, name="support"),
    path("notifications/", views.notifications_page, name="notifications"),
    path("notifications/<int:notification_id>/read/", views.mark_notification_read, name="notification_read"),
    path("active-users-count/", views.active_users_count_api, name="active_users_count_api"),
    path('survey/', views.survey, name='survey'),


    path('transactions/', views.transactions, name='transactions'),
    path('referral_dashboard/', views.referral_dashboard, name='referral_dashboard'),
    path("deposit/", wallet_views.deposit_view, name="deposit"),
    path("deposit/network/", wallet_views.deposit_network_api, name="deposit_network_api"),
    path("deposit/check/", wallet_views.deposit_check_api, name="deposit_check_api"),
    path("relayer/topup/", wallet_views.relayer_topup_view, name="relayer_topup"),
    path("deposit/sweep/", wallet_views.sweep_to_main_view, name="sweep_to_main"),
    path("webhook/deposit/", wallet_views.deposit_webhook, name="deposit_webhook"),
    path("transfer_to_master/<int:wallet_id>/", wallet_views.transfer_to_master_view, name="transfer_to_master"),
]
