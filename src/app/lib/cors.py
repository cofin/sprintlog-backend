from litestar.config.cors import CORSConfig

from app.lib import settings

config = CORSConfig(allow_origins=settings.app.BACKEND_CORS_ORIGINS, allow_credentials=True)
"""Default CORS config."""
