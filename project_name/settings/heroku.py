"""Settings for Development Server"""
from {{ project_name }}.settings.common import *   # pylint: disable=W0614,W0401
import dj_database_url #this can use the DATABASE_URL envvar

DEBUG = False
TEMPLATE_DEBUG = DEBUG

VAR_ROOT = '/apps'
MEDIA_ROOT = os.path.join(VAR_ROOT, 'uploads')
STATIC_ROOT = os.path.join(VAR_ROOT, 'static')

DATABASES['default'] = dj_database_url.config()
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# WSGI_APPLICATION = '{{ project_name }}.wsgi.prod.application'
