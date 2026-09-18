from django.contrib.auth import get_user_model
from django.test import TestCase, Client
from django.urls import reverse
from users.models import Profile

User = get_user_model()


class TwoFactorActivationEmailTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            password='password123',
            email='initial@example.com'
        )
        self.profile = Profile.objects.get_or_create(user=self.user)[0]

    def test_activation_requires_email_when_empty(self):
        self.user.email = ''
        self.user.save()
        self.client.login(username='testuser', password='password123')

        response = self.client.post(reverse('users:toggle_2fa'), {'action': 'activate', 'email': ''})
        self.profile.refresh_from_db()
        self.assertFalse(self.profile.is_2fa_enabled)

    def test_activation_rejects_invalid_email(self):
        self.client.login(username='testuser', password='password123')

        response = self.client.post(reverse('users:toggle_2fa'), {'action': 'activate', 'email': 'not-an-email'})
        self.profile.refresh_from_db()
        self.assertFalse(self.profile.is_2fa_enabled)

    def test_activation_succeeds_and_updates_email_when_changed(self):
        self.client.login(username='testuser', password='password123')

        new_email = 'updated_confirmed@example.com'
        response = self.client.post(reverse('users:toggle_2fa'), {'action': 'activate', 'email': new_email})
        self.profile.refresh_from_db()
        self.user.refresh_from_db()

        self.assertTrue(self.profile.is_2fa_enabled)
        self.assertEqual(self.user.email, new_email)

    def test_activation_succeeds_with_existing_confirmed_email(self):
        self.client.login(username='testuser', password='password123')

        response = self.client.post(reverse('users:toggle_2fa'), {'action': 'activate', 'email': 'initial@example.com'})
        self.profile.refresh_from_db()
        self.user.refresh_from_db()

        self.assertTrue(self.profile.is_2fa_enabled)
        self.assertEqual(self.user.email, 'initial@example.com')

    def test_deactivation(self):
        self.profile.is_2fa_enabled = True
        self.profile.save()
        self.client.login(username='testuser', password='password123')

        response = self.client.post(reverse('users:toggle_2fa'), {'action': 'deactivate'})
        self.profile.refresh_from_db()
        self.assertFalse(self.profile.is_2fa_enabled)
