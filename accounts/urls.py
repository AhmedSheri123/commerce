from django.urls import path
from . import views

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
    path("deposit/", views.deposit_view, name="deposit"),
    path("webhook/deposit/", views.tron_webhook, name="tron_webhook"),
    path("transfer_to_master/<int:wallet_id>/", views.transfer_to_master_view, name="transfer_to_master"),
]
