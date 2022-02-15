import os
from urllib.parse import urlparse


def clean_setting(key):
    return os.environ[key].replace("\n", "").replace("\r", "")


def load_config():
    params = urlparse(os.environ["DATABASE_URL"])
    config = {
        "BOT_TOKEN": clean_setting("BOT_TOKEN"),
        "DB": {
            "db_name": params.path[1:],
            "user": params.username,
            "password": params.password,
            "host": params.hostname,
            "port": params.port,
        },
    }
    return config
