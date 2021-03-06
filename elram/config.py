import os
from urllib.parse import urlparse


def clean_setting(key):
    return os.environ[key].replace("\n", "").replace("\r", "")


def load_config():
    params = urlparse(os.environ["DATABASE_URL"])
    config = {
        "PASSWORD": clean_setting("PASSWORD"),
        "BOT_TOKEN": clean_setting("BOT_TOKEN"),
        "EVENT_WEEKDAY": int(clean_setting("EVENT_WEEKDAY")),
        "DATETIME_FORMATS": [
            "%d/%m/%Y",
            "%d-%m-%Y",
            "%d %m %Y",
            "%d/%m/%y",
            "%d-%m-%y",
            "%d %m %y",
            "%d/%m",
            "%d-%m",
            "%d %m",
        ],
        "DB": {
            "db_name": params.path[1:],
            "user": params.username,
            "password": params.password,
            "host": params.hostname,
            "port": params.port,
        },
        "BOOTSTRAP_FILE_URL": clean_setting("BOOTSTRAP_FILE_URL"),
        "FIRST_EVENT_CODE": int(clean_setting("FIRST_EVENT_CODE")),
        "FIRST_EVENT_HOST_NICKNAME": clean_setting("FIRST_EVENT_HOST_NICKNAME"),
        "HIDDEN_USER_NICKNAME": clean_setting("HIDDEN_USER_NICKNAME"),
    }
    return config
