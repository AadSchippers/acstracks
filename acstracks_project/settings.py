"""
Django settings for acstracks_project project.

Generated by 'django-admin startproject' using Django 3.1.

For more information on this file, see
https://docs.djangoproject.com/en/3.1/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/3.1/ref/settings/
"""

from pathlib import Path
import os

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve(strict=True).parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/3.1/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
# SECRET_KEY =

# SECURITY WARNING: don't run with debug turned on in production!
# DEBUG =

ALLOWED_HOSTS = []


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'acstracks_app',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'acstracks_project.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'acstracks_project.wsgi.application'


# Database
# https://docs.djangoproject.com/en/3.1/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}


# Password validation
# https://docs.djangoproject.com/en/3.1/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/3.1/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'Europe/Amsterdam'
GPX_TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/3.1/howto/static-files/

STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'static')

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'acstracks_app/static/media')

MAPS_URL = '/static/media/maps/'
MAPS_ROOT = os.path.join(BASE_DIR, 'acstracks_app/static/media/maps')

COLORSCHEMES = ["giro", "nostalgia", "ocean", "summer"]
DEFAULT_COLORSCHEME = "giro"

# Folium map colours
PRIMARY_COLOR = {
    "giro": "purple",
    "nostalgia": "maroon",
    "ocean": "darkblue",
    "summer": "darkgreen",
}
START_COLOR = {
    "giro": "pink",
    "nostalgia": "orange",
    "ocean": "lightblue",
    "summer": "lightgreen",
    }
END_COLOR = {
    "giro": "darkpurple",
    "nostalgia": "orangered",
    "ocean": "blue",
    "summer": "green",
    }

MAP_LINE_WEIGHT = 2.5
HEATMAP_OPACITY = 0.5
HEATMAP_LINE_WEIGHT = 3.5
NORMAL_OPACITY = 1

NAMESPACE = {'ns': 'http://www.topografix.com/GPX/1/1'}
GPXTPXNAMESPACE = {'gpxtpxns': 'http://www.garmin.com/xmlschemas/TrackPointExtension/v1'}

HEARTRATETAGS = ['heartrate', '{http://www.garmin.com/xmlschemas/TrackPointExtension/v1}hr']
CADENCETAGS = ['cadence', '{http://www.garmin.com/xmlschemas/TrackPointExtension/v1}cad']

# thresholds
SPEEDTHRESHOLD = 3.60
ELEVATIONTHRESHOLD = 0.25
MAXSPEEDCAPPINGFACTOR = 1.25

# heart rate
MAXIMUM_HEART_RATE = 175
RESTING_HEART_RATE = 70
FACTOR_MAXIMUM_ZONE1 = 0.31
FACTOR_MAXIMUM_ZONE2 = 0.48
FACTOR_MAXIMUM_ZONE3 = 0.65
FACTOR_MAXIMUM_ZONE4 = 0.83

# track effort
# effort at 2 hours(7200 sec) and average heartbeat of 150 = 100 (sqrt(7200)*150**2/19091.883092036783) = 100
TRACKEFFORTFACTOR = 19091.8830920368
WEIGHT_ZONE1 = 0.5
WEIGHT_ZONE2 = 0.75
WEIGHT_ZONE3 = 1
WEIGHT_ZONE4 = 1.5
WEIGHT_ZONE5 = 2

from .config import *   # noqa
