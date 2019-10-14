from rest_framework.views import exception_handler
from django.http import HttpResponseForbidden

class CustomException(Exception):
    """Base class for all custom exceptions"""
    pass

class CustomErrorException(CustomException): 
    """Base class for all custom exceptions that is considered a design error"""
    pass

class DataErrorException(CustomException): 
    """Indicating some data in the database is in an unexpected state."""
    pass

class SchemeErrorException(CustomException):
    """Indicating we are attempting to do something not expected due to a design flaw."""
    pass

def custom_exception_handler(exc, context):
    # Call REST framework's default exception handler first,
    # to get the standard error response.
    response = exception_handler(exc, context)

    # Now add the HTTP status code to the response.
    if response is not None:
        response.data['status_code'] = response.status_code

    return response

    # TODO: https://stackoverflow.com/questions/52388361/custom-403-error-page-in-django-rest-framework