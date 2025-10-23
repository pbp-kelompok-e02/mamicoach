from django.urls import path
from . import views

app_name = 'schedule'

urlpatterns = [
    # API endpoints for coach availability
    path('api/availability/upsert/', views.api_availability_upsert, name='api_availability_upsert'),
    path('api/availability/', views.api_availability_list, name='api_availability_list'),
    # Note: DELETE uses the same URL as GET, Django will route based on HTTP method
]
