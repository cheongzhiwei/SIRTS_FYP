from django.urls import path
from django.contrib.auth import views as auth_views # Add this line
from . import views

urlpatterns = [
    # Main user pages
    path('', views.home, name='home'), # ✅ This name must be 'home'
    path('report/', views.report_incident, name='report_incident'),
    path('ticket/<int:ticket_id>/', views.ticket_detail, name='ticket_detail'),
    path('mail/', views.mail_notifications, name='mail_notifications'),
    path('mail/open/<int:ticket_id>/', views.open_mail_notification, name='open_mail_notification'),
    path('api/update-ticket/', views.update_incident_from_n8n, name='update_ticket'),
    path('api/quarantine-user/', views.quarantine_user_api, name='quarantine_user_api'),
    path('api/classify-ticket/', views.classify_ticket_api, name='classify_ticket_api'),
    path('api/update-ticket-category/', views.update_ticket_category, name='update_ticket_category'),
    path('api/add-ticket-comment/', views.add_ticket_comment_from_n8n, name='add_ticket_comment_from_n8n'),
    
    
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
    
    # Telegram webhook endpoints for IT acknowledgment
    path('webhook/telegram/acknowledge/<int:ticket_id>/', views.telegram_acknowledge, name='telegram_acknowledge'),
    path('webhook/telegram/message/<int:ticket_id>/', views.telegram_leave_message, name='telegram_leave_message'),
    
    # Webapp IT acknowledgment and comments
    path('acknowledge/<int:ticket_id>/', views.acknowledge_ticket, name='acknowledge_ticket'),
    path('comment/<int:ticket_id>/', views.add_comment, name='add_comment'),
    path('mark-comments-read/<int:ticket_id>/', views.mark_comments_read, name='mark_comments_read'),
]