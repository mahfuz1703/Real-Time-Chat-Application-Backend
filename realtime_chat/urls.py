from django.contrib import admin
from django.urls import path
from chat.views import (
    SignupAPIView,
    UserListAPIView,
    MessageHistoryAPIView,
    SendMessageAPIView
)
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Authentication
    path('api/auth/signup/', SignupAPIView.as_view(), name='signup'),
    path('api/auth/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    # Users and Messages
    path('api/users/', UserListAPIView.as_view(), name='user_list'),
    path('api/messages/<int:other_user_id>/', MessageHistoryAPIView.as_view(), name='message_history'),
    path('api/messages/send/', SendMessageAPIView.as_view(), name='send_message'),
]
