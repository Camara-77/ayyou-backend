import os
import sys
from datetime import timedelta
from pathlib import Path
from dotenv import load_dotenv

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Load environment variables from .env file
load_dotenv(os.path.join(BASE_DIR, '.env'))

# Add apps directory to Python path
sys.path.insert(0, os.path.join(BASE_DIR, 'apps'))

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure-ayyou-dev-secret-key-change-in-production-2025')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.getenv('DEBUG', 'True').lower() in ('true', '1', 't')

ALLOWED_HOSTS = [host.strip() for host in os.getenv('ALLOWED_HOSTS', '127.0.0.1,localhost,testserver').split(',') if host.strip()] + ['testserver', '*']

# Application definition
INSTALLED_APPS = [
    # Django core apps
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Third-party apps
    'rest_framework',
    'rest_framework_simplejwt',
    'corsheaders',

    # AYYOU Local apps
    'apps.users',
    'apps.authentication',
    'apps.catalog',
    'apps.orders',
    'apps.payments',
    'apps.deliveries',
    'apps.admin_panel',
    'apps.pro_api',
    'apps.notifications',
    'apps.ai',
]

# Custom User Model configuration
AUTH_USER_MODEL = 'users.Utilisateur'

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',  # CORS middleware placed before CommonMiddleware
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'
ASGI_APPLICATION = 'config.asgi.application'

# Database Configuration (PostgreSQL with Environment Variables)
DB_ENGINE = os.getenv('DB_ENGINE', 'django.db.backends.postgresql')
DB_NAME = os.getenv('DB_NAME', 'ayyou_db')
DB_USER = os.getenv('DB_USER', 'postgres')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'postgres')
DB_HOST = os.getenv('DB_HOST', '127.0.0.1')
DB_PORT = os.getenv('DB_PORT', '5432')

# Fallback to SQLite if USE_SQLITE_DEV=True or if PostgreSQL server is not running in local environment
USE_SQLITE_DEV = os.getenv('USE_SQLITE_DEV', 'False').lower() in ('true', '1', 't')

if USE_SQLITE_DEV:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': DB_ENGINE,
            'NAME': DB_NAME,
            'USER': DB_USER,
            'PASSWORD': DB_PASSWORD,
            'HOST': DB_HOST,
            'PORT': DB_PORT,
        }
    }

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {'min_length': 8},
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
LANGUAGE_CODE = 'fr-fr'
TIME_ZONE = 'Africa/Dakar'
USE_I18N = True
USE_TZ = True

# Static & Media files
STATIC_URL = 'static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

MEDIA_URL = 'media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Django REST Framework Configuration
REST_FRAMEWORK = {
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
        'rest_framework.renderers.BrowsableAPIRenderer',
    ],
    'DEFAULT_PARSER_CLASSES': [
        'rest_framework.parsers.JSONParser',
        'rest_framework.parsers.FormParser',
        'rest_framework.parsers.MultiPartParser',
    ],
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.AllowAny',
    ],
    'EXCEPTION_HANDLER': 'rest_framework.views.exception_handler',
}

# SimpleJWT Configuration
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(days=1),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': False,
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'AUTH_HEADER_TYPES': ('Bearer',),
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
}

# CORS Configuration
CORS_ALLOWED_ORIGINS = [
    origin.strip() for origin in os.getenv('CORS_ALLOWED_ORIGINS', 'http://localhost:4200,http://127.0.0.1:4200').split(',') if origin.strip()
]

# OTP & Authentication Settings
OTP_EXPIRATION_MINUTES = int(os.getenv('OTP_EXPIRATION_MINUTES', '10'))
OTP_MAX_ATTEMPTS = int(os.getenv('OTP_MAX_ATTEMPTS', '3'))
DEFAULT_COUNTRY_CODE = os.getenv('DEFAULT_COUNTRY_CODE', 'SN')

