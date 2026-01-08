from django.urls import path
from django.contrib.auth import views as auth_views # Add this line
from . import views

urlpatterns = [

    # Update this line to use built-in views
    path('login/', auth_views.LoginView.as_view(template_name='login.html'), name='login'),
    
    # Main user pages
    path('', views.home, name='home'), # ✅ This name must be 'home'
    path('report/', views.report_incident, name='report_incident'),
    
    # Admin pages
    path('dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('manage/<int:ticket_id>/', views.manage_ticket, name='manage_ticket'),
    
    # Authentication
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    path('register/', views.register, name='register'),
]