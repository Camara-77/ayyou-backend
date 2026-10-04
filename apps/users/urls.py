from django.urls import path
from .views import UserProfileView, UserLocationView, UserModesView, UserModeSwitchView, UserPhoneUpdateView

app_name = 'users'

urlpatterns = [
    path('me/', UserProfileView.as_view(), name='user-profile'),
    path('me/phone/', UserPhoneUpdateView.as_view(), name='user-phone-update'),
    path('me/location/', UserLocationView.as_view(), name='user-location'),
    path('me/modes/', UserModesView.as_view(), name='user-modes'),
    path('me/mode/', UserModeSwitchView.as_view(), name='user-mode-switch'),
]

