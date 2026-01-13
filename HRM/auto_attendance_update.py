# accounts/management/commands/auto_attendance_update.py
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta, time
from accounts.models import User, Attendance

class Command(BaseCommand):
    help = "Automatically marks absent and performs auto-checkout."

    def handle(self, *args, **kwargs):
        today = timezone.now().date()

        # 1. Auto Absent for previous days
        for user in User.objects.filter(role="staff"):
            for day_offset in range(1, 4):  # last 3 days
                date_to_check = today - timedelta(days=day_offset)

                exists = Attendance.objects.filter(user=user, date=date_to_check).exists()
                if not exists:
                    Attendance.objects.create(user=user, date=date_to_check)
                    self.stdout.write(f"[ABSENT] {user.username} on {date_to_check}")

        # 2. Auto Checkout if missing check_out after 11 PM
        now = timezone.now()
        if now.time() >= time(23, 0):  # 11:00 PM
            open_records = Attendance.objects.filter(check_in__isnull=False, check_out__isnull=True, date=today)
            for record in open_records:
                record.check_out = time(23, 0)
                record.save()
                self.stdout.write(f"[AUTO CHECKOUT] {record.user.username} at 11 PM")

        self.stdout.write("✔ Auto Attendance Update Completed")