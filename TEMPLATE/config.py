import os
from datetime import timedelta
import logging

CONFIG_EXPECTED_KEYS = ("DATABASE_URL", "OPENAPI_VERSION", "JWT_SECRET_KEY")
# use local "TEMPLATE" DB for local dev
DEFAULT_DB_URL = "postgresql:///TEMPLATE"


class Config:
    """Base config."""

    # load more config from secrets manager?
    LOAD_APP_SECRETS = os.getenv("LOAD_APP_SECRETS", False)
    LOAD_RDS_SECRETS = os.getenv("LOAD_RDS_SECRETS", False)
    SECRETS_NAME = os.getenv("APP_SECRETS_NAME", "TEMPLATE/dev")
    RDS_SECRETS_NAME = os.getenv("RDS_SECRETS_NAME")

    DEV_DB_SCRIPTS_ENABLED = False  # can init-db/seed/etc be run?

    DATABASE_URL = os.getenv("DATABASE_URL", DEFAULT_DB_URL)
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # set SQL_ECHO=1 this to echo queries to stderr
    SQLALCHEMY_ECHO = bool(os.getenv("SQL_ECHO"))
    DEBUG = os.getenv("DEBUG", False)
    XRAY = bool(os.getenv("XRAY"))

    # openapi can be found at /api/openapi.json /api/doc
    OPENAPI_VERSION = "3.0.2"
    OPENAPI_URL_PREFIX = "/api"
    OPENAPI_JSON_PATH = "openapi.json"
    OPENAPI_REDOC_PATH = "/doc"
    OPENAPI_SWAGGER_UI_PATH = "/swagger"
    OPENAPI_SWAGGER_UI_VERSION = "3.23.11"
    # https://swagger.io/docs/specification/authentication/bearer-authentication/
    API_SPEC_OPTIONS = {
        "components": {
            "securitySchemes": {
                "bearerAuth": {
                    "type": "http",
                    "scheme": "bearer",
                    "bearerFormat": "JWT",
                }
            }
        },
        "security": [{"bearerAuth": []}],
    }
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "INSECURE")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=8)

    NPLUSONE_LOGGER = logging.getLogger("app.nplusone")
    NPLUSONE_LOG_LEVEL = logging.WARNING


class LocalDevConfig(Config):
    """Local development environment config."""

    DEBUG = True
    DEV_DB_SCRIPTS_ENABLED = True


class DevConfig(Config):
    """AWS dev environment and DB."""

    DEV_DB_SCRIPTS_ENABLED = True


class StagingConfig(Config):
    """AWS staging environment and DB."""

    DEV_DB_SCRIPTS_ENABLED = True


class ProdConfig(Config):
    """AWS production environment and DB."""

    # name of Secrets Manager secretID for config
    APP_SECRETS_NAME = "TEMPLATE/prod"
    LOAD_APP_SECRETS = False
    DEV_DB_SCRIPTS_ENABLED = False


# config checks


class ConfigurationInvalidError(Exception):
    def __init__(self, message: str):
        self.message = message

    def __str__(self):
        return self.message + f"\nEnvironment: {os.environ}"


class ConfigurationKeyMissingError(ConfigurationInvalidError):
    def __init__(self, key: str):
        super().__init__(message=f"Missing {key} key in configuration.")


class ConfigurationValueMissingError(ConfigurationInvalidError):
    def __init__(self, key: str):
        super().__init__(message=f"Missing {key} value in configuration.")


def check_valid(conf) -> bool:
    """Check if config looks okay."""

    def need_key(k):
        if k not in conf:
            raise ConfigurationKeyMissingError(k)
        if not conf.get(k):
            raise ConfigurationValueMissingError(k)

    [need_key(k) for k in CONFIG_EXPECTED_KEYS]
    return True


def check_valid_handler(event, context):
    # which env are we checking?
    config_class = event.get("env", "TEMPLATE.config.LocalDevConfig")

    # create an app with this config
    from .flask import App

    app = App(__name__)
    app.config.from_object(config_class)
    conf = app.config

    ok = check_valid(conf)

    return dict(ok=ok)
