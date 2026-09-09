from .base import *  # noqa
from .base import env

SECRET_KEY = env("DJANGO_SECRET_KEY")

ADMINS = [("Himanhsu", "work.himanshu62@gmail.com")]  # this is for

# TODO add domain names of the production server
CSRF_TRUSTED_ORIGINS = [""]
