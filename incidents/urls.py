from django.urls import path
from . import views

urlpatterns = [
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