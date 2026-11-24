from django.db import IntegrityError
from rest_framework import permissions, status
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.patients.models import Patient
from .models import PatientDoctorMapping
from .serializers import MappingCreateSerializer, MappingReadSerializer


class MappingListCreateView(APIView):
    """
    GET /api/mappings/
    List all mappings whose patient belongs to the authenticated user.

    POST /api/mappings/
    Assign a doctor to a patient owned by the authenticated user.
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        mappings = (
            PatientDoctorMapping.objects.filter(patient__created_by=request.user)
            .select_related('patient', 'doctor')
            .order_by('-assigned_at')
        )
        serializer = MappingReadSerializer(mappings, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = MappingCreateSerializer(
            data=request.data, context={'request': request}
        )
        if not serializer.is_valid():
            errors = serializer.errors

            # Patient not found or not owned by user must return 404 as per API contract
            if 'patient_id' in errors:
                for err in errors['patient_id']:
                    if 'not found' in str(err).lower():
                        raise NotFound("Patient not found")

            # Duplicate mapping must return 400 with code 'duplicate_mapping'
            non_field_errors = errors.get('non_field_errors', [])
            if any('already assigned' in str(err).lower() for err in non_field_errors):
                return Response(
                    {
                        "error": {
                            "code": "duplicate_mapping",
                            "message": "This doctor is already assigned to this patient",
                            "details": {},
                        }
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            raise ValidationError(errors)

        try:
            mapping = serializer.save()
        except IntegrityError:
            return Response(
                {
                    "error": {
                        "code": "duplicate_mapping",
                        "message": "This doctor is already assigned to this patient",
                        "details": {},
                    }
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        read_serializer = MappingReadSerializer(mapping)
        return Response(read_serializer.data, status=status.HTTP_201_CREATED)


class MappingDetailView(APIView):
    """
    Dual-semantics view sharing the /api/mappings/<int:pk>/ route:
    - GET: pk is treated as patient_id -> returns all doctors assigned to that patient
      (only if the patient belongs to request.user, else 404).
    - DELETE: pk is treated as mapping_id -> deletes that specific mapping
      (only if the mapping's patient belongs to request.user, else 404).

    See API_CONTRACT.md section 4.
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        # pk is treated as patient_id
        patient = Patient.objects.filter(id=pk, created_by=request.user).first()
        if not patient:
            raise NotFound("Patient not found")

        mappings = (
            PatientDoctorMapping.objects.filter(patient=patient)
            .select_related('patient', 'doctor')
            .order_by('-assigned_at')
        )
        serializer = MappingReadSerializer(mappings, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def delete(self, request, pk):
        # pk is treated as mapping_id
        mapping = PatientDoctorMapping.objects.filter(
            id=pk, patient__created_by=request.user
        ).first()
        if not mapping:
            raise NotFound("Mapping not found")

        mapping.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# Aliases for explicit imports/references
PatientDoctorsView = MappingDetailView
MappingDeleteView = MappingDetailView
