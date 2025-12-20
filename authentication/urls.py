from django.urls import path
from authentication.views import api_login, api_register_user, api_register_coach, api_logout, api_fcm_token, api_fcm_token_delete, api_test_push, api_fcm_tokens_me

app_name = 'authentication'

urlpatterns = [
    path('api_login/', api_login, name='api_login'),
    path('api_register_user/', api_register_user, name='api_register_user'),
    path('api_register_coach/', api_register_coach, name='api_register_coach'),
    path('api_logout/', api_logout, name='api_logout'), 
    path('api_fcm_token/', api_fcm_token, name='api_fcm_token'),
    path('api_fcm_token_delete/', api_fcm_token_delete, name='api_fcm_token_delete'),
    path('api_test_push/', api_test_push, name='api_test_push'),
    path('api_fcm_tokens_me/', api_fcm_tokens_me, name='api_fcm_tokens_me'),
]