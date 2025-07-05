from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/', views.dashboard, name='dashboard'),
    path('trigger-scan/', views.trigger_scan, name='trigger_scan'),
    path('cancel-scan/', views.cancel_scan, name='cancel_scan'),
    path('start-login/', views.trigger_login, name='start_login'),
]