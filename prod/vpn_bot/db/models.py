from sqlalchemy import (
    create_engine, Column, Integer, BigInteger, String,
    Boolean, DateTime, ForeignKey, func
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from config import DATABASE_URL
import uuid

Base = declarative_base()
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
session = Session()

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    tg_id = Column(BigInteger, unique=True, nullable=False)
    username = Column(String)
    referral_code = Column(String, unique=True, nullable=False)
    referred_by = Column(String)
    referrals_count = Column(Integer, default=0)
    subscription_start = Column(DateTime)
    subscription_end = Column(DateTime)
    is_active = Column(Boolean, default=False)
    balance_days = Column(Integer, default=0)
    last_payment = Column(DateTime)
    payment_tx = Column(String)
    role = Column(String, default="user")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # 🔗 связь с vpn_keys
    vpn_keys = relationship("VpnKey", back_populates="user", cascade="all, delete")

class VpnKey(Base):
    __tablename__ = "vpn_keys"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    uuid = Column(String, unique=True)
    vpn_link = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="vpn_keys")
    bypass_rules = relationship("VpnBypassRule", back_populates="vpn_key", cascade="all, delete")

class BypassSite(Base):
    __tablename__ = "bypass_sites"
    
    id = Column(Integer, primary_key=True)
    domain = Column(String, unique=True, nullable=False)  # example.com
    name = Column(String, nullable=False)  # Человекочитаемое название
    category = Column(String, default="other")  # social, streaming, gaming, etc.
    is_verified = Column(Boolean, default=False)  # Проверен ли сайт
    added_by_user_id = Column(Integer, ForeignKey("users.id"))
    usage_count = Column(Integer, default=0)  # Сколько пользователей используют
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    added_by = relationship("User")

class VpnBypassRule(Base):
    __tablename__ = "vpn_bypass_rules"
    
    id = Column(Integer, primary_key=True)
    vpn_key_id = Column(Integer, ForeignKey("vpn_keys.id"), nullable=False)
    bypass_site_id = Column(Integer, ForeignKey("bypass_sites.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    vpn_key = relationship("VpnKey", back_populates="bypass_rules")
    bypass_site = relationship("BypassSite")

Base.metadata.create_all(engine)

def ensure_user(tg_user, referred_by_code=None):
    user = session.query(User).filter_by(tg_id=tg_user.id).first()
    if not user:
        referral_code = str(uuid.uuid4())[:8]
        user = User(
            tg_id=tg_user.id,
            username=tg_user.username,
            referral_code=referral_code,
            referred_by=referred_by_code
        )

        if referred_by_code:
            referrer = session.query(User).filter_by(referral_code=referred_by_code).first()
            if referrer:
                referrer.balance_days += 3
                referrer.referrals_count += 1
                session.add(referrer)

        session.add(user)
        session.commit()
    return user