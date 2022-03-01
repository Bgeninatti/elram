import json
import logging
from typing import Optional

from peewee import DoesNotExist

from elram.config import load_config
from elram.repository.models import User, database, Event, Attendance

CONFIG = load_config()
logger = logging.getLogger('main')


def populate_db(data_file):
    models_mapping = {
        'users': User,
    }

    with open(data_file) as f:
        data = json.load(f)

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
    database.create_tables([User, Event, Attendance])
    return database


def sign_in(telegram_user):
    try:
        return User.get(User.is_staff, User.telegram_id == telegram_user.id)
    except DoesNotExist:
        return


def sign_up(telegram_user, password: str) -> Optional[User]:
    if password != CONFIG['PASSWORD']:
        return

    user = User.create(
        telegram_id=telegram_user.id,
        last_name=telegram_user.last_name,
        first_name=telegram_user.first_name,
        nickname=telegram_user.username,
        is_staff=True,
        is_host=True,
    )
    logger.info(
        'User created',
        extra={
            'telegram_id': user.telegram_id,
            'first_name': user.first_name,
            'last_name': user.last_name,
        }
    )
    return user


def get_pending_hosts():
    """
    :return: Hosts with an event in DRAFT status
    """
    return User.select()\
        .join(Attendance)\
        .join(Event)\
        .where(Attendance.is_host & (Event.status == Event.DRAFT))\
        .order_by(User.last_name)


def get_hosts():
    return User.select().where(User.is_host).order_by(User.last_name)


def update_draft_events():
    pending_hosts = list(get_pending_hosts())
    hosts = list(get_hosts())
    last_host = pending_hosts[-1]
    last_host_index = hosts.index(last_host)
    for host in hosts[last_host_index:] + hosts[:last_host_index]:
        if host in pending_hosts:
            continue
        Event.create_event(host)
