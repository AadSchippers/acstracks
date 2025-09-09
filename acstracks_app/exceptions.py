from django.core import exceptions


class AcsException(Exception):
    pass


class AcsFileNoActivity(AcsException):
    pass


class AcsTrackNoLength(AcsException):
    pass


class AcsNoPublicFile(AcsException):
    pass
