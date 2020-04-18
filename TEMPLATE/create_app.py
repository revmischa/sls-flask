"""Main Flask app configuration file.

Creates a new instance of our Flask app with plugins, blueprints, views, and configuration loaded.
"""
import logging
import os

import sqlalchemy_aurora_data_api  # noqa: F401
from aws_xray_sdk.core import patcher, xray_recorder
from aws_xray_sdk.ext.flask.middleware import XRayMiddleware
from flask import jsonify
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_migrate import Migrate, MigrateCommand
from flask_script import Manager
from nplusone.ext.flask_sqlalchemy import NPlusOne
from typing import Optional

from .api import api
from .commands import init_cli
from .db import db
from .flaskapp import App
from .secret import db_secret_to_url, get_secret, update_app_config

log = logging.getLogger(__name__)


def create_app(test_config: Optional[dict] = None) -> App:
    app = App("TEMPLATE")

    # load config
    configure(app=app, test_config=test_config)

    # extensions
    CORS(app)
    configure_database(app)
    api.init_app(app)  # flask-smorest
    NPlusOne(app)

    # CLI
    manager = Manager(app)
    manager.add_command("db", MigrateCommand)  # migrations under "flask db"
    init_cli(app, manager)

    init_xray(app)
    init_auth(app)

    return app


def init_auth(app: App) -> None:
    jwt = JWTManager(app)

    @jwt.user_loader_callback_loader
    def user_loader_callback(identity):
        from TEMPLATE.model.user import User

        if identity is None:
            return None
        user = User.query.get(identity)
        return user

    @jwt.user_loader_error_loader
    def custom_user_loader_error(identity):
        ret = {"msg": "User {} not found".format(identity)}
        return jsonify(ret), 404

    @jwt.user_identity_loader
    def user_identity_lookup(user):
        assert user.id
        return user.id


def configure_database(app: App) -> None:
    """Set up flask with SQLAlchemy."""
    # configure options for create_engine
    engine_opts = app.config.get("SQLALCHEMY_ENGINE_OPTIONS", {})

    if app.config.get("AURORA_DATA_API_ENABLED"):
        # configure sqlalchemy-aurora-data-api
        rds_secret_arn = app.get_config_value_or_raise("AURORA_SECRET_ARN")
        aurora_cluster_arn = app.get_config_value_or_raise("AURORA_CLUSTER_ARN")
        db_name = app.get_config_value_or_raise("DATABASE_NAME")
        conn_url = f"postgresql+auroradataapi://:@/{db_name}"
        app.config["SQLALCHEMY_DATABASE_URI"] = conn_url

        # augment connect_args
        connect_args = engine_opts.get("connect_args", {})
        connect_args["aurora_cluster_arn"] = aurora_cluster_arn
        connect_args["secret_arn"] = rds_secret_arn
        engine_opts["connect_args"] = connect_args
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = engine_opts

    db.init_app(app)  # init sqlalchemy
    app.migrate = Migrate(app, db)  # alembic

    @app.teardown_appcontext
    def shutdown_session(exception=None):
        """Close session after request.

        Ensures no open transactions remain.
        """
        db.session.remove()

    if app.config.get("TESTING"):
        return

    test_db(app)


def test_db(app: App) -> None:
    # verify DB works
    try:
        with app.app_context():
            db.session.execute("SELECT 1").scalar()
    except Exception as ex:
        log.error(
            f"Database configuration is invalid. Using URI: {app.config['SQLALCHEMY_DATABASE_URI']}"
        )
        raise ex


def configure_class(app: App) -> None:
    """Load class-based app configuration from config.py."""
    config_class = os.getenv("TEMPLATE_CONFIG".upper())

    if not config_class:
        # figure out which config to load
        # get stage name
        stage = os.getenv("STAGE")
        if stage:
            # running in AWS or sls wsgi serve
            if stage == "prd":
                config_class = "TEMPLATE.config.ProductionConfig"
            else:
                config_class = "TEMPLATE.config.DevConfig"
        else:
            # local dev
            config_class = "TEMPLATE.config.LocalDevConfig"

    app.config.from_object(config_class)


def configure_secrets(app: App) -> None:
    if app.config.get("LOAD_RDS_SECRETS"):
        # fetch db config secrets from Secrets Manager
        secret_name = app.config["RDS_SECRETS_NAME"]
        assert secret_name, "RDS_SECRETS_NAME missing"
        rds_secrets = get_secret(secret_name=secret_name)
        # construct database connection string from secret
        app.config["SQLALCHEMY_DATABASE_URI"] = db_secret_to_url(rds_secrets)

    if app.config.get("LOAD_APP_SECRETS"):
        # fetch app config secrets from Secrets Manager
        secret_name = app.config["APP_SECRETS_NAME"]
        update_app_config(app, secret_name)


def configure_instance(app: App) -> None:
    # load 'instance.cfg'
    # if it exists as our local instance configuration override
    app.config.from_pyfile("instance.cfg", silent=True)


def configure(app: App, test_config=None) -> None:
    configure_class(app)
    config = app.config
    if test_config:
        config.update(test_config)
    else:
        configure_secrets(app)
        configure_instance(app)

    if config.get("SQLALCHEMY_ECHO"):
        logging.basicConfig()
        logging.getLogger("sqlalchemy.engine").setLevel(logging.INFO)

    from .config import check_valid

    if not check_valid(config):
        raise Exception("Configuration is not valid.")


def init_xray(app: App) -> None:
    if not app.config.get("XRAY"):
        return
    patcher.patch(("requests", "boto3"))  # xray tracing for external requests
    xray_recorder.configure(service="TEMPLATE")
    XRayMiddleware(app, xray_recorder)
