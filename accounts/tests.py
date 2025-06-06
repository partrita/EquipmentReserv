from django.test import TestCase, RequestFactory
from django.contrib.auth.models import User
from django.contrib.sites.models import Site
from unittest.mock import patch, MagicMock

# Functions to test from accounts.views
from .views import send_activation_email
# For token generation (though not directly testing token generation here, it's part of the context)
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from .tokens import account_activation_token

class SendActivationEmailTests(TestCase):
    def setUp(self):
        # Create a dummy user
        self.user = User.objects.create_user(username='testuser', email='test@knu.ac.kr', password='password123')
        # Create a request factory
        self.factory = RequestFactory()
        # Create a request object (send_activation_email doesn't use much from request, but site needs it)
        self.request = self.factory.get('/fake-path')
        # Ensure a Site object exists for get_current_site
        if not Site.objects.exists():
            Site.objects.create(domain='example.com', name='example.com')
        self.current_site = Site.objects.get_current()
        # Prepare uid and token as they would be generated in the signup view
        self.uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        self.token = account_activation_token.make_token(self.user)

    @patch('accounts.views.EmailMessage')
    @patch('accounts.views.render_to_string')
    def test_send_activation_email_sends_mail(self, mock_render_to_string, mock_email_message_cls):
        # Mock the return value of render_to_string
        mock_render_to_string.return_value = "Test email message body"

        # Mock the EmailMessage instance and its send method
        mock_email_instance = MagicMock()
        mock_email_message_cls.return_value = mock_email_instance

        # Call the function
        send_activation_email(self.request, self.user, self.current_site, self.uid, self.token)

        # Assert render_to_string was called correctly
        mock_render_to_string.assert_called_once_with(
            'accounts/activation_email.html',
            {
                'user': self.user,
                'domain': self.current_site.domain,
                'uid': self.uid,
                'token': self.token,
            }
        )

        # Assert EmailMessage was initialized correctly
        expected_mail_title = "사회대 스터디룸 예약 시스템 계정 활성화 확인"
        mock_email_message_cls.assert_called_once_with(
            expected_mail_title,
            "Test email message body", # The mocked message body
            to=[self.user.email]
        )

        # Assert the send method was called on the EmailMessage instance
        mock_email_instance.send.assert_called_once()

# Example of how to run this specific test class:
# python manage.py test accounts.tests.SendActivationEmailTests
# To run all tests in accounts app:
# python manage.py test accounts
# To run all tests in the project:
# python manage.py test
