from datetime import time, timedelta
import datetime
import io
from openpyxl import Workbook
import json
from openpyxl import Workbook
from django.http import HttpResponse
from .models import Student  # Make sure to import your Student model

import os
import base64
from django.core.files.storage import default_storage
from django.conf import settings
from django.test import Client
import qrcode
import cv2
import numpy as np
from django.shortcuts import render, redirect, get_object_or_404
from .models import Student,Attendance,MessAttendance
from .forms import  StudentForm
from django.http import HttpResponse, JsonResponse
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.core.files import File
from django.utils.timezone import now
from django.http import Http404
import pyzbar.pyzbar as pyzbar
from datetime import date
from .models import MealEntry
from datetime import datetime


def generate_qr_code(student):
    """Helper function to generate and save QR code for a student."""
    try:
        # Prepare QR code data
        qr_data = f"{student.uni_roll_no},{student.name}"
        qr = qrcode.make(qr_data)

        # Define the QR code file path
        qr_code_dir = os.path.join(settings.MEDIA_ROOT, "qr_codes")
        os.makedirs(qr_code_dir, exist_ok=True)  # Ensure the directory exists
        qr_code_path = os.path.join(qr_code_dir, f"{student.uni_roll_no}.png")

        # Save the QR code image
        qr.save(qr_code_path)

        # Save QR code to ImageField in the Student model
        with open(qr_code_path, "rb") as qr_file:
            student.qr_code.save(f"{student.uni_roll_no}.png", File(qr_file), save=True)

        return True  # Indicate success
    except Exception as e:
        print(f"Error generating QR code: {e}")
        return False  # Indicate failure

@csrf_exempt  # Disable CSRF for testing only
def regenerate_qr_code(request, uni_roll_no):
    # Retrieve the student instance
    student = get_object_or_404(Student, uni_roll_no=uni_roll_no)

    if request.method == 'POST':
        # Generate a new QR code for the student
        success = generate_qr_code(student)  # Use your helper function to generate the QR code
        if success:
            qr_code_url = student.qr_code.url  # Get the URL of the saved QR code image
            return JsonResponse({
                'success': True,
                'qr_code': qr_code_url  # Send the URL to the frontend
            })
        else:
            return JsonResponse({
                'success': False,
                'message': 'An error occurred while generating the QR code.'
            })

    return JsonResponse({
        'success': False,
        'message': 'Invalid request method.'
    })
def student_list(request):
    students = Student.objects.all()  # Fetch all students
    form = None

    if request.method == "POST":
        # If 'uni_roll_no' is in request.POST, update an existing student
        if 'uni_roll_no' in request.POST:
            uni_roll_no = request.POST.get('uni_roll_no')
            student_to_update = get_object_or_404(Student, uni_roll_no=uni_roll_no)
            form = StudentForm(request.POST, instance=student_to_update)  # Populate form with existing data
        else:
            # Else, we are registering a new student
            form = StudentForm(request.POST)  # New student form
    
        if form.is_valid():
            student = form.save(commit=False)
            student.save()  # Save the student to the database
            if 'uni_roll_no' in request.POST:
                messages.success(request, 'Student updated successfully!')
            else:
                messages.success(request, 'Student registered successfully!')

            # Generate QR code after saving student data
            generate_qr_code(student)

            return redirect('student_list')  # Redirect to avoid re-submission of form

    else:
        # For GET request, provide an empty form for a new student
        form = StudentForm() 

    return render(request, 'student_list.html', {'form': form, 'students': students})

    context = {
        'students': students,
        'form': form,
    }
    return render(request, 'student_list.html', context)
def register_student(request):
    if request.method == 'POST':
        form = StudentForm(request.POST, request.FILES)
        if form.is_valid():
            student = form.save()  # Save the student object
            generate_qr_code(student)  # Pass only the student object
            return redirect('student_list')
    else:
        form = StudentForm()

    return render(request, 'student_form.html', {'form': form})

def student_detail(request, uni_roll_no):
    """Display detailed information about a specific student."""
    student = get_object_or_404(Student, uni_roll_no=uni_roll_no)
    return render(request, 'student_detail.html', {'student': student})

