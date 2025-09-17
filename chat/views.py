from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework import status
from django.contrib.auth import get_user_model
from .models import Message
from .serializers import MessageSerializer, UserSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from django.db.models import Q
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

User = get_user_model()

# Create your views here.
class SignupAPIView(APIView):
    permission_classes = [AllowAny] # Allow anyone to access this view

    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')

        if not username or not password:
            return Response({'error': 'Username and password are required.'}, status=status.HTTP_400_BAD_REQUEST)

        if User.objects.filter(username=username).exists():
            return Response({'error': 'Username already exists.'}, status=status.HTTP_400_BAD_REQUEST)

        user = User.objects.create_user(username=username, password=password)
        refresh = RefreshToken.for_user(user)

        return Response({
            'user': UserSerializer(user).data,
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        }, status=status.HTTP_201_CREATED)
    

class UserListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        users = User.objects.exclude(id=request.user.id) # Exclude the requesting user
        serializer = UserSerializer(users, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

class MessageHistoryAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, other_user_id):
        try:
            other_user = User.objects.get(id=other_user_id)
        except User.DoesNotExist:
            return Response({'error': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)

        messages = Message.objects.filter(
            Q(sender=request.user, recipient=other_user) | Q(sender=other_user, recipient=request.user)
        ).order_by('timestamp')

        serializer = MessageSerializer(messages, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    

class SendMessageAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        recipient_id = request.data.get('recipient_id')
        content = request.data.get('content')

        if not recipient_id or not content:
            return Response({'error': 'Recipient ID and content are required.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            recipient = User.objects.get(id=recipient_id)
        except User.DoesNotExist:
            return Response({'error': 'Recipient not found.'}, status=status.HTTP_404_NOT_FOUND)

        message = Message.objects.create(sender=request.user, recipient=recipient, content=content)

        # Notify the recipient via WebSocket
        channel_layer = get_channel_layer()
        room_name = f"chat_{min(request.user.id, recipient.id)}_{max(request.user.id, recipient.id)}"
        async_to_sync(channel_layer.group_send)(
            room_name,
            {
                "type": "chat.message",
                "message": {
                    "id": message.id,
                    "sender": request.user.id,
                    "recipient": recipient.id,
                    "content": message.content,
                    "timestamp": message.timestamp.isoformat(),
                },
            }
        )

        serializer = MessageSerializer(message)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
