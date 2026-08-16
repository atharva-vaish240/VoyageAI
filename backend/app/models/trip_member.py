"""TripMember association database model for trip collaboration."""

import enum
from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    Integer,
    DateTime,
    Enum,
    ForeignKey,
    UniqueConstraint,
    Index,
)
from sqlalchemy.orm import relationship

from app.core.database import Base


class MemberRole(str, enum.Enum):
    OWNER = "OWNER"
    MEMBER = "MEMBER"


class TripMember(Base):
    __tablename__ = "trip_members"

    id = Column(Integer, primary_key=True, index=True)
    trip_id = Column(
        Integer,
        ForeignKey("trips.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role = Column(Enum(MemberRole), nullable=False, default=MemberRole.MEMBER)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    trip = relationship("Trip", back_populates="members")
    user = relationship("User", back_populates="trip_memberships")

    @property
    def email(self) -> str:
        return self.user.email if self.user else ""

    @property
    def name(self) -> str:
        return self.user.name if self.user else ""

    __table_args__ = (
        UniqueConstraint("trip_id", "user_id", name="uq_trip_member_trip_user"),
        Index("ix_trip_members_trip_user", "trip_id", "user_id"),
    )

    def __repr__(self):
        return f"<TripMember id={self.id} trip_id={self.trip_id} user_id={self.user_id} role={self.role}>"
