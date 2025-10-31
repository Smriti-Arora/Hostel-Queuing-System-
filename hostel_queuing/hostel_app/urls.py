from django.conf import settings
from django.conf.urls.static import static
from django.urls import path
from .views import loginaction, signaction,student_list, register_student, student_detail, delete_student, scan_qr,update_student, validate_qr_code,regenerate_qr_code,reset_form,scan_qr_for_mess,mess_entry_list,attendance_overview,vacant_rooms_view


urlpatterns = [
    path('', loginaction, name='login'),
    path('home/', student_list, name='student_list'),
    path('signup/', signaction, name='register_student'),
    path('student/<str:uni_roll_no>/', student_detail, name='student_detail'),
    path('student/delete/<str:uni_roll_no>/', delete_student, name='delete_student'),
    path('validate_qr_code/', validate_qr_code, name='validate_qr_code'),
    path('student/update/<str:uni_roll_no>/', update_student, name='update_student'),
    path('generate_qr_code/<int:uni_roll_no>/', regenerate_qr_code, name='generate_qr_code'),
    path('register/', register_student, name='register_student'),
    path('vacant-rooms/', vacant_rooms_view, name='vacant_rooms'),
   
   
    path('scan_qr/', scan_qr, name='scan_qr'),
    path('reset_form/', reset_form, name='reset_form'),  
    path('attendance_overview/', attendance_overview, name='attendance_overview'),
    path('mess_entry/', scan_qr_for_mess, name='scan_qr_for_mess'),
    path('mess-entries/', mess_entry_list, name='mess_entry_list'),
   
    
]
    
if settings.DEBUG:  # Only serve media files in debug mode_i
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)