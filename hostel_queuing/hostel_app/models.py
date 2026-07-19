import base64
from datetime import datetime

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, RegexValidator
from django.db import models
from django.db.models import Count

ROOM_TYPE_CHOICES = [
    ('Single', 'Single (1 student)'),
    ('Double', 'Double (2 students)'),
    ('Triple', 'Triple (3 students)'),
    ('FourSitter', 'Four Sitter (4 students)'),
]

ROOM_TYPE_PREFIX = {
    'Single': 'S',
    'Double': 'D',
    'Triple': 'T',
    'FourSitter': 'F',
}

DEFAULT_CAPACITY = {
    'Single': 1,
    'Double': 2,
    'Triple': 3,
    'FourSitter': 4,
}

HOSTEL_TYPE_CHOICES = [
    ('Boys', 'Boys'),
    ('Girls', 'Girls'),
]

STATE_CHOICES = [
    ('Andhra Pradesh', 'Andhra Pradesh'),
    ('Telangana', 'Telangana'),
]

BRANCH_CHOICES = [
    ('CSE', 'Computer Science and Engineering'),
    ('ECE', 'Electronics and Communication Engineering'),
    ('EEE', 'Electrical and Electronics Engineering'),
    ('ME', 'Mechanical Engineering'),
    ('CE', 'Civil Engineering'),
]


class StaffProfile(models.Model):
    ROLE_ADMIN = 'admin'
    ROLE_GATE = 'gate'
    ROLE_MESS = 'mess'
    ROLE_CHOICES = [
        (ROLE_ADMIN, 'Super Admin'),
        (ROLE_GATE, 'Gate Staff'),
        (ROLE_MESS, 'Mess Staff'),
    ]
    STAFF_CREATE_CHOICES = [
        (ROLE_GATE, 'Gate Staff'),
        (ROLE_MESS, 'Mess Staff'),
    ]

    user = models.OneToOneField(
        'auth.User',
        on_delete=models.CASCADE,
        related_name='staff_profile',
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=ROLE_GATE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Staff profile'
        verbose_name_plural = 'Staff profiles'

    def __str__(self):
        return f'{self.user.username} ({self.get_role_display()})'

    @property
    def is_admin(self):
        return self.role == self.ROLE_ADMIN

    @property
    def is_gate(self):
        return self.role == self.ROLE_GATE

    @property
    def is_mess(self):
        return self.role == self.ROLE_MESS


class HostelSettings(models.Model):
    """Singleton settings for hostel room inventory and capacities."""

    single_rooms = models.PositiveIntegerField(default=10, validators=[MinValueValidator(0)])
    double_rooms = models.PositiveIntegerField(default=20, validators=[MinValueValidator(0)])
    triple_rooms = models.PositiveIntegerField(default=10, validators=[MinValueValidator(0)])
    foursitter_rooms = models.PositiveIntegerField(default=5, validators=[MinValueValidator(0)])

    single_capacity = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])
    double_capacity = models.PositiveIntegerField(default=2, validators=[MinValueValidator(1)])
    triple_capacity = models.PositiveIntegerField(default=3, validators=[MinValueValidator(1)])
    foursitter_capacity = models.PositiveIntegerField(default=4, validators=[MinValueValidator(1)])

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Hostel settings'
        verbose_name_plural = 'Hostel settings'

    def __str__(self):
        return 'Hostel room settings'

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def room_count(self, room_type):
        return {
            'Single': self.single_rooms,
            'Double': self.double_rooms,
            'Triple': self.triple_rooms,
            'FourSitter': self.foursitter_rooms,
        }.get(room_type, 0)

    def capacity_for(self, room_type):
        return {
            'Single': self.single_capacity,
            'Double': self.double_capacity,
            'Triple': self.triple_capacity,
            'FourSitter': self.foursitter_capacity,
        }.get(room_type, DEFAULT_CAPACITY.get(room_type, 1))

    def inventory_for(self, room_type):
        """All configured room numbers for a type, e.g. S01..S10."""
        prefix = ROOM_TYPE_PREFIX.get(room_type)
        count = self.room_count(room_type)
        if not prefix or count <= 0:
            return []
        return [f'{prefix}{i:02d}' for i in range(1, count + 1)]

    def all_inventory(self):
        rooms = {}
        for room_type, _ in ROOM_TYPE_CHOICES:
            for room_no in self.inventory_for(room_type):
                rooms[room_no] = room_type
        return rooms


