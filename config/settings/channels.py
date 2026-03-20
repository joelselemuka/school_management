"""
Configuration Django Channels pour les WebSockets (temps réel).
"""

import os

# Channels Configuration
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            'hosts': [(
                os.getenv('REDIS_HOST', 'localhost'),
                int(os.getenv('REDIS_PORT', 6379))
            )],
            'capacity': 1500,  # Max messages per channel
            'expiry': 10,  # Message expiry in seconds
        },
    },
}

# ASGI Application
ASGI_APPLICATION = 'config.asgi.application'
