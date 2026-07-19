import io
import json
import logging
from datetime import date, time

import pytz
import qrcode
from django.contrib import messages
from django.contrib.auth import login, logout
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from .forms import HostelSettingsForm, LoginForm, StaffUserCreateForm, StudentForm
from .models import (
    Attendance,
    HostelSettings,
    MessAttendance,
    ROOM_TYPE_CHOICES,
    StaffProfile,
    Student,
    available_rooms,
)
from .permissions import get_user_role, home_url_for_role, role_required

logger = logging.getLogger(__name__)


def _scan_timestamp():
    """Current local time formatted for scan responses."""
    now = timezone.localtime()
    return {
        'scanned_at': now.strftime('%d %b %Y, %I:%M:%S %p'),
        'scanned_time': now.strftime('%I:%M:%S %p'),
        'scanned_date': now.strftime('%d %b %Y'),
    }


def generate_qr_code(student):
    """Generate a QR code and store the PNG bytes in the database."""
    try:
        qr_data = f"{student.uni_roll_no},{student.name}"
        qr = qrcode.make(qr_data)

        buffer = io.BytesIO()
        qr.save(buffer, format='PNG')
        student.qr_code = buffer.getvalue()
        student.qr_code_data = qr_data
        student.save(update_fields=['qr_code', 'qr_code_data'])
        return True
    except Exception:
        logger.exception('Failed to generate QR code for %s', student.uni_roll_no)
        return False


