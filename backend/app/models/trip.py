"""Trip database model."""

import enum
from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    Integer,
    String,
    Date,
    DateTime,
    Enum,
    ForeignKey,
)
from sqlalchemy.orm import relationship

from app.core.database import Base


class TripStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    PLANNED = "PLANNED"
    COMPLETED = "COMPLETED"


class Trip(Base):
    __tablename__ = "trips"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    title = Column(String(200), nullable=False)
    destination = Column(String(200), nullable=True)  # Nullable since destination might not be selected initially
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    status = Column(Enum(TripStatus), nullable=False, default=TripStatus.DRAFT)

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationship
    user = relationship("User", back_populates="trips")

    def __repr__(self):
        return f"<Trip id={self.id} title={self.title!r} user_id={self.user_id}>"
