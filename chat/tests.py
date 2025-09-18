from rest_framework.test import APITestCase
from rest_framework import status
from django.contrib.auth import get_user_model
from chat.models import Message

User = get_user_model()


class ChatAPITests(APITestCase):
    def setUp(self):
        self.signup_url = "/api/auth/signup/"
        self.token_url = "/api/auth/token/"
        self.user_list_url = "/api/users/"
        self.send_message_url = "/api/messages/send/"

        self.alice = User.objects.create_user(username="alice", password="alice123")
        self.bob = User.objects.create_user(username="bob", password="bob123")

    def _auth_as_alice(self):
        token_response = self.client.post(self.token_url, {"username": "alice", "password": "alice123"}, format="json")
        token = token_response.data["access"]
        self.client.credentials(HTTP_AUTHORIZATION="Bearer " + token)

    # Signup Tests ----------
    def test_signup_success(self):
        response = self.client.post(self.signup_url, {"username": "mahfuz", "password": "mahfuz123"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(User.objects.filter(username="mahfuz").exists())

    def test_signup_missing_fields(self):
        response = self.client.post(self.signup_url, {"username": ""}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_signup_duplicate_username(self):
        response = self.client.post(self.signup_url, {"username": "alice", "password": "alice123"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # Token/Login Tests ----------
    def test_token_success(self):
        response = self.client.post(self.token_url, {"username": "alice", "password": "alice123"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)

    def test_token_invalid_credentials(self):
        response = self.client.post(self.token_url, {"username": "alice", "password": "wrongpass"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    # User List Tests ----------
    def test_user_list_success(self):
        self._auth_as_alice()
        response = self.client.get(self.user_list_url, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, list)
        self.assertGreaterEqual(len(response.data), 1)
        for user in response.data:
            self.assertIn("id", user)
            self.assertIn("username", user)
            self.assertNotEqual(user["username"], "alice")

    # Message send ----------
    def test_send_message_success(self):
        self._auth_as_alice()
        resp = self.client.post(self.send_message_url, {"recipient_id": self.bob.id, "content": "hello bob"}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        msg = Message.objects.filter(sender=self.alice, recipient=self.bob).first()
        self.assertIsNotNone(msg)
        self.assertEqual(msg.content, "hello bob")

    def test_send_message_missing_fields(self):
        self._auth_as_alice()
        resp = self.client.post(self.send_message_url, {"content": "no recipient"}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_send_message_recipient_not_found(self):
        self._auth_as_alice()
        resp = self.client.post(self.send_message_url, {"recipient_id": 9999, "content": "hello"}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_send_message_unauthenticated(self):
        resp = self.client.post(self.send_message_url, {"recipient_id": self.bob.id, "content": "hi"}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    # Message history ----------
    def test_message_history_success(self):
        Message.objects.create(sender=self.alice, recipient=self.bob, content="first")
        self._auth_as_alice()
        resp = self.client.get(f"/api/messages/{self.bob.id}/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(resp.data), 1)
        self.assertEqual(resp.data[0]["content"], "first")

    def test_message_history_other_user_not_found(self):
        self._auth_as_alice()
        resp = self.client.get("/api/messages/9999/")
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_message_history_unauthenticated(self):
        resp = self.client.get(f"/api/messages/{self.bob.id}/")
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)