def update_student(request, uni_roll_no):
    student = get_object_or_404(Student, uni_roll_no=uni_roll_no)

    if request.method == 'POST':
        form = StudentForm(request.POST, instance=student)
        if form.is_valid():
            form.save()  # The 'uni_roll_no' field will not be updated because it is disabled
            messages.success(request, 'Student updated successfully!')
            return redirect('student_list')  # Redirect to the student list view
        else:
            messages.error(request, 'Error updating student. Please correct the errors below.')

    form = StudentForm(instance=student)
    return render(request, 'student_form.html', {'form': form, 'student': student})
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib import messages
from django.core.files.storage import default_storage
from .models import Student

from django.db import transaction

def delete_student(request, uni_roll_no):
    """Delete a student and their associated QR code."""
    student = get_object_or_404(Student, uni_roll_no=uni_roll_no)
    if request.method == 'POST':
        try:
            # Delete QR code if it exists
            if student.qr_code:
                qr_code_path = student.qr_code.name
                if default_storage.exists(qr_code_path):
                    default_storage.delete(qr_code_path)

            # Delete the student
            student.delete()
            messages.success(request, "Student deleted successfully.")
            return redirect('student_list')

        except Exception as e:
            messages.error(request, f"There was an error: {e}")
            return redirect('student_list')

    return render(request, 'confirm_delete.html', {'student': student})




def reset_form(request):
    """Reset the form and redirect to student list."""
    messages.info(request, "Form has been reset.")
    return redirect('student_list')


def view_qr_code(request, uni_roll_no):
    student = get_object_or_404(Student, uni_roll_no=uni_roll_no)
    qr_code_path = os.path.join('media', 'qr_codes', f"{uni_roll_no}.png")  # Adjust path as necessary
    return render(request, 'view_qr_code.html', {'student': student, 'qr_code_path': qr_code_path})
from datetime import datetime, time

from datetime import datetime, time

from datetime import datetime, time



from datetime import datetime, time
from django.http import JsonResponse
from django.shortcuts import render
from .models import Student, Attendance

def scan_qr(request):
    if request.method == "POST":
        import json
        data = json.loads(request.body.decode("utf-8"))
        qr_data = data.get("qr_data")  # Extract data from POST request

        # Assuming the QR data format is: "123,Smriti Arora"
        uni_roll_no = qr_data.split(",")[0]  # Extract only the uni_roll_no

        try:
            student = Student.objects.get(uni_roll_no=uni_roll_no)  # Query by uni_roll_no
            today = datetime.now().date()  # Get today's date
            attendance, created = Attendance.objects.get_or_create(
                uni_roll_no=uni_roll_no, date=today  # Use uni_roll_no as a string
            )

            current_time = datetime.now().time()  # Get the current time
            cutoff_time_night = time(22, 0)  # 10 PM cutoff
            cutoff_time_morning = time(7, 0)  # 7 AM cutoff

            # Restrict entry/exit between 10 PM and 7 AM
            if cutoff_time_night <= current_time or current_time < cutoff_time_morning:
                return JsonResponse({
                    "message": f"{student.name} cannot enter or exit between 10 PM and 7 AM.",
                    "success": False
                })

            # Toggle attendance status
            if attendance.status == 'Absent':
                # Mark the student as Present
                attendance.time_in = current_time
                attendance.time_out = None  # Clear exit time for re-entry
                attendance.status = 'Present'
                attendance.save()
                return JsonResponse({"message": f"{student.name} marked Present.", "success": True})
            elif attendance.status == 'Present':
                # Mark the student as Absent
                attendance.time_out = current_time
                attendance.status = 'Absent'
                attendance.save()
                return JsonResponse({"message": f"{student.name} marked Absent.", "success": True})

        except Student.DoesNotExist:
            return JsonResponse({"message": "Unauthorized user.", "success": False})

    return render(request, 'scan_qr.html')



import logging
logger = logging.getLogger(__name__)

