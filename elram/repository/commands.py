import logging

from elram.config import load_config
from elram.repository.models import User, database, Event, Attendance, Account, Transaction

CONFIG = load_config()
logger = logging.getLogger('main')


def populate_db(data):
    models_mapping = {
        'users': User,
        'accounts': Account,
    }

    for model_key, model_data in data.items():
        model_class = models_mapping.get(model_key)
        if model_class is None:
            logger.error('No model class found', extra={'model_key': model_key})
            continue
        models = (model_class(**data) for data in model_data)
        model_class.bulk_create(models)
        logger.info(
            'Records created',
            extra={'model': model_class.__name__, 'records': len(model_data)},
        )


def init_db(db_name, user, password, host, port):
    database.init(database=db_name, user=user, password=password, host=host, port=port)
    database.connect()
    database.create_tables([User, Event, Attendance, Account, Transaction])
    return database
