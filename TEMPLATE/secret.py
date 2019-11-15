"""Access AWS Secrets Manager."""
import boto3
import base64
import json
import logging

log = logging.getLogger(__name__)


def get_secret(secret_name):
    """Fetch secret via boto3."""
    client = boto3.client(service_name="secretsmanager")
    get_secret_value_response = client.get_secret_value(SecretId=secret_name)

    if "SecretString" in get_secret_value_response:
        secret = get_secret_value_response["SecretString"]
        return json.loads(secret)
    else:
        decoded_binary_secret = base64.b64decode(
            get_secret_value_response["SecretBinary"]
        )
        return decoded_binary_secret


def update_app_config(app, secret_name: str):
    secrets = get_secret(secret_name=secret_name)
    if secrets:
        log.debug(f"{len(secrets.keys())} app secrets loaded")
        app.config.update(secrets)
    else:
        log.warning(f"Failed to load secrets '{secret_name}'")


def db_secret_to_url(secrets) -> str:
    """Given a database secret construct a connection string for DATABASE_URL config."""
    password = secrets.get('password', '')
    dbname = secrets.get('dbname', '')
    engine = secrets.get('engine', '')
    port = secrets.get('port', '5432')
    host = secrets.get('host', '')
    username = secrets.get('username', '')
    return f"{engine}://{username}:{password}@{host}:{port}/{dbname}"