@require_http_methods(['GET', 'POST'])
def login_view(request):
    if request.user.is_authenticated:
        return redirect(home_url_for_role(get_user_role(request.user)))

    form = LoginForm(request, data=request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.get_user()
        login(request, user)
        role = get_user_role(user)
        if role is None and not user.is_superuser:
            logout(request)
            messages.error(request, 'No staff role assigned. Ask the super admin to set up your account.')
            return render(request, 'login.html', {'form': LoginForm(request)})
        messages.success(request, f'Welcome back, {user.get_username()}.')
        next_url = request.GET.get('next') or home_url_for_role(role)
        return redirect(next_url)

    return render(request, 'login.html', {'form': form})


@require_POST
@role_required(StaffProfile.ROLE_ADMIN, StaffProfile.ROLE_GATE, StaffProfile.ROLE_MESS)
def logout_view(request):
    logout(request)
    messages.info(request, 'You have been signed out.')
    return redirect('login')


@role_required(StaffProfile.ROLE_ADMIN)
@require_POST
def regenerate_qr_code(request, uni_roll_no):
    student = get_object_or_404(Student, uni_roll_no=uni_roll_no)
    if generate_qr_code(student):
        return JsonResponse({
            'success': True,
            'qr_code': student.qr_code_data_uri,
        })
    return JsonResponse(
        {'success': False, 'message': 'Could not generate QR code.'},
        status=500,
    )


@role_required(StaffProfile.ROLE_ADMIN)
@require_GET
def student_qr_image(request, uni_roll_no):
    """Serve the QR PNG stored in the database."""
    student = get_object_or_404(Student, uni_roll_no=uni_roll_no)
    if not student.qr_code:
        return HttpResponse(status=404)
    return HttpResponse(bytes(student.qr_code), content_type='image/png')


@role_required(StaffProfile.ROLE_ADMIN)
@require_http_methods(['GET', 'POST'])
def student_list(request):
    students = Student.objects.all().order_by('uni_roll_no')
    form = StudentForm(request.POST or None)

    if request.method == 'POST':
        if form.is_valid():
            student = form.save()
            generate_qr_code(student)
            messages.success(request, 'Student saved successfully.')
            return redirect('student_list')
        messages.error(request, 'Please correct the errors below.')

    return render(request, 'student_list.html', {'form': form, 'students': students})


@role_required(StaffProfile.ROLE_ADMIN)
@require_http_methods(['GET', 'POST'])
def register_student(request):
    form = StudentForm(request.POST or None, request.FILES or None)
    if request.method == 'POST' and form.is_valid():
        student = form.save()
        generate_qr_code(student)
        messages.success(request, 'Student registered successfully.')
        return redirect('student_list')
    return render(request, 'student_form.html', {'form': form, 'title': 'Register Student'})


@role_required(StaffProfile.ROLE_ADMIN)
@require_GET
def student_detail(request, uni_roll_no):
    student = get_object_or_404(Student, uni_roll_no=uni_roll_no)
    return render(request, 'student_detail.html', {'student': student})


@role_required(StaffProfile.ROLE_ADMIN)
@require_http_methods(['GET', 'POST'])
def update_student(request, uni_roll_no):
    student = get_object_or_404(Student, uni_roll_no=uni_roll_no)
    form = StudentForm(request.POST or None, instance=student)
    if request.method == 'POST':
        if form.is_valid():
            form.save()
            messages.success(request, 'Student updated successfully.')
            return redirect('student_list')
        messages.error(request, 'Please correct the errors below.')
    return render(
        request,
        'student_form.html',
        {'form': form, 'student': student, 'title': 'Update Student'},
    )


@role_required(StaffProfile.ROLE_ADMIN)
@require_http_methods(['GET', 'POST'])
def delete_student(request, uni_roll_no):
    student = get_object_or_404(Student, uni_roll_no=uni_roll_no)
    if request.method == 'POST':
        try:
            student.delete()
            messages.success(request, 'Student deleted successfully.')
        except Exception:
            logger.exception('Error deleting student %s', uni_roll_no)
            messages.error(request, 'Could not delete student.')
        return redirect('student_list')
    return render(request, 'confirm_delete.html', {'student': student})


@role_required(StaffProfile.ROLE_ADMIN)
@require_GET
def reset_form(request):
    messages.info(request, 'Form has been reset.')
    return redirect('student_list')


@role_required(StaffProfile.ROLE_GATE)
@require_http_methods(['GET', 'POST'])
def scan_qr(request):
    if request.method == 'POST':
        stamp = _scan_timestamp()
        try:
            data = json.loads(request.body.decode('utf-8'))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return JsonResponse({
                'message': 'Invalid request body.',
                'success': False,
                **stamp,
            }, status=400)

        qr_data = (data.get('qr_data') or '').strip()
        if not qr_data or ',' not in qr_data:
            return JsonResponse({
                'message': 'Invalid QR data.',
                'success': False,
                **stamp,
            }, status=400)

        uni_roll_no = qr_data.split(',', 1)[0].strip()
        try:
            student = Student.objects.get(uni_roll_no=uni_roll_no)
        except Student.DoesNotExist:
            return JsonResponse({
                'message': 'Unauthorized user.',
                'success': False,
                **stamp,
            }, status=404)

        today = timezone.localdate()
        current_time = timezone.localtime().time()
        attendance, _ = Attendance.objects.get_or_create(uni_roll_no=uni_roll_no, date=today)

        if time(22, 0) <= current_time or current_time < time(7, 0):
            return JsonResponse({
                'message': f'{student.name} cannot enter or exit between 10 PM and 7 AM.',
                'success': False,
                **stamp,
            })

        if attendance.status == 'Absent':
            attendance.time_in = current_time
            attendance.time_out = None
            attendance.status = 'Present'
            attendance.save()
            return JsonResponse({
                'message': f'{student.name} marked Present.',
                'success': True,
                'status': 'Present',
                'name': student.name,
                'uni_roll_no': student.uni_roll_no,
                **stamp,
            })

        attendance.time_out = current_time
        attendance.status = 'Absent'
        attendance.save()
        return JsonResponse({
            'message': f'{student.name} marked Absent.',
            'success': True,
            'status': 'Absent',
            'name': student.name,
            'uni_roll_no': student.uni_roll_no,
            **stamp,
        })

    return render(request, 'scan_qr.html')


@role_required(StaffProfile.ROLE_ADMIN, StaffProfile.ROLE_GATE)
@require_POST
def validate_qr_code(request):
    qr_code_data = (request.POST.get('qr_code') or '').strip()
    if not qr_code_data:
        return JsonResponse({'valid': False}, status=400)
    exists = Student.objects.filter(qr_code_data=qr_code_data).exists()
    return JsonResponse({'valid': exists})


@role_required(StaffProfile.ROLE_MESS)
@require_http_methods(['GET', 'POST'])
def scan_qr_for_mess(request):
    if request.method == 'POST':
        stamp = _scan_timestamp()
        uni_roll_no = (request.POST.get('uni_roll_no') or '').strip()
        meal = (request.POST.get('meal') or '').strip().lower()

        if meal not in ('breakfast', 'lunch', 'dinner'):
            return JsonResponse({
                'message': 'Invalid meal type.',
                'success': False,
                **stamp,
            }, status=400)

        student = Student.objects.filter(uni_roll_no=uni_roll_no).first()
        if not student:
            return JsonResponse({
                'message': 'Student not found.',
                'success': False,
                **stamp,
            }, status=404)

        india_tz = pytz.timezone('Asia/Kolkata')
        current_time = timezone.now().astimezone(india_tz).time()
        windows = {
            'breakfast': (time(7, 30), time(9, 0)),
            'lunch': (time(12, 30), time(14, 0)),
            'dinner': (time(19, 30), time(21, 0)),
        }
        start, end = windows[meal]
        if not (start <= current_time <= end):
            return JsonResponse({
                'message': f'Invalid time for {meal}. Attendance not marked.',
                'success': False,
                **stamp,
            })

        if MessAttendance.objects.filter(
            uni_roll_no=uni_roll_no, meal=meal, date=date.today()
        ).exists():
            return JsonResponse({
                'message': 'Attendance already marked for this meal today.',
                'success': False,
                **stamp,
            })

        MessAttendance.objects.create(uni_roll_no=uni_roll_no, meal=meal, date=date.today())
        return JsonResponse({
            'message': f'{student.name} marked for {meal.title()}.',
            'success': True,
            'name': student.name,
            'uni_roll_no': student.uni_roll_no,
            'meal': meal,
            **stamp,
        })

    return render(request, 'scan_qr_for_mess.html')


@role_required(StaffProfile.ROLE_MESS)
@require_GET
def mess_entry_list(request):
    meal_entries = MessAttendance.objects.all().order_by('-date', '-id')
    context = {
        'meal_entries': meal_entries,
        'breakfast_count': meal_entries.filter(meal='breakfast').count(),
        'lunch_count': meal_entries.filter(meal='lunch').count(),
        'dinner_count': meal_entries.filter(meal='dinner').count(),
    }
    return render(request, 'mess_entry_list.html', context)


@role_required(StaffProfile.ROLE_GATE)
@require_GET
def attendance_overview(request):
    today = timezone.localdate()
    present_students = []
    absent_students = []

    for student in Student.objects.all().order_by('uni_roll_no'):
        attendance = Attendance.objects.filter(uni_roll_no=student.uni_roll_no, date=today).first()
        if attendance and attendance.status == 'Present':
            present_students.append(student)
        else:
            absent_students.append(student)

    return render(request, 'attendance_overview.html', {
        'present_students': present_students,
        'absent_students': absent_students,
        'total_students': len(present_students) + len(absent_students),
        'today': today,
        'current_time': timezone.localtime().time(),
    })


def get_vacant_rooms():
    from django.db.models import Count

    settings = HostelSettings.load()
    types = ['Single', 'Double', 'Triple', 'FourSitter']
    vacant_rooms = {
        'rows': [],
        'single_vacant': 0,
        'double_vacant': 0,
        'triple_vacant': 0,
        'foursitter_vacant': 0,
        'single_vacant_space': 0,
        'double_vacant_space': 0,
        'triple_vacant_space': 0,
        'foursitter_vacant_space': 0,
        'single_room_numbers': [],
        'double_room_numbers': [],
        'triple_room_numbers': [],
        'foursitter_room_numbers': [],
    }

    occupied = {
        row['room_no']: row['count']
        for row in Student.objects.values('room_no').annotate(count=Count('uni_roll_no'))
    }

    key_map = {
        'Single': 'single',
        'Double': 'double',
        'Triple': 'triple',
        'FourSitter': 'foursitter',
    }

    for room_type in types:
        capacity = settings.capacity_for(room_type)
        for room_no in settings.inventory_for(room_type):
            used = occupied.get(room_no, 0)
            free = capacity - used
            if free > 0:
                key = key_map[room_type]
                vacant_rooms[f'{key}_vacant'] += 1
                vacant_rooms[f'{key}_vacant_space'] += free
                vacant_rooms[f'{key}_room_numbers'].append(f'{room_no} ({used}/{capacity})')
                vacant_rooms['rows'].append({
                    'room_no': room_no,
                    'room_type': room_type,
                    'occupied': used,
                    'capacity': capacity,
                    'free': free,
                })

    return vacant_rooms


@role_required(StaffProfile.ROLE_ADMIN)
@require_GET
def vacant_rooms_view(request):
    return render(request, 'vacant_rooms.html', {
        'vacant_rooms': get_vacant_rooms(),
        'settings': HostelSettings.load(),
    })


@role_required(StaffProfile.ROLE_ADMIN)
@require_http_methods(['GET', 'POST'])
def hostel_settings_view(request):
    settings = HostelSettings.load()
    form = HostelSettingsForm(request.POST or None, instance=settings)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Hostel room settings saved.')
        return redirect('hostel_settings')

    preview = {
        'Single': settings.inventory_for('Single')[:5],
        'Double': settings.inventory_for('Double')[:5],
        'Triple': settings.inventory_for('Triple')[:5],
        'FourSitter': settings.inventory_for('FourSitter')[:5],
    }
    return render(request, 'hostel_settings.html', {
        'form': form,
        'settings': settings,
        'preview': preview,
    })


@role_required(StaffProfile.ROLE_ADMIN)
@require_GET
def available_rooms_api(request):
    room_type = (request.GET.get('room_type') or '').strip()
    exclude = (request.GET.get('exclude') or '').strip() or None
    if room_type not in dict(ROOM_TYPE_CHOICES):
        return JsonResponse({'rooms': []})
    rooms = available_rooms(room_type, exclude_roll_no=exclude)
    return JsonResponse({'rooms': rooms})

@role_required(StaffProfile.ROLE_ADMIN)
@require_http_methods(['GET', 'POST'])
def manage_staff(request):
    form = StaffUserCreateForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        messages.success(
            request,
            f'Created {user.staff_profile.get_role_display()} account: {user.username}',
        )
        return redirect('manage_staff')

    staff_users = (
        StaffProfile.objects.select_related('user')
        .exclude(role=StaffProfile.ROLE_ADMIN)
        .order_by('role', 'user__username')
    )
    return render(request, 'manage_staff.html', {
        'form': form,
        'staff_users': staff_users,
    })


@role_required(StaffProfile.ROLE_ADMIN)
@require_POST
def toggle_staff_active(request, user_id):
    from django.contrib.auth.models import User
    user = get_object_or_404(User, pk=user_id)
    if user.is_superuser or user.pk == request.user.pk:
        messages.error(request, 'You cannot deactivate this account.')
        return redirect('manage_staff')
    if not hasattr(user, 'staff_profile'):
        messages.error(request, 'User has no staff profile.')
        return redirect('manage_staff')
    user.is_active = not user.is_active
    user.save(update_fields=['is_active'])
    state = 'activated' if user.is_active else 'deactivated'
    messages.success(request, f'{user.username} {state}.')
    return redirect('manage_staff')