@csrf_exempt
def validate_qr_code(request):
    if request.method == 'POST':
        qr_code_data = request.POST.get('qr_code', '')
        logger.warning(f"Received QR Code Data: {qr_code_data}")  # Log the incoming QR code

        try:
            # Check if any student has this QR code
            student = Student.objects.get(qr_code_data=qr_code_data)
            return JsonResponse({'valid': True})
        except Student.DoesNotExist:
            logger.warning(f"No student found for QR Code: {qr_code_data}")  # Log the failure case
            return JsonResponse({'valid': False})
    return JsonResponse({'valid': False}, status=400)


from django.shortcuts import render # type: ignore
import mysql.connector as sql
em=''
pwd=''
# Create your views here.
def loginaction(request):
    global em,pwd
    if request.method=="POST":
        # m=sql.connect(host="localhost",user="root",passwd="sonu@2002",database='website')
        # cursor=m.cursor()
        d=request.POST
        for key,Value in d.items():    
            if key=="username":
                em=Value
            if key=="password":
                pwd=Value  

        # c="select * from users where email='{}' and password='{}'".format(em,pwd)
        # cursor.execute(c)
        # t=tuple(cursor.fetchall())
        print(em,pwd)
        if (em=="admin" and pwd=="1234"):
        
            return redirect('/home')
        else:
            print("fail")
            return render(request,"login.html")

    return render(request,'login.html')

from django.shortcuts import render # type: ignore
import mysql.connector as sql 
fn=''
ln=''
s=''
em=''
pwd=''
# Create your views here.
def signaction(request):
    global fn,ln,s,em,pwd
    if request.method=="POST":
        m=sql.connect(host="localhost",user="root",passwd="sonu@2002",database='website')
        cursor=m.cursor()
        d=request.POST
        for key,Value in d.items():
            if key=="first_name":
                fn=Value
            if key=="last_name":
                ln=Value
            if key=="sex":
                s=Value        
            if key=="email":
                em=Value
            if key=="password":
                pwd=Value  

        c="insert into users values('{}','{}','{}','{}','{}')".format(fn,ln,s,em,pwd)
        cursor.execute(c)
        m.commit()         
    return render(request,'register.html') 
from datetime import datetime, time
from django.http import JsonResponse
from django.utils.timezone import now
import pytz

def scan_qr_for_mess(request):
    if request.method == 'POST':
        # Get the scanned QR code and meal details
        uni_roll_no = request.POST.get('uni_roll_no')
        meal = request.POST.get('meal')

        # Define meal time ranges in IST (Indian Standard Time)
        india_tz = pytz.timezone("Asia/Kolkata")
        current_time = now().astimezone(india_tz).time()

        breakfast_start = time(7, 30)
        breakfast_end = time(9, 0)
        lunch_start = time(12, 30)
        lunch_end = time(14, 0)
        dinner_start = time(19, 30)
        dinner_end = time(21, 0)

        # Validate meal times
        if (
            (meal == "breakfast" and not (breakfast_start <= current_time <= breakfast_end)) or
            (meal == "lunch" and not (lunch_start <= current_time <= lunch_end)) or
            (meal == "dinner" and not (dinner_start <= current_time <= dinner_end))
        ):
            return JsonResponse({'message': f'Invalid time for {meal}. Attendance not marked.'})

        # Check if attendance has already been marked for this student and meal today
        from datetime import date
        existing_record = MessAttendance.objects.filter(
            uni_roll_no=uni_roll_no,
            meal=meal,
            date=date.today()
        ).first()

        if existing_record:
            return JsonResponse({'message': 'Attendance already marked for this meal today.'})
        else:
            # Mark attendance if not already present
            MessAttendance.objects.create(uni_roll_no=uni_roll_no, meal=meal, date=date.today())
            return JsonResponse({'message': 'Attendance marked successfully!'})

    return render(request, 'scan_qr_for_mess.html')


def mess_entry_list(request):
    meal_entries = MessAttendance.objects.all().order_by('-date') 
    print(meal_entries) # Order by latest entries
    return render(request, 'mess_entry_list.html', {'meal_entries': meal_entries})
