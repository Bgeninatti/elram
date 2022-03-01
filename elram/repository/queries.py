import logging
from typing import Optional

from peewee import DoesNotExist

from elram.config import load_config
from elram.repository.models import User

CONFIG = load_config()
logger = logging.getLogger('main')


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
