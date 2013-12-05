"""Settings for Development Server"""
from {{ project_name }}.settings.common import *   # pylint: disable=W0614,W0401

DEBUG = True
TEMPLATE_DEBUG = DEBUG

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': '{{ project_name }}',
        'USER': 'postgres',
#        'PASSWORD': 'dbpassword',
    }
}

INSTALLED_APPS += (
    'django_nose',
)

# WSGI_APPLICATION = '{{ project_name }}.wsgi.dev.application'

TEST_RUNNER = 'django_nose.NoseTestSuiteRunner'
