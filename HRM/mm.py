from accounts.models import User, Attendance, Profile
from datetime import datetime, timedelta
import random
import string

# Fix User UID
for user in User.objects.filter(uid__isnull=True):
    prefix = "U"
    code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    uid = f"{prefix}{code}"
    while User.objects.filter(uid=uid).exists():
        code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        uid = f"{prefix}{code}"
    user.uid = uid
    user.save()
    print(f"User {user.username} UID: {user.uid}")

# Fix Attendance UID, working_hours, status
for att in Attendance.objects.all():
    # UID
    if not att.uid:
        prefix = "A"
        code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        uid = f"{prefix}{code}"
        while Attendance.objects.filter(uid=uid).exists():
            code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
            uid = f"{prefix}{code}"
        att.uid = uid

    # Working hours & status
    if att.check_in and att.check_out:
        check_in_dt = datetime.combine(att.date, att.check_in)
        check_out_dt = datetime.combine(att.date, att.check_out)
        if check_out_dt < check_in_dt:
            check_out_dt += timedelta(days=1)
        duration = check_out_dt - check_in_dt
        att.working_hours = duration
        total_hours = duration.total_seconds() / 3600
        att.status = "Present" if 8 <= total_hours <= 9 else "Half Day"

    att.save()
    print(f"Attendance {att.date} UID: {att.uid}, Hours: {att.working_hours}, Status: {att.status}")

# Fix Profile full_name
for profile in Profile.objects.filter(full_name__isnull=True):
    profile.full_name = profile.user.get_full_name() or profile.user.username
    profile.save()
    print(f"Profile {profile.user.username} full_name: {profile.full_name}")