from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from .models import User


class UserSerializer(serializers.ModelSerializer):
    """Serializer for displaying user details."""

    class Meta:
        model = User
        fields = ('id', 'name', 'email')
        read_only_fields = ('id', 'name', 'email')


class RegisterSerializer(serializers.ModelSerializer):
    """Serializer for registering a new user."""

    name = serializers.CharField(max_length=255, required=True, allow_blank=False)
    email = serializers.EmailField(max_length=255, required=True)
    password = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'},
    )

    class Meta:
        model = User
        fields = ('id', 'name', 'email', 'password')
        extra_kwargs = {
            'password': {'write_only': True},
        }

    def validate_name(self, value):
        stripped = value.strip()
        if not stripped:
            raise serializers.ValidationError("Name cannot be blank.")
        return stripped

    def validate_email(self, value):
        normalized_email = value.strip().lower()
        if User.objects.filter(email=normalized_email).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return normalized_email

    def validate_password(self, value):
        try:
            validate_password(value)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(list(exc.messages))
        return value

    def validate(self, attrs):
        # Validate password similarity against user attributes
        if 'password' in attrs:
            user = User(email=attrs.get('email', ''), name=attrs.get('name', ''))
            try:
                validate_password(attrs['password'], user=user)
            except DjangoValidationError as exc:
                raise serializers.ValidationError({'password': list(exc.messages)})
        return attrs

    def create(self, validated_data):
        return User.objects.create_user(
            email=validated_data['email'],
            name=validated_data['name'],
            password=validated_data['password'],
        )


class LoginSerializer(serializers.Serializer):
    """Serializer for authenticating a user via email and password."""

    email = serializers.EmailField(required=True)
    password = serializers.CharField(
        required=True,
        write_only=True,
        style={'input_type': 'password'},
        trim_whitespace=False,
    )

    def validate(self, attrs):
        email = attrs.get('email', '')
        if email:
            email = email.strip().lower()
        password = attrs.get('password')

        request = self.context.get('request')
        user = authenticate(request=request, email=email, password=password)

        if not user:
            raise serializers.ValidationError('No active account found with the given credentials')

        if not user.is_active:
            raise serializers.ValidationError('User account is disabled.')

        attrs['user'] = user
        return attrs
