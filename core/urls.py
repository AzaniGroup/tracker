from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

app_name = 'core'

urlpatterns = [
    # Landing page / root
    path('', views.DashboardView.as_view(), name='home'),
    # Auth routes
    path('accounts/login/', views.CustomLoginView.as_view(), name='login'),
    path('accounts/verify-otp/', views.VerifyOTPView.as_view(), name='verify_otp'),
    path('accounts/resend-otp/', views.ResendOTPView.as_view(), name='resend_otp'),
    path('accounts/logout/', views.logout_view, name='logout'),
    path('dashboard/', views.DashboardView.as_view(), name='dashboard'),
    path('expenses/', views.ExpensesDashboardView.as_view(), name='expenses_dashboard'),
    path('expenses/unplanned/add/', views.UnplannedExpenseCreateView.as_view(), name='add_unplanned_expense'),
    path('project/<int:pk>/select/', views.ProjectSwitcherView.as_view(), name='select_project'),
]
