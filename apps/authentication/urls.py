from django.urls import path
from .views import RegisterView, VerifyOtpView, LoginView

app_name = 'authentication'

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('verify-otp/', VerifyOtpView.as_view(), name='verify-otp'),
    path('login/', LoginView.as_view(), name='login'),
]
