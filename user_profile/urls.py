from django.urls import path
from .views import register_user, register_coach, login_user, logout_user, dashboard_coach, coach_profile

app_name = "user_profile"

urlpatterns = [
    path("register/", register_user, name="register"),
    path("register/coach/", register_coach, name="register_coach"),
    path("login/", login_user, name="login"),
    path("logout/", logout_user, name="logout"),
    path("dashboard/coach/", dashboard_coach, name="dashboard_coach"),
    path("profile/coach/", coach_profile, name="coach_profile"),
]
