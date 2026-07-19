from django.conf import settings
from django.conf.urls.static import static
from django.urls import path

from . import views

urlpatterns = [
    path('', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('home/', views.student_list, name='student_list'),
    path('register/', views.register_student, name='register_student'),
    path('student/<str:uni_roll_no>/', views.student_detail, name='student_detail'),
    path('student/<str:uni_roll_no>/qr/', views.student_qr_image, name='student_qr_image'),
    path('student/delete/<str:uni_roll_no>/', views.delete_student, name='delete_student'),
    path('student/update/<str:uni_roll_no>/', views.update_student, name='update_student'),
    path('generate_qr_code/<str:uni_roll_no>/', views.regenerate_qr_code, name='generate_qr_code'),
    path('validate_qr_code/', views.validate_qr_code, name='validate_qr_code'),
    path('scan_qr/', views.scan_qr, name='scan_qr'),
    path('reset_form/', views.reset_form, name='reset_form'),
    path('attendance_overview/', views.attendance_overview, name='attendance_overview'),
    path('mess_entry/', views.scan_qr_for_mess, name='scan_qr_for_mess'),
    path('mess-entries/', views.mess_entry_list, name='mess_entry_list'),
    path('vacant-rooms/', views.vacant_rooms_view, name='vacant_rooms'),
    path('settings/', views.hostel_settings_view, name='hostel_settings'),
    path('api/available-rooms/', views.available_rooms_api, name='available_rooms_api'),
    path('staff/', views.manage_staff, name='manage_staff'),
    path('staff/<int:user_id>/toggle/', views.toggle_staff_active, name='toggle_staff_active'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
