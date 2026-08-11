"""Import all models so SQLAlchemy can resolve string-based relationships."""

from app.models import preference  # noqa: F401
from app.models import trip  # noqa: F401
from app.models import user  # noqa: F401
from app.models import google_calendar  # noqa: F401
