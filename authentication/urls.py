from django.urls import path
from authentication.views import api_login

app_name = 'authentication'

urlpatterns = [
    path('login/', api_login, name='login'),
]