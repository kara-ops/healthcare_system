from rest_framework import generics, status
from rest_framework.exceptions import AuthenticationFailed, ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from .serializers import LoginSerializer, RegisterSerializer, UserSerializer


class RegisterView(generics.CreateAPIView):
    """
    POST /api/auth/register/
    Register a new user and return user info with 201 Created.
    """

    permission_classes = [AllowAny]
    serializer_class = RegisterSerializer


class LoginView(APIView):
    """
    POST /api/auth/login/
    Authenticate user credentials and return access/refresh JWT tokens.
    """

    permission_classes = [AllowAny]
    serializer_class = LoginSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data, context={'request': request})
        try:
            serializer.is_valid(raise_exception=True)
        except ValidationError as exc:
            # If authentication failed (credentials invalid), raise AuthenticationFailed
            # so the custom exception handler produces a 401 response with code 'authentication_failed'.
            if 'non_field_errors' in exc.detail:
                raise AuthenticationFailed(str(exc.detail['non_field_errors'][0]))
            raise

        user = serializer.validated_data['user']
        refresh = RefreshToken.for_user(user)

        return Response(
            {
                'access': str(refresh.access_token),
                'refresh': str(refresh),
                'user': UserSerializer(user).data,
            },
            status=status.HTTP_200_OK,
        )
