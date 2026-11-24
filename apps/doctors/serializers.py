from rest_framework import serializers

from .models import Doctor


class DoctorSerializer(serializers.ModelSerializer):
    email = serializers.EmailField()

    class Meta:
        model = Doctor
        fields = [
            'id',
            'name',
            'specialization',
            'email',
            'phone',
            'years_of_experience',
            'created_by',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_by', 'created_at', 'updated_at']

    def validate_name(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("Name is required.")
        return value.strip()

    def validate_specialization(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("Specialization is required.")
        return value.strip()

    def validate_email(self, value):
        normalized_email = value.lower().strip()
        qs = Doctor.objects.filter(email__iexact=normalized_email)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("A doctor with this email already exists.")
        return normalized_email

    def validate_phone(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("Phone is required.")
        return value.strip()

    def validate_years_of_experience(self, value):
        if value < 0:
            raise serializers.ValidationError("Years of experience must be non-negative.")
        return value
