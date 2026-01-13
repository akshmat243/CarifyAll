# accounts/admin.py
from django.contrib import admin
from .models import User, Profile, Attendance, Leave, Holiday, WorkLog
from datetime import date
from datetime import date as date_class

import openpyxl
from openpyxl.styles import Font
from django.http import HttpResponse
from datetime import date
from calendar import monthrange
from .models import Attendance, User, Task

admin.site.register(WorkLog)

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'full_name', 'phone', 'department', 'designation', 'join_date', 'slug')
    search_fields = ('user__username', 'full_name')

def get_month_attendance_summary(user, month, year):
    total_days = monthrange(year, month)[1]
    today = date_class.today()

    present_count = 0
    absent_count = 0

    for day in range(1, total_days + 1):
        d = date_class(year, month, day)

        if d > today:
            continue

        record = Attendance.objects.filter(user=user, date=d, check_in__isnull=False).first()

        if record:
            present_count += 1
        else:
            absent_count += 1

    return present_count, absent_count

@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ("user", "date", "check_in", "check_out", "status")
    list_filter = ("user", "date", "status")

def export_attendance_excel(request):
    user_id = request.GET.get("user_id")
    year = int(request.GET.get("year"))
    month = int(request.GET.get("month"))

    user = User.objects.get(id=user_id)

    num_days = monthrange(year, month)[1]

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Attendance"

    # Header
    ws.append(["Date", "Status", "Check In", "Check Out"])
    ws.row_dimensions[1].font = Font(bold=True)

    for day in range(1, num_days + 1):
        d = date(year, month, day)
        record = Attendance.objects.filter(user=user, date=d).first()

        if record and record.check_in:
            status = "Present"
            check_in = record.check_in
            check_out = record.check_out or "-"
        elif d > date.today():
            status = "-"
            check_in = "-"
            check_out = "-"
        else:
            status = "Absent"
            check_in = "-"
            check_out = "-"

        ws.append([d, status, str(check_in), str(check_out)])

    # Prepare response
    file_name = f"{user.username}_attendance_{month}_{year}.xlsx"

    response = HttpResponse(content_type="application/ms-excel")
    response['Content-Disposition'] = 'attachment; filename="%s"' % file_name
    wb.save(response)
    return response

@admin.register(Leave)
class LeaveAdmin(admin.ModelAdmin):
    list_display = ('user', 'date', 'leave_type', 'status')
    list_filter = ('status', 'leave_type')

@admin.register(Holiday)
class HolidayAdmin(admin.ModelAdmin):
    list_display = ('name', 'date')


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ('title', 'assigned_to', 'created_by', 'status', 'due_date', 'created_at')
    list_filter = ('status', 'assigned_to', 'created_by')
    search_fields = ('title', 'description', 'assigned_to__username')