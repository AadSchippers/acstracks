from django.core import exceptions


class AcsException(Exception):
    pass


class AcsFileNoActivity(AcsException):
    pass


class AcsFileNotValid(AcsException):
    pass
