# accounts/views.py
from django.core.validators import slug_unicode_re
from rest_framework.decorators import api_view, permission_classes 
from rest_framework.permissions import IsAuthenticated , AllowAny
from rest_framework.response import Response 
from rest_framework import status, generics, viewsets
from django.utils import timezone
from django.shortcuts import render
from django.contrib.auth import alogout, get_user_model
from django.db.models import Q, Count
from django.http import HttpResponse
from calendar import monthrange
from datetime import date, datetime, time
from openpyxl import Workbook
from openpyxl.styles import Font
import csv
from .serializers import UserSerializer
from .models import Attendance, Profile, Leave, Holiday, Task, WorkLog
from .serializers import (
    AttendanceSerializer, AttendanceByDateSerializer,
    ProfileSerializer, LeaveSerializer, HolidaySerializer, TaskSerializer
)
from .permissions import IsAdmin

User = get_user_model()


# ————————————————————————————————————————
# 1. CHECK-IN & CHECK-OUT (NEW & FIXED)
# ————————————————————————————————————————
@api_view(['POST'])
@permission_classes([AllowAny])
def check_in(request):
    user = request.user
    today = date.today()

    # Get IST time correctly
    ist_now = timezone.localtime(timezone.now())

    attendance, created = Attendance.objects.get_or_create(
        user=user,
        date=today,
        defaults={'check_in': ist_now.time(), 'status': 'Present'}
    )

    if not created and attendance.check_in:
        return Response(
            {"error": "Already checked in today"},
            status=status.HTTP_409_CONFLICT
        )

    attendance.check_in = ist_now.time()
    attendance.status = 'Present'
    attendance.save()

    return Response({
        "message": "Checked in successfully",
        "check_in": ist_now.strftime("%H:%M:%S")   # Always IST
    })



@api_view(['POST'])
@permission_classes([IsAuthenticated])
def check_out(request):
    user = request.user
    today = date.today()

    try:
        attendance = Attendance.objects.get(user=user, date=today)
    except Attendance.DoesNotExist:
        return Response({"error": "Check-in first!"}, status=400)

    if attendance.check_out:
        return Response({"error": "Already checked out"}, status=409)

    # -----------------------------------------------
    # 1. VALIDATE form inputs
    # -----------------------------------------------
    project = request.data.get("project")
    work = request.data.get("work")
    time_taken = request.data.get("time_taken")
    progress = request.data.get("progress")

    if not project:
        return Response({"error": "Project name required"}, status=400)

    # -----------------------------------------------
    # 2. Convert to IST
    # -----------------------------------------------
    ist_now = timezone.localtime(timezone.now())

    # -----------------------------------------------
    # 3. Save Attendance checkout time
    # -----------------------------------------------
    attendance.check_out = ist_now.time()
    attendance.save()

    # -----------------------------------------------
    # 4. Create WorkLog entry
    # -----------------------------------------------
    WorkLog.objects.create(
        user=user,
        date=today,
        project=project,
        work=work,
        time_taken=time_taken,
        progress=progress,
        check_in=attendance.check_in,
        check_out=ist_now.time()
    )

    return Response({
        "message": "Checked out successfully",
        "check_out": ist_now.strftime("%H:%M:%S")
    })



# ————————————————————————————————————————
# 2. MY ATTENDANCE
# ————————————————————————————————————————
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def my_attendance(request):
    data = Attendance.objects.filter(user=request.user).order_by('-date')
    serializer = AttendanceSerializer(data, many=True)
    return Response(serializer.data)


# ————————————————————————————————————————
# 3. ALL ATTENDANCE (Admin only)
# ————————————————————————————————————————
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def all_attendance(request):
    if not request.user.is_superuser and request.user.role != "admin":
        return Response({"error": "Admin access required"}, status=403)

    data = Attendance.objects.all().order_by('-date')
    serializer = AttendanceSerializer(data, many=True)
    return Response(serializer.data)


