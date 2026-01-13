# attendance_system/urls.py
from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from HRM.views import (
    # ----- REMOVE these two lines -----
    # UserViewSet,
    # ProfileViewSet,
    # -----------------------------------
    check_in,
    check_out,
    my_attendance,
    all_attendance,
    attendance_by_date,
    present_absent_by_date,
    attendance_month,
    monthly_summary,
    live_status,
    export_monthly_report,
    dashboard,
    request_leave,
    update_leave_status,
    create_holiday,
    ProfileDetailBySlug,
    register_user,
    delete_user,
    create_task,
    my_tasks,
    all_tasks,
    update_task_status,
)
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from rest_framework import permissions
from HRM.admin import export_attendance_excel


schema_view = get_schema_view(
    openapi.Info(title="Attendance API", default_version='v1'),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

# ----- REMOVE the router completely (no ViewSets) -----
# router = DefaultRouter()
# router.register('users', UserViewSet)
# router.register('profiles', ProfileViewSet)
# -------------------------------------------------------

urlpatterns = [
    # path('admin/', admin.site.urls),

    # Attendance APIs
    path('checkin/', check_in, name='checkin'),
    path('checkout/', check_out, name='checkout'),
    path('myattendance/', my_attendance, name='myattendance'),
    path('allattendance/', all_attendance, name='allattendance'),
    path('attendance/by-date/', attendance_by_date, name='attendance_by_date'),
    path('attendance/status/by-date/', present_absent_by_date, name='attendance_status_by_date'),
    path('attendance/month/', attendance_month, name='attendance_month_view'),
 #   path('register/', register_user, name='register'),
    path('delete-user/<str:user_uid>/<str:uid>/',delete_user,name='delete-user-secure'),

    # Auth
   # path('login/', TokenObtainPairView.as_view(), name='login'),
   # path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    # ----- REMOVE this line -----
    # path('', include(router.urls)),
    # ---------------------------

    # Swagger
    # path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    # path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),

    # Misc
    path('attendance/export/excel/', export_attendance_excel, name='export_attendance_excel'),
    path("attendance/summary/", monthly_summary, name="monthly_summary"),
    path("attendance/live-status/", live_status),
    path("attendance/export/month/", export_monthly_report),
    path("dashboard/", dashboard, name="dashboard"),
    path("leave/request/", request_leave),
    path('leave/update/<int:leave_id>/', update_leave_status),
    path("holiday/create/", create_holiday),
    path('profiles/<slug:slug>/', ProfileDetailBySlug.as_view(), name='profile-detail-slug'),

        # Task Management
    path('tasks/create/', create_task, name='create_task'),
    path('tasks/my/', my_tasks, name='my_tasks'),
    path('tasks/all/', all_tasks, name='all_tasks'),
    path('tasks/update/<str:task_uid>/', update_task_status, name='update_task_status'),
]