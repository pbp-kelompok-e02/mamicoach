from django.urls import path
from .views import register_user, register_coach, login_user, logout_user, dashboard_coach, coach_profile, dashboard_user, user_profile

app_name = "user_profile"

urlpatterns = [
    path("register/", register_user, name="register"),
    path("register/coach/", register_coach, name="register_coach"),
    path("login/", login_user, name="login"),
    path("logout/", logout_user, name="logout"),
    path("dashboard/coach/", dashboard_coach, name="dashboard_coach"),
    path("profile/coach/", coach_profile, name="coach_profile"),
    path("dashboard/user/", dashboard_user, name="dashboard_user"),
    path("profile/user/", user_profile, name="user_profile"),
]
