# accounts/tests.py
from django.test import TestCase
from .models import User, Profile

class ProfileTest(TestCase):
    def test_slug_generation(self):
        user1 = User.objects.create(username='john')
        profile1 = Profile.objects.create(user=user1, full_name='John Doe')
        self.assertEqual(profile1.slug, 'john-doe')  # Assuming slugify works

        user2 = User.objects.create(username='john2')
        profile2 = Profile.objects.create(user=user2, full_name='John Doe')
        self.assertEqual(profile2.slug, 'john-doe-1')  # Unique

def test_uid_generation(self):
  user = User.objects.create(username='test')
  self.assertIsNotNone(user.uid)
  self.assertTrue(user.uid.startswith('U'))