from rest_framework import serializers

from .models import Patient


class PatientSerializer(serializers.ModelSerializer):
    medical_history = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        default='',
    )

    class Meta:
        model = Patient
        fields = [
            'id',
            'name',
            'age',
            'gender',
            'phone',
            'address',
            'medical_history',
            'created_by',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_by', 'created_at', 'updated_at']

    def validate_name(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("Name is required.")
        return value.strip()

    def validate_phone(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("Phone is required.")
        return value.strip()

    def validate_address(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("Address is required.")
        return value.strip()

    def validate_age(self, value):
        if value < 1 or value > 150:
            raise serializers.ValidationError("Age must be between 1 and 150.")
        return value

    def validate_gender(self, value):
        valid_genders = [choice[0] for choice in Patient.GENDER_CHOICES]
        if value not in valid_genders:
            raise serializers.ValidationError(
                f"Gender must be one of: {', '.join(valid_genders)}."
            )
        return value

    def validate_medical_history(self, value):
        if value is None:
            return ''
        return value