# Email Configuration (Transactional Emails)
EMAIL_BACKEND = os.getenv('EMAIL_BACKEND', 'django.core.mail.backends.console.EmailBackend')
EMAIL_HOST = os.getenv('EMAIL_HOST', 'localhost')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', '25'))
EMAIL_USE_TLS = os.getenv('EMAIL_USE_TLS', 'False').lower() in ('true', '1', 't')
EMAIL_USE_SSL = os.getenv('EMAIL_USE_SSL', 'False').lower() in ('true', '1', 't')
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '')
DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', 'AYYOU <no-reply@ayyou.com>')

# Cloudinary Configuration (Feed Video Uploads)
CLOUDINARY_CLOUD_NAME = os.getenv('CLOUDINARY_CLOUD_NAME', '')
CLOUDINARY_API_KEY = os.getenv('CLOUDINARY_API_KEY', '')
CLOUDINARY_API_SECRET = os.getenv('CLOUDINARY_API_SECRET', '')

try:
    import cloudinary
    cloudinary.config(
        cloud_name=CLOUDINARY_CLOUD_NAME,
        api_key=CLOUDINARY_API_KEY,
        api_secret=CLOUDINARY_API_SECRET,
        secure=True
    )
except ImportError:
    pass

# PayDunya Payment Gateway Configuration
PAYDUNYA_MASTER_KEY = os.getenv('PAYDUNYA_MASTER_KEY', 'test_master_key')
PAYDUNYA_PRIVATE_KEY = os.getenv('PAYDUNYA_PRIVATE_KEY', 'test_private_key')
PAYDUNYA_PUBLIC_KEY = os.getenv('PAYDUNYA_PUBLIC_KEY', 'test_public_key')
PAYDUNYA_TOKEN = os.getenv('PAYDUNYA_TOKEN', 'test_token')
PAYDUNYA_MODE = os.getenv('PAYDUNYA_MODE', 'test').lower()  # 'test' or 'live'
PAYDUNYA_RETURN_URL = os.getenv('PAYDUNYA_RETURN_URL', 'http://localhost:4200/checkout/confirm')
PAYDUNYA_CANCEL_URL = os.getenv('PAYDUNYA_CANCEL_URL', 'http://localhost:4200/checkout/cancel')
PAYDUNYA_IPN_URL = os.getenv('PAYDUNYA_IPN_URL', 'https://running-custody-neatness.ngrok-free.dev/api/payments/ipn/')

# PayTech Payment Gateway Configuration
PAYTECH_API_KEY = os.getenv('PAYTECH_API_KEY', os.getenv('PAYTECH_CLE_API', ''))
PAYTECH_API_SECRET = os.getenv('PAYTECH_API_SECRET', os.getenv('PAYTECH_CLÉ_SECRETE', os.getenv('PAYTECH_CLE_SECRET', '')))
PAYTECH_ENV = os.getenv('PAYTECH_ENV', 'test').lower()
PAYTECH_FEE_RATE = float(os.getenv('PAYTECH_FEE_RATE', '0.015'))
PAYTECH_IPN_URL = os.getenv('PAYTECH_IPN_URL', 'https://running-custody-neatness.ngrok-free.dev/api/payments/paytech/ipn/')

PAYTECH_SUCCESS_URL = os.getenv('PAYTECH_SUCCESS_URL', 'https://running-custody-neatness.ngrok-free.dev/api/payments/paytech/success/')
PAYTECH_CANCEL_URL = os.getenv('PAYTECH_CANCEL_URL', 'https://running-custody-neatness.ngrok-free.dev/api/payments/paytech/cancel/')




# Logging Configuration (Protects against leaking sensitive data like passwords, tokens, OTP codes)
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '[{asctime}] {levelname} [{name}:{lineno}] {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': os.getenv('DJANGO_LOG_LEVEL', 'INFO'),
        },
        'apps': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': True,
        },
    },
}
