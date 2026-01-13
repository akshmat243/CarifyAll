# accounts/models.py
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.text import slugify
from django.db.models.signals import pre_save
from django.dispatch import receiver
from datetime import date, datetime, timedelta
from django.conf import settings
from django.contrib.auth import get_user_model
User = get_user_model()
import uuid
import random
import string
import shortuuid


# ----------------------------------------------------------------------
# UID generator (shared by User and Attendance)
# ----------------------------------------------------------------------
def generate_uid(prefix="U"):
    """6-char unique UID – no DB look-ups, no race conditions."""
    return f"{prefix}{shortuuid.uuid()[:6].upper()}"


# ROLES = (
#      ("SuperAdmin", "SuperAdmin"),
#     ("admin", "Admin"),
#     ("team_leader", "Team Leader"),
#     ("staff", "Staff"),
   
# )

# role = models.CharField(max_length=20, choices=ROLES, default="staff")

class WorkLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    date = models.DateField()

    project = models.CharField(max_length=200)
    work = models.TextField(blank=True, null=True)
    time_taken = models.CharField(max_length=50, blank=True, null=True)
    progress = models.TextField(blank=True, null=True)

    check_in = models.TimeField()
    check_out = models.TimeField()

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.project} ({self.date})"


# ----------------------------------------------------------------------
# Profile
# ----------------------------------------------------------------------
class Profile(models.Model):
    user = models.OneToOneField(
    User,
    on_delete=models.CASCADE,
    related_name='hrm_profile'
)

    full_name = models.CharField(max_length=200, null=True, blank=True)
    phone = models.CharField(max_length=15, null=True, blank=True)
    department = models.CharField(max_length=100, null=True, blank=True)
    designation = models.CharField(max_length=100, null=True, blank=True)
    join_date = models.DateField(null=True, blank=True)
    slug = models.SlugField(max_length=250, unique=True, blank=True, db_index=True)
    delete_code = models.CharField(max_length=10, blank=True, null=True, unique=True)
    
    def save(self, *args, **kwargs):
        if not self.delete_code:
            self.delete_code = generate_uid("D")[:7]  # e.g. D9XK2MP
        super().save(*args, **kwargs)

    def __str__(self):
        return self.full_name or self.user.username

# ----------------------------------------------------------------------
# Attendance
# ----------------------------------------------------------------------
class Attendance(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='accounts_attendance')
    date = models.DateField(default=date.today)
    check_in = models.TimeField(null=True, blank=True)
    check_out = models.TimeField(null=True, blank=True)
    uid = models.CharField(max_length=20, unique=True, blank=True, null=True)

    # Auto-calculated fields
    working_hours = models.DurationField(null=True, blank=True)
    status = models.CharField(
        max_length=12,
        choices=(
            ("Present", "Present"),
            ("Half Day", "Half Day"),
            ("Checked In", "Checked In"),
            ("Absent", "Absent"),
        ),
        default="Absent",
    )

    class Meta:
        unique_together = ('user', 'date')

    # ------------------------------------------------------------------
    # AUTO-CALCULATE ON SAVE
    # ------------------------------------------------------------------
    def save(self, *args, **kwargs):
        # 1. UID
        if not self.uid:
            self.uid = generate_uid("A")

        # 2. Status & working hours
        if self.check_in and self.check_out:
            check_in_dt = datetime.combine(self.date, self.check_in)
            check_out_dt = datetime.combine(self.date, self.check_out)

            # Overnight shift handling
            if check_out_dt < check_in_dt:
                check_out_dt += timedelta(days=1)

            duration = check_out_dt - check_in_dt
            self.working_hours = duration

            total_hours = duration.total_seconds() / 3600
            self.status = "Present" if 8 <= total_hours <= 9 else "Half Day"

        elif self.check_in:
            self.status = "Checked In"
            self.working_hours = None
        else:
            self.status = "Absent"
            self.working_hours = None

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user.username} – {self.date} ({self.status})"


# ----------------------------------------------------------------------
# Leave
# ----------------------------------------------------------------------
class Leave(models.Model):
    LEAVE_TYPES = (
        ("Sick", "Sick Leave"),
        ("Casual", "Casual Leave"),
        ("WFH", "Work From Home"),
    )
    STATUS = (
        ("Pending", "Pending"),
        ("Approved", "Approved"),
        ("Rejected", "Rejected"),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    date = models.DateField()
    leave_type = models.CharField(max_length=20, choices=LEAVE_TYPES)
    status = models.CharField(max_length=10, choices=STATUS, default="Pending")

    def __str__(self):
        return f"{self.user.username} - {self.leave_type} ({self.date})"


# ----------------------------------------------------------------------
# Holiday
# ----------------------------------------------------------------------
class Holiday(models.Model):
    date = models.DateField(unique=True)
    name = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.name} ({self.date})" 



class Task(models.Model):
    STATUS_CHOICES = (
        ("Pending", "Pending"),
        ("In Progress", "In Progress"),
        ("Completed", "Completed"),
    )

    title       = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    assigned_to = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='assigned_tasks',
        limit_choices_to={'role': 'staff'}
    )
    created_by  = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_tasks'
    )
    created_at  = models.DateTimeField(auto_now_add=True)
    due_date    = models.DateField(null=True, blank=True)
    status      = models.CharField(max_length=20, choices=STATUS_CHOICES, default="Pending")
    uid         = models.CharField(max_length=20, unique=True, blank=True, null=True)

    def save(self, *args, **kwargs):
        if not self.uid:
            self.uid = generate_uid("T")          # e.g. T9XK2M
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.title} – {self.assigned_to.username}"