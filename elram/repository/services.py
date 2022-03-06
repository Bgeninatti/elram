import logging
from datetime import datetime
from typing import Optional

import attr
from peewee import DoesNotExist

from elram.repository.models import Event, User
from elram.config import load_config

CONFIG = load_config()
logger = logging.getLogger('main')


class CommandException(Exception):
    ...


class UsersService:

    def find_user(self, nickname):
        nickname = nickname.title()
        try:
            return User.get(nickname=nickname.title())
        except DoesNotExist:
            raise CommandException(f'No conozco a ningún peñero con el nombre {nickname}')

    def sign_in(self, telegram_user):
        try:
            return User.get(User.is_staff, User.telegram_id == telegram_user.id)
        except DoesNotExist:
            return

    def sign_up(self, telegram_user, password: str) -> Optional[User]:
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


@attr.s
class AttendanceService:
    event: Event = attr.ib()
    users_service = attr.ib(factory=lambda: UsersService())

    def add_attendance(self, nickname):
        user = self.users_service.find_user(nickname)
        self.event.add_attendee(user)

    def remove_attendance(self, nickname):
        user = self.users_service.find_user(nickname)
        if user == self.event.host:
            raise CommandException(f'Primero decime quien organiza la peña si no va {user.nickname}')
        self.event.remove_attendee(user)

    def replace_host(self, nickname):
        user = self.users_service.find_user(nickname)
        self.event.replace_host(user)


class EventService:

    def get_next_event(self):
        return Event.select()\
            .where(Event.datetime >= datetime.now())\
            .order_by(Event.datetime)\
            .first()


class AccountabilityService:

    def add_expense(self, nickname: str, amount: float, description: str = ''):
        ...
