from django.urls import path
from main.views import show_main, register_user, register_coach, login_user, logout_user

app_name = "main"

urlpatterns = [
    path("", show_main, name="show_main"),
    path("register/", register_user, name="register"),
    path("register/coach/", register_coach, name="register_coach"),
    path("login/", login_user, name="login"),
    path("logout/", logout_user, name="logout"),
]
