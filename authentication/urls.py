from django.urls import path
from authentication.views import api_login, api_register_user, api_register_coach, api_logout

app_name = 'authentication'

urlpatterns = [
    path('api_login/', api_login, name='api_login'),
    path('api_register_user/', api_register_user, name='api_register_user'),
    path('api_register_coach/', api_register_coach, name='api_register_coach'),
    path('api_logout/', api_logout, name='api_logout'), 
]