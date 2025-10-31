from django.db import models
from django.core.validators import RegexValidator
from django.core.exceptions import ValidationError
from django.utils import timezone  
from django.utils.timezone import now# Corrected import for timezone
from datetime import datetime
from django.core.exceptions import ValidationError

# Define choices for your fields
ROOM_TYPE_CHOICES = [
    ('Single', 'Single'),
    ('Double', 'Double'),
    ('Triple', 'Triple'),
]

HOSTEL_TYPE_CHOICES = [
    ('Boys', 'Boys'),
    ('Girls', 'Girls'),
]

STATE_CHOICES = [
    ('Andhra Pradesh', 'Andhra Pradesh'),
    ('Telangana', 'Telangana'),
    # Add more states as needed
]

BRANCH_CHOICES = [
    ('CSE', 'Computer Science and Engineering'),
    ('ECE', 'Electronics and Communication Engineering'),
    ('EEE', 'Electrical and Electronics Engineering'),
    ('ME', 'Mechanical Engineering'),
    ('CE', 'Civil Engineering'),
    # Add more branches as needed
]

class Admin(models.Model):  # Conventionally use `Admin` instead of lowercase `admin`
    username = models.CharField(max_length=50)
    password = models.CharField(max_length=20)
    name = models.CharField(max_length=50)

    def __str__(self):
        return f"{self.name} - {self.username} ({self.password})"





class Student(models.Model):
    branch = models.CharField(
        max_length=100,
        choices=BRANCH_CHOICES,
        help_text="Select your branch"
    )
    uni_roll_no = models.CharField(
        max_length=7,  # Limit to 7 characters
        primary_key=True,
        unique=True,
        validators=[
            RegexValidator(
                regex=r'^\d{7}$',  # Ensures exactly 7 digits
                message="University Roll Number must be exactly 7 digits and contain only numbers."
            )
        ],
        help_text="Enter your University Roll Number (exactly 7 digits)"
    )
    name = models.CharField(
        max_length=45,
        help_text="Enter your name"
    )
    father_name = models.CharField(
        max_length=45,
        help_text="Enter your father's name"
    )
    father_phone_no = models.CharField(
        max_length=10,
        unique=True,  # Ensures no duplicate father's phone numbers
        validators=[
            RegexValidator(
                regex=r'^\d{10}$',  # Ensures exactly 10 digits
                message="Father's phone number must be 10 digits."
            )
        ],
        help_text="Enter your father's phone number (10 digits)"
    )
    phone_no = models.CharField(
        max_length=10,
        unique=True,  # Ensures no duplicate phone numbers
        validators=[
            RegexValidator(
                regex=r'^\d{10}$',  # Ensures exactly 10 digits
                message="Phone number must be 10 digits."
            )
        ],
        help_text="Enter your phone number (10 digits)"
    )
    room_no = models.CharField(
        max_length=45,
        help_text="Enter your room number"
    )
    room_type = models.CharField(
        max_length=45,
        choices=ROOM_TYPE_CHOICES,
        help_text="Select your room type"
    )
    hostel_type = models.CharField(
        max_length=45,
        choices=HOSTEL_TYPE_CHOICES,
        help_text="Select your hostel type"
    )
    state = models.CharField(
        max_length=45,
        choices=STATE_CHOICES,
        help_text="Select your state"
    )
    city = models.CharField(
        max_length=100, 
        default=" ", # Adjust max_length as necessary
        help_text="Enter your city"
    )
    address = models.TextField(default=" ",
        help_text="Enter your full address"
    )
    qr_code = models.ImageField(upload_to='qr_codes/', blank=True, null=True)
    qr_code_data = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return f"{self.name} ({self.uni_roll_no})"

    def save_qr_code(self, qr_code_image):
        self.qr_code = qr_code_image

    def clean(self):
        # Check room type constraints
        students_in_room = Student.objects.filter(room_no=self.room_no)

        # Check if room type conflicts with existing allocations
        if students_in_room.exists():
            existing_room_type = students_in_room.first().room_type
            if existing_room_type != self.room_type:
                raise ValidationError(
                    f"Room {self.room_no} is already allocated as '{existing_room_type}' type and cannot be re-allocated as '{self.room_type}'."
                )

        # Validate the maximum occupancy per room type
        if self.room_type == "Single" and students_in_room.exclude(uni_roll_no=self.uni_roll_no).count() >= 1:
            raise ValidationError(f"Room {self.room_no} can only have one occupant for 'Single' room type.")
        
        if self.room_type == "Double" and students_in_room.exclude(uni_roll_no=self.uni_roll_no).count() >= 2:
            raise ValidationError(f"Room {self.room_no} can only have two occupants for 'Double' room type.")
        
        if self.room_type == "Triple" and students_in_room.exclude(uni_roll_no=self.uni_roll_no).count() >= 3:
            raise ValidationError(f"Room {self.room_no} can only have three occupants for 'Triple' room type.")
    
    def save(self, *args, **kwargs):
        # Run clean method before saving
        self.clean()
        super().save(*args, **kwargs)



class Attendance(models.Model):
    uni_roll_no = models.CharField(max_length=20, default='unknown')
    date = models.DateField(default=datetime.now)
    time_in = models.TimeField(null=True, blank=True)
    time_out = models.TimeField(null=True, blank=True)
    status = models.CharField(max_length=10, default='Absent')

    def __str__(self):
        return f"{self.uni_roll_no} - {self.date}"
class MessAttendance(models.Model):
    uni_roll_no = models.CharField(max_length=20)
    meal = models.CharField(max_length=20, choices=[('breakfast', 'Breakfast'), ('lunch', 'Lunch'), ('dinner', 'Dinner')])
    date = models.DateField(auto_now_add=True)
    status = models.CharField(max_length=10, default='Present')

    def __str__(self):
        return f"{self.uni_roll_no} - {self.meal} - {self.date}"
class MealEntry(models.Model):
    uni_roll_no = models.CharField(max_length=15)  # Student unique roll number
    meal = models.CharField(max_length=50)        # Meal type (e.g., Breakfast, Lunch, Dinner)
    date= models.DateTimeField(auto_now_add=True)  # Record when the entry was made
    


    def __str__(self):
        return f"{self.uni_roll_no} - {self.meal} - {self.date}"