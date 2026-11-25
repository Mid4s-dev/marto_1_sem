import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "fallback-dev-secret-key")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    BCRYPT_LOG_ROUNDS = int(os.environ.get("BCRYPT_LOG_ROUNDS", 12))
    LOCKOUT_ATTEMPTS = int(os.environ.get("LOCKOUT_ATTEMPTS", 5))
    LOCKOUT_TIME_MINUTES = int(os.environ.get("LOCKOUT_TIME_MINUTES", 30))
    INTASEND_SECRET_KEY = os.environ.get("INTASEND_SECRET_KEY", "")
    INTASEND_WEBHOOK_CHALLENGE = os.environ.get("INTASEND_WEBHOOK_CHALLENGE", "")
    INTASEND_BASE_URL = os.environ.get(
        "INTASEND_BASE_URL",
        "https://api.intasend.com/api/v1",
    )


class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        "mysql+mysqlclient://srms_user:SecurePassword123!@localhost:3306/srms_db",
    )


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False
    BCRYPT_LOG_ROUNDS = 4  # faster hashing in tests


class ProductionConfig(Config):
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL")


config_map = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}