# ————————————————————————————————————————
# 4. ATTENDANCE BY DATE
# ————————————————————————————————————————
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def attendance_by_date(request):
    date_str = request.GET.get('date')
    if not date_str:
        return Response({"error": "date parameter required"}, status=400)

    try:
        query_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return Response({"error": "Invalid date format. Use YYYY-MM-DD"}, status=400)

    records = Attendance.objects.filter(date=query_date)
    serializer = AttendanceByDateSerializer(records, many=True)
    return Response(serializer.data)


# ————————————————————————————————————————
# 5. PRESENT / ABSENT COUNT BY DATE
# ————————————————————————————————————————
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def present_absent_by_date(request):
    date_str = request.GET.get('date')
    if not date_str:
        return Response({"error": "date parameter required"}, status=400)

    try:
        query_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return Response({"error": "Invalid date format"}, status=400)

    present = Attendance.objects.filter(date=query_date, check_in__isnull=False).count()
    total_staff = User.objects.filter(role='staff').count()
    absent = total_staff - present

    return Response({
        "date": query_date,
        "present": present,
        "absent": absent,
        "total_staff": total_staff
    })


# ————————————————————————————————————————
# 6. ATTENDANCE BY MONTH (List)
# ————————————————————————————————————————
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def attendance_month(request):
    month = request.GET.get('month')  # YYYY-MM
    if not month or len(month) != 7:
        return Response({"error": "month=YYYY-MM required"}, status=400)

    year, month = map(int, month.split('-'))
    records = Attendance.objects.filter(date__year=year, date__month=month)
    serializer = AttendanceSerializer(records, many=True)
    return Response(serializer.data)


# ————————————————————————————————————————
# 7. MONTHLY SUMMARY (Present/Absent Days per User)
# ————————————————————————————————————————
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def monthly_summary(request):
    month = request.GET.get('month')  # YYYY-MM
    if not month:
        return Response({"error": "month=YYYY-MM required"}, status=400)

    try:
        year, month_num = map(int, month.split('-'))
    except ValueError:
        return Response({"error": "Invalid month format. Use YYYY-MM"}, status=400)

    today = date.today()

    # Validate: cannot summarize future months
    if today.year < year or (today.year == year and today.month < month_num):
        return Response({"error": "Cannot summarize future months"}, status=400)

    # Total days in the month
    total_days_in_month = monthrange(year, month_num)[1]
    last_day_of_month = date(year, month_num, total_days_in_month)

    # Eligible days: from 1st of month → up to today (or end of month if earlier)
    eligible_days = min(today, last_day_of_month).day

    # Count holidays in this month (same for all users)
    holidays_count = Holiday.objects.filter(
        date__year=year,
        date__month=month_num
    ).count()

    summary = []
    for user in User.objects.filter(role='staff'):
        # Count present days (has check_in)
        present = Attendance.objects.filter(
            user=user,
            date__year=year,
            date__month=month_num,
            check_in__isnull=False
        ).count()

        # Count approved leaves for this user
        approved_leaves = Leave.objects.filter(
            user=user,
            date__year=year,
            date__month=month_num,
            status='Approved'
        ).count()

        # Calculate actual workdays
        workdays = eligible_days - holidays_count - approved_leaves
        workdays = max(workdays, 0)  # safety

        # Absent = workdays - present
        absent = max(workdays - present, 0)

        # Get full name
        profile = user.profile
        full_name = profile.full_name or user.get_full_name() or user.username

        summary.append({
            "user": user.username,
            "full_name": full_name,
            "present": present,
            "absent": absent,
            "workdays": workdays,
            "eligible_days": eligible_days,
            "holidays": holidays_count,
            "approved_leaves": approved_leaves
        })

    return Response(summary)

# ————————————————————————————————————————
# 8. LIVE STATUS (Who is in office now)
# ————————————————————————————————————————
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def live_status(request):
    today = date.today()
    in_office = Attendance.objects.filter(
        date=today,
        check_in__isnull=False,
        check_out__isnull=True
    ).select_related('user__profile')

    data = []
    for record in in_office:
        profile = record.user.profile
        data.append({
            "username": record.user.username,
            "full_name": profile.full_name or record.user.username,
            "check_in": record.check_in.strftime("%H:%M"),
            "slug": profile.slug
        })

    return Response({"in_office": data})