def available_rooms(room_type, exclude_roll_no=None):
    """Room numbers of a type that still have free beds."""
    settings = HostelSettings.load()
    capacity = settings.capacity_for(room_type)
    inventory = settings.inventory_for(room_type)

    occupied = (
        Student.objects.filter(room_type=room_type, room_no__in=inventory)
        .values('room_no')
        .annotate(count=Count('uni_roll_no'))
    )
    counts = {row['room_no']: row['count'] for row in occupied}

    if exclude_roll_no:
        current = Student.objects.filter(uni_roll_no=exclude_roll_no).first()
        if current and current.room_type == room_type and current.room_no in counts:
            counts[current.room_no] = max(0, counts[current.room_no] - 1)

    result = []
    for room_no in inventory:
        used = counts.get(room_no, 0)
        if used < capacity:
            free = capacity - used
            result.append({
                'room_no': room_no,
                'occupied': used,
                'capacity': capacity,
                'free': free,
                'label': f'{room_no} ({used}/{capacity} occupied · {free} free)',
            })
    return result


class Student(models.Model):
    branch = models.CharField(
        max_length=100,
        choices=BRANCH_CHOICES,
        help_text='Select your branch',
    )
    uni_roll_no = models.CharField(
        max_length=7,
        primary_key=True,
        unique=True,
        validators=[
            RegexValidator(
                regex=r'^\d{7}$',
                message='University Roll Number must be exactly 7 digits and contain only numbers.',
            )
        ],
        help_text='Enter your University Roll Number (exactly 7 digits)',
    )
    name = models.CharField(max_length=45, help_text='Enter your name')
    father_name = models.CharField(max_length=45, help_text="Enter your father's name")
    father_phone_no = models.CharField(
        max_length=10,
        unique=True,
        validators=[
            RegexValidator(
                regex=r'^\d{10}$',
                message="Father's phone number must be 10 digits.",
            )
        ],
        help_text="Enter your father's phone number (10 digits)",
    )
    phone_no = models.CharField(
        max_length=10,
        unique=True,
        validators=[
            RegexValidator(
                regex=r'^\d{10}$',
                message='Phone number must be 10 digits.',
            )
        ],
        help_text='Enter your phone number (10 digits)',
    )
    room_no = models.CharField(max_length=45, help_text='Select your room number')
    room_type = models.CharField(
        max_length=45,
        choices=ROOM_TYPE_CHOICES,
        help_text='Select your room type',
    )
    hostel_type = models.CharField(
        max_length=45,
        choices=HOSTEL_TYPE_CHOICES,
        help_text='Select your hostel type',
    )
    state = models.CharField(
        max_length=45,
        choices=STATE_CHOICES,
        help_text='Select your state',
    )
    city = models.CharField(max_length=100, default=' ', help_text='Enter your city')
    address = models.TextField(default=' ', help_text='Enter your full address')
    qr_code = models.BinaryField(blank=True, null=True, editable=False)
    qr_code_data = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return f'{self.name} ({self.uni_roll_no})'

    @property
    def qr_code_data_uri(self):
        if not self.qr_code:
            return ''
        encoded = base64.b64encode(bytes(self.qr_code)).decode('ascii')
        return f'data:image/png;base64,{encoded}'

    def clean(self):
        if not self.room_no or not self.room_type:
            return

        settings = HostelSettings.load()
        inventory = settings.all_inventory()

        if self.room_no not in inventory:
            raise ValidationError({
                'room_no': f'Room {self.room_no} is not configured in hostel settings.',
            })

        expected_type = inventory[self.room_no]
        if self.room_type != expected_type:
            raise ValidationError({
                'room_type': f'Room {self.room_no} is a {expected_type} room, not {self.room_type}.',
            })

        students_in_room = Student.objects.filter(room_no=self.room_no)
        if students_in_room.exists():
            existing_room_type = students_in_room.first().room_type
            if existing_room_type != self.room_type:
                raise ValidationError(
                    f"Room {self.room_no} is already allocated as '{existing_room_type}' "
                    f"and cannot be re-allocated as '{self.room_type}'."
                )

        capacity = settings.capacity_for(self.room_type)
        occupants = students_in_room.exclude(uni_roll_no=self.uni_roll_no).count()
        if occupants >= capacity:
            raise ValidationError(
                f'Room {self.room_no} is full ({capacity}/{capacity} for {self.room_type}).'
            )

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)


class Attendance(models.Model):
    uni_roll_no = models.CharField(max_length=20, default='unknown')
    date = models.DateField(default=datetime.now)
    time_in = models.TimeField(null=True, blank=True)
    time_out = models.TimeField(null=True, blank=True)
    status = models.CharField(max_length=10, default='Absent')

    def __str__(self):
        return f'{self.uni_roll_no} - {self.date}'


class MessAttendance(models.Model):
    uni_roll_no = models.CharField(max_length=20)
    meal = models.CharField(
        max_length=20,
        choices=[('breakfast', 'Breakfast'), ('lunch', 'Lunch'), ('dinner', 'Dinner')],
    )
    date = models.DateField(auto_now_add=True)
    status = models.CharField(max_length=10, default='Present')

    def __str__(self):
        return f'{self.uni_roll_no} - {self.meal} - {self.date}'


class MealEntry(models.Model):
    uni_roll_no = models.CharField(max_length=15)
    meal = models.CharField(max_length=50)
    date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.uni_roll_no} - {self.meal} - {self.date}'
