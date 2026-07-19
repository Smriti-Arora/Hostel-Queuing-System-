from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password

from .models import HostelSettings, StaffProfile, Student, available_rooms


class LoginForm(AuthenticationForm):
    username = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'Username',
            'autocomplete': 'username',
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder': 'Password',
            'autocomplete': 'current-password',
        })
    )


class StaffUserCreateForm(forms.Form):
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={'class': 'form-input', 'autocomplete': 'off'}),
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-input', 'autocomplete': 'new-password'}),
    )
    password_confirm = forms.CharField(
        label='Confirm password',
        widget=forms.PasswordInput(attrs={'class': 'form-input', 'autocomplete': 'new-password'}),
    )
    role = forms.ChoiceField(
        choices=StaffProfile.STAFF_CREATE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'}),
    )

    def clean_username(self):
        username = self.cleaned_data['username'].strip()
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError('That username is already taken.')
        return username

    def clean_password(self):
        password = self.cleaned_data['password']
        validate_password(password)
        return password

    def clean(self):
        cleaned = super().clean()
        password = cleaned.get('password')
        confirm = cleaned.get('password_confirm')
        if password and confirm and password != confirm:
            self.add_error('password_confirm', 'Passwords do not match.')
        return cleaned

    def save(self):
        user = User.objects.create_user(
            username=self.cleaned_data['username'],
            password=self.cleaned_data['password'],
        )
        StaffProfile.objects.create(user=user, role=self.cleaned_data['role'])
        return user


class HostelSettingsForm(forms.ModelForm):
    class Meta:
        model = HostelSettings
        fields = [
            'single_rooms', 'double_rooms', 'triple_rooms', 'foursitter_rooms',
            'single_capacity', 'double_capacity', 'triple_capacity', 'foursitter_capacity',
        ]
        labels = {
            'single_rooms': 'Number of single rooms',
            'double_rooms': 'Number of double rooms',
            'triple_rooms': 'Number of triple rooms',
            'foursitter_rooms': 'Number of four-sitter rooms',
            'single_capacity': 'Students per single room',
            'double_capacity': 'Students per double room',
            'triple_capacity': 'Students per triple room',
            'foursitter_capacity': 'Students per four-sitter room',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault('class', 'form-input')
            field.widget.attrs.setdefault('min', '0')


class StudentForm(forms.ModelForm):
    room_no = forms.ChoiceField(choices=[], required=True)

    class Meta:
        model = Student
        fields = [
            'uni_roll_no', 'name', 'father_name', 'father_phone_no', 'phone_no',
            'room_type', 'room_no', 'hostel_type', 'state', 'branch', 'address', 'city',
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            css = 'form-input'
            if isinstance(field.widget, forms.Select):
                css = 'form-select'
            elif isinstance(field.widget, forms.Textarea):
                css = 'form-textarea'
            field.widget.attrs.setdefault('class', css)

        if self.instance and self.instance.pk:
            self.fields['uni_roll_no'].disabled = True

        room_type = ''
        if self.data.get('room_type'):
            room_type = self.data.get('room_type')
        elif self.initial.get('room_type'):
            room_type = self.initial.get('room_type')
        elif self.instance and self.instance.pk:
            room_type = self.instance.room_type

        exclude = self.instance.pk if self.instance and self.instance.pk else None
        choices = [('', 'Select room type first')]
        if room_type:
            rooms = available_rooms(room_type, exclude_roll_no=exclude)
            choices = [('', 'Select room number')] + [
                (r['room_no'], r['label']) for r in rooms
            ]
            if (
                self.instance
                and self.instance.pk
                and self.instance.room_type == room_type
                and self.instance.room_no
                and self.instance.room_no not in dict(choices)
            ):
                choices.append((self.instance.room_no, f'{self.instance.room_no} (current)'))

        self.fields['room_no'].choices = choices
        self.fields['room_type'].widget.attrs['id'] = 'id_room_type'
        self.fields['room_no'].widget.attrs['id'] = 'id_room_no'

    def clean(self):
        cleaned = super().clean()
        room_type = cleaned.get('room_type')
        room_no = cleaned.get('room_no')
        if room_type and room_no:
            exclude = self.instance.pk if self.instance and self.instance.pk else None
            valid = {r['room_no'] for r in available_rooms(room_type, exclude_roll_no=exclude)}
            if (
                self.instance
                and self.instance.pk
                and self.instance.room_no == room_no
                and self.instance.room_type == room_type
            ):
                valid.add(room_no)
            if room_no not in valid:
                self.add_error('room_no', 'Selected room is full or not available for this type.')
        return cleaned
