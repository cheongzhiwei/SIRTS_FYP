from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

urlpatterns = [
    # 1. User Pages
    path('report/', views.report_incident, name='report_incident'),
    path('history/', views.user_history, name='user_history'),

    # 2. Authentication
    path('login/', auth_views.LoginView.as_view(template_name='login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),

    # 3. Admin Dashboard
    path('dashboard/', views.admin_dashboard, name='admin_dashboard'),

    # 4. Manage Ticket (THIS WAS MISSING)
    path('manage/<int:ticket_id>/', views.manage_ticket, name='manage_ticket'),
]