from django.urls import path
from django.contrib.auth import views as auth_views # Add this line
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

    # Calendar
    path('calendar/', views.incident_calendar, name='incident_calendar'), # The page itself
    path('calendar/data/', views.incident_calendar_data, name='calendar_data'),
    
    # Webhook endpoint for n8n
    path('webhook-test/new-incident/', views.n8n_webhook_new_incident, name='n8n_webhook_new_incident'),
]