# ————————————————————————————————————————
# 9. EXPORT MONTHLY REPORT (Excel)
# ————————————————————————————————————————
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def export_monthly_report(request):
    month = request.GET.get('month')
    if not month:
        return Response({"error": "month=YYYY-MM required"}, status=400)

    year, month_num = map(int, month.split('-'))
    wb = Workbook()
    ws = wb.active
    ws.title = f"Attendance {month}"

    # Header
    headers = ["User", "Full Name", "Present", "Absent", "Total Days"]
    ws.append(headers)
    for cell in ws[1]:
        cell.font = Font(bold=True)

    days_in_month = monthrange(year, month_num)[1]
    for user in User.objects.filter(role='staff'):
        present = Attendance.objects.filter(
            user=user, date__year=year, date__month=month_num, check_in__isnull=False
        ).count()
        absent = days_in_month - present

        profile = user.profile
        ws.append([
            user.username,
            profile.full_name or user.get_full_name() or user.username,
            present,
            absent,
            days_in_month
        ])

    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response['Content-Disposition'] = f'attachment; filename=attendance_{month}.xlsx'
    wb.save(response)
    return response


# ————————————————————————————————————————
# 10. DASHBOARD (Summary Stats)
# ————————————————————————————————————————
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard(request):
    today = date.today()
    now = timezone.now()

    # ------------------------------------------------------------------
    # 1. Totals
    # ------------------------------------------------------------------
    total_staff = User.objects.filter(role='staff').count()
    total_admins = User.objects.filter(role='admin').count()

    # ------------------------------------------------------------------
    # 2. Today’s Attendance
    # ------------------------------------------------------------------
    today_attendance = Attendance.objects.filter(date=today)
    present_today = today_attendance.filter(check_in__isnull=False).count()
    checked_out_today = today_attendance.filter(check_out__isnull=False).count()

    # ------------------------------------------------------------------
    # 3. On Leave (Approved)
    # ------------------------------------------------------------------
    on_leave_today = Leave.objects.filter(
        date=today,
        status='Approved'
    ).count()

    # ------------------------------------------------------------------
    # 4. In Office Now
    # ------------------------------------------------------------------
    in_office_now = today_attendance.filter(
        check_in__isnull=False,
        check_out__isnull=True
    ).count()

    # ------------------------------------------------------------------
    # 5. Holidays
    # ------------------------------------------------------------------
    is_holiday = Holiday.objects.filter(date=today).exists()
    holiday_name = Holiday.objects.filter(date=today).first().name if is_holiday else None

    # ------------------------------------------------------------------
    # 6. Current Month Summary (up to today)
    # ------------------------------------------------------------------
    year, month = today.year, today.month
    eligible_days = today.day
    month_holidays = Holiday.objects.filter(date__year=year, date__month=month).count()

    # Total possible workdays for staff
    total_possible = total_staff * eligible_days
    total_possible -= month_holidays * total_staff  # subtract holidays
    total_possible = max(total_possible, 1)  # avoid divide by zero

    # Total actual present days
    actual_present = Attendance.objects.filter(
        date__year=year,
        date__month=month,
        check_in__isnull=False
    ).count()

    avg_present_rate = round((actual_present / total_possible) * 100, 1)

    # ------------------------------------------------------------------
    # 7. Live Check-ins (last 5 mins)
    # ------------------------------------------------------------------
    five_mins_ago = (now - timezone.timedelta(minutes=5)).time()
    recent_checkins = Attendance.objects.filter(
        date=today,
        check_in__gte=five_mins_ago
    ).select_related('user__profile').order_by('-check_in')[:5]

    live_checkins = [
        {
            "name": a.user.profile.full_name or a.user.username,
            "time": a.check_in.strftime("%I:%M %p")
        }
        for a in recent_checkins
    ]

    # ------------------------------------------------------------------
    # Final Response
    # ------------------------------------------------------------------
    data = {
        "today": today.strftime("%A, %B %d, %Y"),
        "is_holiday": is_holiday,
        "holiday_name": holiday_name,

        "totals": {
            "staff": total_staff,
            "admins": total_admins,
            "total": total_staff + total_admins
        },

        "today_stats": {
            "present": present_today,
            "on_leave": on_leave_today,
            "in_office": in_office_now,
            "checked_out": checked_out_today,
            "absent": total_staff - present_today - on_leave_today
        },

        "month_summary": {
            "month": today.strftime("%B %Y"),
            "eligible_days": eligible_days,
            "holidays": month_holidays,
            "average_present_rate": f"{avg_present_rate}%"
        },

        "live_activity": {
            "recent_checkins": live_checkins,
            "total_checkins_today": present_today
        }
    }

    # Optional: Admin-only stats
    if request.user.role == 'admin' or request.user.is_superuser:
        data["admin_insights"] = {
            "pending_leaves": Leave.objects.filter(status='Pending').count(),
            "overtime_today": Attendance.objects.filter(
                date=today,
                working_hours__gt=timezone.timedelta(hours=9)
            ).count()
        }

    return Response(data)


