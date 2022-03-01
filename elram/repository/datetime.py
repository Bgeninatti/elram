from datetime import datetime

from elram.config import load_config

CONFIG = load_config()


def get_from_text(text):
    for f in CONFIG['DATETIME_FORMATS']:
        try:
            return datetime.strptime(text, f)
        except ValueError:
            continue
    return
