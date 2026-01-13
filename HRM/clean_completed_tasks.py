# accounts/management/commands/clean_completed_tasks.py
from django.core.management.base import BaseCommand
from accounts.models import Task
from django.utils import timezone
from datetime import timedelta

class Command(BaseCommand):
    help = "Deletes completed tasks older than 30 days"

    def handle(self, *args, **options):
        threshold = timezone.now() - timedelta(days=30)
        old_completed = Task.objects.filter(status="Completed", created_at__lt=threshold)
        count = old_completed.count()
        old_completed.delete()
        self.stdout.write(f"Deleted {count} old completed tasks.")