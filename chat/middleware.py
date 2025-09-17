from urllib.parse import parse_qs
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import AccessToken
from django.contrib.auth.models import AnonymousUser
from channels.db import database_sync_to_async

User = get_user_model()

@database_sync_to_async
def get_user(user_id):
    try:
        return User.objects.get(id=user_id)
    except User.DoesNotExist:
        return AnonymousUser()

class JwtAuthMiddleware:

    def __init__(self, inner):
        self.inner = inner

    def __call__(self, scope):
        return JwtAuthMiddlewareInstance(scope, self.inner)

class JwtAuthMiddlewareInstance:
    def __init__(self, scope, inner):
        self.scope = dict(scope)
        self.inner = inner

    async def __call__(self, receive, send):
        query_string = self.scope.get("query_string", b"").decode()
        qs = parse_qs(query_string)
        token_list = qs.get("token") or qs.get("access_token")
        if token_list:
            token_str = token_list[0]
            try:
                access_token = AccessToken(token_str)  # validate & decode
                user_id = access_token["user_id"]
                self.scope["user"] = await get_user(user_id)
            except Exception:
                self.scope["user"] = AnonymousUser()
        else:
            self.scope["user"] = AnonymousUser()

        inner = self.inner(self.scope)
        return await inner(receive, send)

# helper to wrap
def JwtAuthMiddlewareStack(inner):
    return JwtAuthMiddleware(inner)
