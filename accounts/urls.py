from django.urls import path
from .views import RegisterView, LoginView, ProfileView, UserPreferenceView

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('profile/', ProfileView.as_view(), name='profile'),
    path('preferences/', UserPreferenceView.as_view(), name='user-preferences'),
]