from django.urls import path
from . import views

app_name = 'management'

urlpatterns = [
    path('', views.index, name='index'),
    path('platforms/', views.ViewPlateforms, name='platforms'),
    path('platforms/add/', views.addPlateform, name='add_platform'),
    path('platforms/edit/<int:plateform_id>/', views.editPlateform, name='edit_platform'),
    path('platforms/delete/<int:plateform_id>/', views.DeletePlateform, name='delete_platform'),

    path('categories/<int:plateform_id>/', views.ViewCategories, name='categories'),
    path('categories/add/<int:plateform_id>/', views.addCategory, name='add_category'),
    path('categories/edit/<int:category_id>/', views.editCategory, name='edit_category'),
    path('categories/delete/<int:category_id>/', views.DeleteCategory, name='delete_category'),

    path('products/<int:category_id>/', views.ViewProducts, name='products'),
    path('products/add/<int:category_id>/', views.addProduct, name='add_product'),
    path('products/edit/<int:product_id>/', views.editProduct, name='edit_product'),
    path('products/delete/<int:product_id>/', views.DeleteProduct, name='delete_product'),

    path('users/', views.ViewUsers, name='users'),
    path('users/add/', views.addUser, name='add_user'),
    path('users/edit/<int:user_id>/', views.editUser, name='edit_user'),
    path('users/delete/<int:user_id>/', views.deleteUser, name='delete_user'),
    path('users/analytics/<int:user_id>/', views.UserAnalytics, name='user_analytics'),
    path('users/toggle-enabled/<int:user_id>/', views.toggleUserEnabled, name='toggle_user_enabled'),
    path('users/progress/delete/<int:user_id>/', views.deleteUserProgress, name='delete_user_progress'),

    path('withdrawals/', views.ViewWithdrawals, name='withdrawals'),
    path('withdrawals/approve/<int:tx_id>/', views.approveWithdrawal, name='approve_withdrawal'),
    path('withdrawals/reject/<int:tx_id>/', views.rejectWithdrawal, name='reject_withdrawal'),
    path('transfers/', views.ViewTransfers, name='transfers'),

    path('wallets/', views.ViewWallets, name='wallets'),
    path('wallets/<int:wallet_id>/deposits/', views.ViewWalletDeposits, name='wallet_deposits'),
    path('deposits/', views.ViewDeposits, name='deposits'),

    path('api/platforms/<int:platform_id>/categories/', views.api_categories_by_platform, name='api_categories_by_platform'),
    path('api/categories/<int:category_id>/products/', views.api_products_by_category, name='api_products_by_category'),

    path('survey/questions/', views.ViewSurveyQuestions, name='survey_questions'),
    path('survey/questions/add/', views.addSurveyQuestion, name='survey_question_add'),
    path('survey/questions/edit/<int:question_id>/', views.editSurveyQuestion, name='survey_question_edit'),
    path('survey/questions/delete/<int:question_id>/', views.deleteSurveyQuestion, name='survey_question_delete'),

    path('survey/questions/<int:question_id>/options/', views.ViewSurveyOptions, name='survey_options'),
    path('survey/questions/<int:question_id>/options/add/', views.addSurveyOption, name='survey_option_add'),
    path('survey/options/edit/<int:option_id>/', views.editSurveyOption, name='survey_option_edit'),
    path('survey/options/delete/<int:option_id>/', views.deleteSurveyOption, name='survey_option_delete'),

    path('notifications/', views.ViewNotifications, name='notifications'),
    path('support/', views.ViewSupportContacts, name='support_contacts'),
    path('support/toggle/<int:contact_id>/', views.toggleSupportContact, name='support_contact_toggle'),
    path('support/delete/<int:contact_id>/', views.deleteSupportContact, name='support_contact_delete'),
]