# ————————————————————————————————————————
# 11. LEAVE & HOLIDAY
# ————————————————————————————————————————
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def request_leave(request):
    serializer = LeaveSerializer(data=request.data)
    if serializer.is_valid():
        # Pass user directly to save() → overrides read_only
        leave = serializer.save(user=request.user)
        return Response({
            "message": "Leave request submitted",
            "leave": LeaveSerializer(leave).data
        }, status=201)
    return Response(serializer.errors, status=400)


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def update_leave_status(request, leave_id):
    if not request.user.is_superuser and request.user.role != "admin":
        return Response({"error": "Admin only"}, status=403)

    try:
        leave = Leave.objects.get(id=leave_id)
    except Leave.DoesNotExist:
        return Response({"error": "Not found"}, status=404)

    status_val = request.data.get('status')
    if status_val not in ['Approved', 'Rejected']:
        return Response({"error": "Invalid status"}, status=400)

    leave.status = status_val
    leave.save()
    return Response({"message": "Updated", "status": status_val})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_holiday(request):
    if not request.user.is_superuser and request.user.role != "admin":
        return Response({"error": "Admin only"}, status=403)

    serializer = HolidaySerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response({"message": "Holiday added"})
    return Response(serializer.errors, status=400)


# ————————————————————————————————————————
# 12. PROFILE BY SLUG
# ————————————————————————————————————————
class ProfileDetailBySlug(generics.RetrieveUpdateAPIView):
    queryset = Profile.objects.all()
    serializer_class = ProfileSerializer
    lookup_field = 'slug'
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        if self.request.method in ['PATCH', 'PUT']:
            return [IsAdmin()]
        return super().get_permissions()


# ————————————————————————————————————————
# 13. REGISTER / ADD USER (staff can be created by admin or self-signup)

@api_view(['POST'])
@permission_classes([IsAdmin])
def register_user(request):
    serializer = UserSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.save()          # <-- now returns a saved instance
        # profile is created by signal – just make sure it exists
        Profile.objects.get_or_create(user=user)
        return Response({
            "message": "User created successfully",
            "user": {
                "uid": user.uid,
                "username": user.username,
                "email": user.email,
                "role": user.role,
                "slug": user.profile.slug
            }
        }, status=201)

    return Response(serializer.errors, status=400)

