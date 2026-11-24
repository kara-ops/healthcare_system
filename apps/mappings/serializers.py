from rest_framework import serializers
from rest_framework.exceptions import NotFound, ValidationError

from apps.patients.models import Patient
from apps.doctors.models import Doctor
from .models import PatientDoctorMapping


class MappingCreateSerializer(serializers.Serializer):
    patient_id = serializers.IntegerField(write_only=True)
    doctor_id = serializers.IntegerField(write_only=True)

    def validate_patient_id(self, value):
        request = self.context.get('request')
        user = request.user if request else None
        patient = Patient.objects.filter(id=value).first()
        if not patient or (user and user.is_authenticated and patient.created_by != user):
            raise serializers.ValidationError("Patient not found")
        return value

    def validate_doctor_id(self, value):
        if not Doctor.objects.filter(id=value).exists():
            raise serializers.ValidationError("Doctor not found")
        return value

    def validate(self, attrs):
        patient_id = attrs.get('patient_id')
        doctor_id = attrs.get('doctor_id')
        if patient_id and doctor_id:
            if PatientDoctorMapping.objects.filter(patient_id=patient_id, doctor_id=doctor_id).exists():
                raise serializers.ValidationError("This doctor is already assigned to this patient")
        return attrs

    def create(self, validated_data):
        return PatientDoctorMapping.objects.create(
            patient_id=validated_data['patient_id'],
            doctor_id=validated_data['doctor_id'],
        )


class MappingReadSerializer(serializers.ModelSerializer):
    patient_id = serializers.IntegerField(read_only=True)
    doctor_id = serializers.IntegerField(read_only=True)
    patient_name = serializers.CharField(source='patient.name', read_only=True)
    doctor_name = serializers.CharField(source='doctor.name', read_only=True)

    class Meta:
        model = PatientDoctorMapping
        fields = [
            'id',
            'patient_id',
            'doctor_id',
            'patient_name',
            'doctor_name',
            'assigned_at',
        ]
        read_only_fields = fields
