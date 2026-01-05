from django.urls import path
from . import views

urlpatterns = [
    path('report/', views.report_incident, name='report_incident'),
    
    path('history/', views.user_history, name='user_history'),
]