# ------------------------------------------------------------------
# 14. DELETE USER (Admin only)
# ------------------------------------------------------------------
@api_view(['DELETE'])
@permission_classes([IsAuthenticated, IsAdmin])
def delete_user(request, user_uid, uid):
    """
    DELETE /delete-user/<user_uid>/<uid>/
    
    Example:
      DELETE /delete-user/ULI3BNF/AJ2MHLJ/
    
    Requires:
      - user_uid: The actual UID from User model (e.g. ULI3BNF)
      - uid: A SECOND confirmation code (e.g. AJ2MHLJ) – can be anything unique
    
    Only deletes if BOTH match the same user.
    """
    # Step 1: Find user by user_uid
    try:
        user = User.objects.get(uid=user_uid)
    except User.DoesNotExist:
        return Response(
            {"error": "Invalid user_uid: User not found"},
            status=status.HTTP_404_NOT_FOUND
        )

    # Step 2: Double-check: does the same user have the second 'uid'?
    # (You can store this in Profile or just compare)
    # Here we assume `uid` is stored in `user.profile.some_confirmation_field`
    # But since you don't have that, we allow **any non-empty uid** as second key
    # OR you can generate a "delete code" when user is created

    # OPTION A: Simple – just require second uid to be non-empty
    if not uid or len(uid) < 6:
        return Response(
            {"error": "Second confirmation ID (uid) is required and must be valid"},
            status=status.HTTP_400_BAD_REQUEST
        )

    # OPTION B (Recommended): Store a `delete_code` in Profile
    # Let's implement it safely below
    try:
        profile = user.profile
        if not hasattr(profile, 'delete_code') or profile.delete_code != uid:
            return Response(
                {"error": "Invalid confirmation code. Both IDs required."},
                status=status.HTTP_400_BAD_REQUEST
            )
    except:
        return Response(
            {"error": "Profile error. Contact developer."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

    # Safety checks
    if user == request.user:
        return Response({"error": "You cannot delete yourself"}, status=400)
    if user.is_superuser:
        return Response({"error": "Cannot delete superuser"}, status=400)

    username = user.username
    user.delete()  # Deletes user + profile + all attendance

    return Response({
        "message": "User deleted successfully",
        "deleted_user": {
            "username": username,
            "user_uid": user_uid,
            "confirmed_with": uid
        }
    }, status=status.HTTP_200_OK)


# ————————————————————————————————————————
# 15. TASK MANAGEMENT
# ————————————————————————————————————————
# -------------------------------------------------
# 1. CREATE TASK (Admin only)
# -------------------------------------------------
@api_view(['POST'])
@permission_classes([IsAuthenticated, IsAdmin])
def create_task(request):
    data = request.data.copy()
    data['created_by'] = request.user.id               # ← who created it

    serializer = TaskSerializer(data=data)
    if serializer.is_valid():
        task = serializer.save()
        return Response(TaskSerializer(task).data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# -------------------------------------------------
# 2. MY TASKS (Staff sees only own)
# -------------------------------------------------
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def my_tasks(request):
    tasks = Task.objects.filter(assigned_to=request.user).order_by('-created_at')
    serializer = TaskSerializer(tasks, many=True)
    return Response(serializer.data)


# -------------------------------------------------
# 3. ALL TASKS (Admin only)
# -------------------------------------------------
@api_view(['GET'])
@permission_classes([IsAuthenticated, IsAdmin])
def all_tasks(request):
    tasks = Task.objects.all().order_by('-created_at')
    serializer = TaskSerializer(tasks, many=True)
    return Response(serializer.data)


# -------------------------------------------------
# 4. UPDATE STATUS (Staff or Admin)
# -------------------------------------------------
@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def update_task_status(request, task_uid):
    try:
        task = Task.objects.get(uid=task_uid)
    except Task.DoesNotExist:
        return Response({"error": "Task not found"}, status=status.HTTP_404_NOT_FOUND)

    # Only assigned user or admin can update
    if task.assigned_to != request.user and not (request.user.is_superuser or request.user.role == "admin"):
        return Response({"error": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)

    status_val = request.data.get('status')
    if status_val not in dict(Task.STATUS_CHOICES):
        return Response({"error": "Invalid status"}, status=status.HTTP_400_BAD_REQUEST)

    task.status = status_val
    task.save()
    return Response({"message": "Status updated", "status": status_val})