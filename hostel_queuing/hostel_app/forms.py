# forms.py
from django import forms
from .models import Student

class StudentForm(forms.ModelForm):
    class Meta:
        model = Student
        fields = ['uni_roll_no', 'name', 'father_name', 'father_phone_no', 'phone_no', 
                  'room_no', 'room_type', 'hostel_type', 'state', 'branch', 'qr_code','address','city']

    branch = forms.ChoiceField(choices=Student._meta.get_field('branch').choices, required=True)

    # Optionally, you can add CSS for styling
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['branch'].widget.attrs.update({'class': 'form-control'})
        self.fields['address'].widget.attrs.update({'class': 'form-control'})
        self.fields['city'].widget.attrs.update({'class': 'form-control'})