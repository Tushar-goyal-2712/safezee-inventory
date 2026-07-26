from django.urls import path
from . import views

app_name = "accounts"

urlpatterns = [
    path("login/", views.login_page, name="login"),
    path("login/options/", views.authentication_options, name="login_options"),
    path("login/verify/", views.authentication_verify, name="login_verify"),
    path("logout/", views.logout_view, name="logout"),

    path("register/", views.register_page, name="register"),
    path("register/options/", views.registration_options, name="register_options"),
    path("register/verify/", views.registration_verify, name="register_verify"),
]
