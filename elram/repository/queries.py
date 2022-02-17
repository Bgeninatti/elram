import logging
from typing import Optional

from elram.config import load_config
from elram.repository.models import User

CONFIG = load_config()
logger = logging.getLogger('main')


def sign_in(telegram_user):
    return User.get(User.telegram_id == telegram_user.id)


def sign_up(telegram_user, password: str) -> Optional[User]:
    if password != CONFIG['PASSWORD']:
        return

    user = User.create(
        telegram_id=telegram_user.id,
        last_name=telegram_user.last_name,
        first_name=telegram_user.first_name,
        is_staff=True,
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
