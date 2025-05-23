from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth.models import User
from .models import Board, Channel

class LockTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.board = Board.objects.create(ccid="test123", ip="127.0.0.1", board_address="00", device_id="12345678", device_type="12")
        self.channel = Channel.objects.create(ccid=self.board, channel=1, status="01")
        refresh = RefreshToken.for_user(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')

    def test_login_view(self):
        response = self.client.post('/api/login/', {'username': 'testuser', 'password': 'testpass'})
        self.assertEqual(response.status_code, 200)
        self.assertIn('access', response.data)

    def test_board_list_view(self):
        response = self.client.get('/api/boards/')
        self.assertEqual(response.status_code, 200)

    def test_unlock_view(self):
        response = self.client.post('/api/unlock/', {'channel': 1, 'ccid': 'test123'})
        self.assertEqual(response.status_code, 200)

    def test_lock_view(self):
        response = self.client.post('/api/lock/', {'channel': 1, 'ccid': 'test123'})
        self.assertEqual(response.status_code, 200)

    def test_status_view(self):
        response = self.client.get('/api/status/test123/')
        self.assertEqual(response.status_code, 200)

    def test_read_channel_view(self):
        response = self.client.get('/api/read_channel/test123/1/')
        self.assertEqual(response.status_code, 200)

    def test_read_all_channels_view(self):
        response = self.client.get('/api/read_all_channels/test123/')
        self.assertEqual(response.status_code, 200)

    def test_open_all_view(self):
        response = self.client.post('/api/open_all/test123/')
        self.assertEqual(response.status_code, 200)

    def test_open_multiple_view(self):
        response = self.client.post('/api/open_multiple/test123/', {'channels': [1, 2]})
        self.assertEqual(response.status_code, 200)

    def test_keep_open_view(self):
        response = self.client.post('/api/keep_open/test123/1/')
        self.assertEqual(response.status_code, 200)