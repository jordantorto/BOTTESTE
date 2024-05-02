from sqlalchemy import Boolean, Column,\
    ForeignKey, Integer, BigInteger, Float,\
    String, inspect, DateTime
from sqlalchemy.orm import relationship
from bot.db.database import Base


def object_as_dict(obj):
    if isinstance(obj, list):
        return [{c.key: getattr(item, c.key)
                 for c in inspect(item).mapper.column_attrs} for item in obj]
    else:
        return {c.key: getattr(obj, c.key)
                for c in inspect(obj).mapper.column_attrs}


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    user_bot = Column(BigInteger, index=True, nullable=False)
    email = Column(String, unique=True, index=True)
    name = Column(String, unique=False, index=True)
    password = Column(String, nullable=False)
    account_type = Column(String, index=True, default="DEMO")
    game_type = Column(String, index=True, default="DOUBLE")
    hashed_token = Column(String(200), index=True, nullable=True)
    already_tested = Column(Boolean, default=False)
    token = Column(String(200), index=True, nullable=True)
    process_pid = Column(BigInteger, index=True, nullable=True)
    wallet = Column(String(20), index=True, nullable=True)
    is_active = Column(Boolean, default=False)
    is_testing = Column(Boolean, default=False)
    payment_id = Column(BigInteger, index=True, nullable=True)
    payment_expire_in = Column(Integer, index=True, nullable=True)
    payment_status = Column(String, index=True, default="PENDING")
    is_betting = Column(Boolean, default=False)
    color_bet = Column(String(20), index=True, nullable=True)
    color_before = Column(String(20), index=True, nullable=True)
    point_bet = Column(String(20), index=True, nullable=True)
    point_before = Column(String(20), index=True, nullable=True)
    created_at = Column(DateTime, nullable=True)
    expire_in = Column(DateTime, nullable=True)

    settings = relationship("Settings",
                            back_populates="owner",
                            cascade="all, delete",
                            passive_deletes=True)
    variables = relationship("Variables",
                             back_populates="owner",
                             cascade="all, delete",
                             passive_deletes=True)
    strategies = relationship("Strategies",
                              back_populates="owner",
                              cascade="all, delete",
                              passive_deletes=True)

    def as_dict(self):
        return object_as_dict(self)


class Settings(Base):
    __tablename__ = "settings"

    id = Column(Integer, primary_key=True, index=True)
    strategy_type = Column(String, index=True, default="SYSTEM")
    enter_type = Column(String, index=True, default="VALOR")
    enter_percent = Column(Float, index=True, default=0.5)
    first_amount = Column(Float, index=True, default=2.0)
    first_protection = Column(Float, index=True, default=1.8)
    enter_value = Column(Float, index=True, default=2.0)
    stop_type = Column(String, index=True, default="VALOR")
    stop_gain = Column(String, index=True, default="100")
    stop_loss = Column(String, index=True, default="30")
    protection_hand = Column(String, index=True, default="NÃO")
    protection_value = Column(Float, index=True, default=1.8)
    martingale = Column(Integer, index=True, default=2)
    white_martingale = Column(String, index=True, default="NÃO")
    martingale_multiplier = Column(Float, index=True)
    white_multiplier = Column(Float, index=True)
    quantity_cycles = Column(Integer, index=True, default=0)
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))

    owner = relationship("User", back_populates="settings")

    def as_dict(self):
        return object_as_dict(self)


class Variables(Base):
    __tablename__ = "variables"

    id = Column(Integer, primary_key=True, index=True)
    count_loss = Column(Integer, index=True, default=0)
    count_win = Column(Integer, index=True, default=0)
    count_martingale = Column(Integer, index=True, default=0)
    profit = Column(Float, index=True, default=0)
    balance = Column(Float, index=True, default=0)
    first_balance = Column(Float, index=True, default=0)
    created = Column(Integer, index=True, default=0)
    is_gale = Column(Boolean, index=True, default=0)
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))

    owner = relationship("User", back_populates="variables")

    def as_dict(self):
        return object_as_dict(self)


class Strategies(Base):
    __tablename__ = "strategies"

    id = Column(Integer, primary_key=True, index=True)
    sequence = Column(String, index=True)
    color = Column(String, index=True)
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))

    owner = relationship("User", back_populates="strategies")

    def as_dict(self):
        return object_as_dict(self)
