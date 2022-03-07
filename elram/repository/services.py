import logging
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Optional

import attr
from peewee import DoesNotExist

from elram.repository.models import Event, User, Attendance
from elram.config import load_config

CONFIG = load_config()
logger = logging.getLogger('main')


class CommandException(Exception):
    ...


class UsersService:

    def find_user(self, nickname):
        nickname = nickname.title()
        try:
            return User.get(nickname=nickname.title(), hidden=False)
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

    @staticmethod
    def last_host_in_alphabet():
        """
        :return: Hosts with a future event
        """
        return User.select() \
            .join(Attendance) \
            .join(Event) \
            .where(Attendance.is_host & (Event.datetime > datetime.datetime.now()) & ~User.hidden) \
            .order_by(User.last_name.desc())\
            .first()

    @staticmethod
    def get_hosts():
        return User.select().where(User.is_host & ~User.hidden).order_by(User.last_name)


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

    def is_attendee(self, nickname):
        user = self.users_service.find_user(nickname)
        return self.event.is_attendee(user)


@attr.s
class EventService:
    users_service = attr.ib(factory=lambda: UsersService())

    def get_active_event(self):
        return Event.select()\
            .where(Event.datetime >= datetime.now())\
            .order_by(Event.datetime)\
            .first()

    def find_event_by_code(self, event_code: int):
        try:
            return Event.get(Event.code == event_code)
        except DoesNotExist:
            raise CommandException(f'No encontré la peña {event_code}')

    def create_event(self, host, offset=1):
        last_event = Event.get_last_event()
        assert last_event is not None
        next_code = last_event.code + 1
        event = Event.create(
            code=next_code,
            datetime=Event.get_next_event_date(offset)
        )
        event.add_host(host)
        logger.info(
            'Event created',
            extra={
                'code': event.code,
                'host': host.nickname,
            }
        )
        return event

    @staticmethod
    def create_future_events():
        future_hosts = list(User.get_future_hosts())
        last_host = future_hosts[-1]
        hosts = list(User.get_hosts())
        index = hosts.index(last_host)
        ordered_hosts = enumerate(hosts[index:] + hosts[:index])
        for offset, host in ordered_hosts:
            if host in future_hosts:
                continue
            event = Event.create_event(host, offset=offset)
            hidden_host = User.get_hidden_host()
            event.add_attendee(hidden_host)


@attr.s
class AccountabilityService:
    event: Event = attr.ib()
    users_service = attr.ib(factory=lambda: UsersService())

    def _get_amount(self, str_value):
        try:
            return Decimal(str_value)
        except InvalidOperation:
            raise CommandException(f'No entiendo que cantidad de plata es esta: {str_value}')

    def add_expense(self, nickname: str, amount: str, description: str = None):
        user = self.users_service.find_user(nickname)
        if not self.event.is_attendee(user):
            raise CommandException(f'{user.nickname} no es asistente de esta peña.')
        amount = self._get_amount(amount)
        logger.info(
            "Adding expense",
            extra={'user': user, 'amount': amount, 'description': description}
        )
        self.event.add_credit(user, amount, description)

    def add_payment(self, nickname: str, amount: str):

        user = self.users_service.find_user(nickname)
        if not self.event.is_attendee(user):
            raise CommandException(f'{user.nickname} no es asistente de esta peña.')
        amount = self._get_amount(amount)
        logger.info(
            "Adding payment",
            extra={'user': user, 'amount': amount}
        )
        self.event.add_debit(user, amount)
