from sqlalchemy import Column, Integer, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from db.conn import Base
from models.user_model import User


class BlinkSample(Base):
    __tablename__ = "blink_samples"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    timestamp = Column(DateTime, nullable=False)
    count = Column(Integer, nullable=False)
    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=True)

    user = relationship(User)
    session = relationship("Session", back_populates="blink_samples")