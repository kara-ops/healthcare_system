from django.http import Http404
from django.core.exceptions import PermissionDenied as DjangoPermissionDenied

from rest_framework import status
from rest_framework.exceptions import (
    APIException,
    AuthenticationFailed,
    MethodNotAllowed,
    NotAuthenticated,
    NotFound,
    PermissionDenied,
    ValidationError,
)
from rest_framework.views import exception_handler


def custom_exception_handler(exc, context):
    """
    Custom DRF exception handler that returns a uniform error envelope:
    {
        "error": {
            "code": "<error_code>",
            "message": "<human-readable message>",
            "details": { ... }
        }
    }
    """
    # Convert Django's Http404 to DRF NotFound
    if isinstance(exc, Http404):
        exc = NotFound(detail=str(exc) if str(exc) else "Not found.")

    # Convert Django's PermissionDenied to DRF PermissionDenied
    if isinstance(exc, DjangoPermissionDenied):
        exc = PermissionDenied(detail=str(exc) if str(exc) else "Permission denied.")

    # Let DRF handle the exception first (sets response status, headers, etc.)
    response = exception_handler(exc, context)

    if response is not None:
        # Determine the error code and message
        if isinstance(exc, ValidationError):
            code = 'validation_error'
            message = 'Validation failed.'
            details = response.data
        elif isinstance(exc, (AuthenticationFailed, NotAuthenticated)):
            code = 'authentication_failed'
            message = _extract_message(response.data)
            details = {}
        elif isinstance(exc, PermissionDenied):
            code = 'permission_denied'
            message = _extract_message(response.data)
            details = {}
        elif isinstance(exc, NotFound):
            code = 'not_found'
            message = _extract_message(response.data)
            details = {}
        elif isinstance(exc, MethodNotAllowed):
            code = 'method_not_allowed'
            message = _extract_message(response.data)
            details = {}
        else:
            code = 'server_error'
            message = 'An unexpected error occurred.'
            details = {}

        response.data = {
            'error': {
                'code': code,
                'message': message,
                'details': details,
            }
        }
    else:
        # Unhandled exception — return 500 with generic message (no stack trace)
        from rest_framework.response import Response

        response = Response(
            {
                'error': {
                    'code': 'server_error',
                    'message': 'An unexpected error occurred.',
                    'details': {},
                }
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    return response


def _extract_message(data):
    """Extract a human-readable message from DRF error data."""
    if isinstance(data, dict):
        detail = data.get('detail', '')
        if detail:
            return str(detail)
        # Fallback: join all values
        messages = []
        for value in data.values():
            if isinstance(value, list):
                messages.extend(str(v) for v in value)
            else:
                messages.append(str(value))
        return ' '.join(messages) if messages else 'An error occurred.'
    if isinstance(data, list):
        return ' '.join(str(item) for item in data)
    return str(data)
