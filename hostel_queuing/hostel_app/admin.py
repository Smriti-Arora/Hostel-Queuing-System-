from django.contrib import admin

from .models import Attendance, HostelSettings, MealEntry, MessAttendance, StaffProfile, Student


@admin.register(StaffProfile)
class StaffProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'role', 'created_at')
    list_filter = ('role',)
    search_fields = ('user__username',)


@admin.register(HostelSettings)
class HostelSettingsAdmin(admin.ModelAdmin):
    list_display = (
        'single_rooms', 'double_rooms', 'triple_rooms', 'foursitter_rooms', 'updated_at',
    )


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ('uni_roll_no', 'name', 'room_no', 'room_type', 'hostel_type', 'branch', 'has_qr')
    list_filter = ('hostel_type', 'room_type', 'branch', 'state')
    search_fields = ('uni_roll_no', 'name', 'phone_no', 'room_no')
    readonly_fields = ('qr_code_data', 'has_qr')

    @admin.display(boolean=True, description='QR stored')
    def has_qr(self, obj):
        return bool(obj.qr_code)


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ('uni_roll_no', 'date', 'status', 'time_in', 'time_out')
    list_filter = ('status', 'date')
    search_fields = ('uni_roll_no',)


@admin.register(MessAttendance)
class MessAttendanceAdmin(admin.ModelAdmin):
    list_display = ('uni_roll_no', 'meal', 'date', 'status')
    list_filter = ('meal', 'date', 'status')
    search_fields = ('uni_roll_no',)


@admin.register(MealEntry)
class MealEntryAdmin(admin.ModelAdmin):
    list_display = ('uni_roll_no', 'meal', 'date')
    search_fields = ('uni_roll_no',)


admin.site.site_header = 'Hostel Queuing Admin'
admin.site.site_title = 'Hostel Queuing'
admin.site.index_title = 'Operations'
