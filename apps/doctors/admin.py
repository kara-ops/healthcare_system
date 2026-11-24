from django.contrib import admin

from .models import Doctor


@admin.register(Doctor)
class DoctorAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'name',
        'specialization',
        'email',
        'phone',
        'years_of_experience',
        'created_by',
        'created_at',
    )
    list_filter = ('specialization', 'created_at')
    search_fields = ('name', 'email', 'specialization', 'phone', 'created_by__email')
    readonly_fields = ('created_at', 'updated_at')
