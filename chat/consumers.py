import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from .models import Message

User = get_user_model()

@database_sync_to_async
def save_message(sender_id, recipient_id, content):
    sender = User.objects.get(id=sender_id)
    recipient = User.objects.get(id=recipient_id)
    message = Message.objects.create(sender=sender, recipient=recipient, content=content)
    return {
        'id': message.id,
        'sender': {'id': sender.id, 'username': sender.username},
        'recipient': {'id': recipient.id, 'username': recipient.username},
        'content': message.content,
        'timestamp': message.timestamp.isoformat(),
        'is_read': message.is_read,
    }

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        user = self.scope.get("user")
        if not user or user.is_anonymous:
            await self.close()
            return

        self.user = user
        self.other_user_id = int(self.scope["url_route"]["kwargs"]["other_user_id"])
        
        # determine room name
        a = min(self.user.id, self.other_user_id)
        b = max(self.user.id, self.other_user_id)
        self.room_group_name = f"chat_{a}_{b}"

        # join the group
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data=None, bytes_data=None):
        data = json.loads(text_data)
        content = data.get("message")
        if not content:
            return

        # save
        msg = await save_message(self.user.id, self.other_user_id, content)

        # broadcast to group
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "chat.message",
                "message": msg,
            },
        )

    async def chat_message(self, event):
        # Forward message dict to WebSocket client
        await self.send(text_data=json.dumps({"type":"message", "message": event["message"]}))
    