def process_qr_code(request):
    if request.method == 'POST':
        uni_roll_no = request.POST.get('uni_roll_no')
        meal = request.POST.get('meal')

        # Save to MealEntry model
        MealEntry.objects.create(uni_roll_no=uni_roll_no, meal=meal)

        return redirect('mess_entry_list')
    
from django.utils import timezone
from .models import Student, Attendance

def attendance_overview(request):
    today = timezone.now().date()  # Get today's date
    current_time = timezone.now().time()  # Get current time

    # Fetch all students and their attendance for today
    students = Student.objects.all()
    present_students = []
    absent_students = []

    for student in students:
        # Use uni_roll_no to filter attendance for the day
        attendance = Attendance.objects.filter(uni_roll_no=student.uni_roll_no, date=today).first()
        if attendance:
            if attendance.status == 'Present':
                present_students.append(student)
            else:
                absent_students.append(student)
        else:
            # If no attendance record exists, consider the student as absent
            absent_students.append(student)

    context = {
        'present_students': present_students,
        'absent_students': absent_students,
        'today': today,
        'current_time': current_time,
    }

    return render(request, 'attendance_overview.html', context)


    
from django.db.models import Count
from django.shortcuts import render
from .models import Student

def get_vacant_rooms():
    # Define room capacities
    ROOM_CAPACITY = {
        "Single": 1,
        "Double": 2,
        "Triple": 3,
    }

    # Annotate each room with its current occupancy
    rooms = (
        Student.objects.values('room_no', 'room_type')  # Group by room_no and room_type
        .annotate(
            current_occupants=Count('uni_roll_no'),  # Count students in each room
        )
    )

    # Dictionaries to store the count of vacant rooms, vacant spaces, and room numbers for each room type
    vacant_rooms = {
        "single_vacant": 0,
        "double_vacant": 0,
        "triple_vacant": 0,
        "single_vacant_space": 0,
        "double_vacant_space": 0,
        "triple_vacant_space": 0,
        "single_room_numbers": [],
        "double_room_numbers": [],
        "triple_room_numbers": [],
    }

    # Loop through each room and calculate vacant spaces and room numbers
    for room in rooms:
        room_type = room['room_type']
        max_capacity = ROOM_CAPACITY.get(room_type, 0)  # Fetch max capacity for the room type
        current_occupants = room['current_occupants']
        vacant_space = max_capacity - current_occupants

        # Only include rooms with vacant space
        if vacant_space > 0:
            if room_type == "Single":
                vacant_rooms["single_vacant"] += 1
                vacant_rooms["single_vacant_space"] += vacant_space
                vacant_rooms["single_room_numbers"].append(room['room_no'])
            elif room_type == "Double":
                vacant_rooms["double_vacant"] += 1
                vacant_rooms["double_vacant_space"] += vacant_space
                vacant_rooms["double_room_numbers"].append(room['room_no'])
            elif room_type == "Triple":
                vacant_rooms["triple_vacant"] += 1
                vacant_rooms["triple_vacant_space"] += vacant_space
                vacant_rooms["triple_room_numbers"].append(room['room_no'])

    return vacant_rooms


def vacant_rooms_view(request):
    # Fetch vacant room data
    vacant_rooms = get_vacant_rooms()

    # Render the data to the template
    return render(request, 'vacant_rooms.html', {'vacant_rooms': vacant_rooms})
from django.db.models import Count

from django.db.models import Count
from .models import MessAttendance  # Ensure your model is imported



def mess_entry_records(request):
    # Fetch all meal attendance records
    meal_entries = MessAttendance.objects.all()

    # Count students for each meal
    breakfast_count = meal_entries.filter(meal="breakfast").count()
    lunch_count = meal_entries.filter(meal="lunch").count()
    dinner_count = meal_entries.filter(meal="dinner").count()

    # Pass counts and meal entries to the template
    context = {
        'meal_entries': meal_entries,
        'breakfast_count': breakfast_count,
        'lunch_count': lunch_count,
        'dinner_count': dinner_count,
    }
    return render(request, 'mess_entry_list.html', context)





