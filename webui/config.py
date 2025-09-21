LOGGING_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'level': 'DEBUG'
        },
        'file': {
            'class': 'logging.FileHandler',
            'filename': 'netureon.log',
            'level': 'DEBUG'
        }
    },
    'root': {
        'handlers': ['console', 'file'],
        'level': 'DEBUG'
    }
}