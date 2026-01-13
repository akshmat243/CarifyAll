# accounts/management/commands/fix_duplicate_slugs.py

from django.core.management.base import BaseCommand
from accounts.models import Profile

class Command(BaseCommand):
    help = "Generate slugs for profiles missing them"

    def handle(self, *args, **options):
        for profile in Profile.objects.filter(slug__isnull=True) | Profile.objects.filter(slug=''):
            profile.save()
            self.stdout.write(f"Slug generated: {profile.slug}")