import logging
from datetime import datetime, timedelta, date
from decimal import Decimal, InvalidOperation
from typing import Optional

import attr
from peewee import DoesNotExist

from elram.repository.models import Event, User, AttendeeNotFound, Account
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

    @classmethod
    def get_next_event_date(cls, offset=1):
        today = date.today()
        return today + timedelta(
            weeks=offset,
            days=CONFIG['EVENT_WEEKDAY'] - today.weekday(),
            hours=23,
            minutes=59,
        )

    def create_event(self, host, offset=1):
        last_event = Event.get_last_event()
        assert last_event is not None
        next_code = last_event.code + 1
        event = Event.create(
            code=next_code,
            datetime=self.get_next_event_date(offset)
        )
        event.add_host(host)
        logger.info(
            'Event created',
            extra={
                'code': event.code,
                'host': host.nickname,
            }
        )
        hidden_host = User.get_hidden_host()
        event.add_attendee(hidden_host)
        return event

    def create_first_event(self):
        # FIXME: The first event should be created by `create_future_event` somehow
        host = User.get(nickname=CONFIG['FIRST_EVENT_HOST_NICKNAME'])
        event = Event(
            code=CONFIG['FIRST_EVENT_CODE'],
            datetime=self.get_next_event_date()
        )
        event.save()
        event.add_host(host)
        logger.info(
            'Event created',
            extra={
                'code': event.code,
                'host': host.nickname,
            }
        )
        hidden_host = User.get_hidden_host()
        event.add_attendee(hidden_host)
        return event

    def create_future_events(self):
        future_hosts = list(User.get_future_hosts())
        last_host = future_hosts[-1]
        hosts = list(User.get_hosts())
        index = hosts.index(last_host)
        ordered_hosts = enumerate(hosts[index:] + hosts[:index])
        for offset, host in ordered_hosts:
            if host in future_hosts:
                continue
            self.create_event(host, offset=offset)


@attr.s
class AccountabilityService:
    event: Event = attr.ib()
    _EXPENSE = None
    _REFOUND = None
    _CONTRIBUTION = None

    @property
    def EXPENSE(self):
        if self._EXPENSE is None:
            self._EXPENSE = Account.get(name='Expenses')
        return self._EXPENSE

    @property
    def REFOUND(self):
        if self._REFOUND is None:
            self._REFOUND = Account.get(name='Refunds')
        return self._REFOUND

    @property
    def CONTRIBUTION(self):
        if self._CONTRIBUTION is None:
            self._CONTRIBUTION = Account.get(name='Contributions')
        return self._CONTRIBUTION

    @staticmethod
    def _get_amount(str_value):
        try:
            return Decimal(str_value)
        except InvalidOperation:
            raise CommandException(f'No entiendo que cantidad de plata es esta: {str_value}')

    def _find_attendee(self, nickname):
        try:
            attendee = self.event.find_attendee(nickname)
        except AttendeeNotFound as ex:
            raise CommandException(str(ex))
        return attendee

    def add_expense(self, nickname: str, amount: str, description: str = None):
        attendee = self._find_attendee(nickname.title())
        amount = self._get_amount(amount)
        logger.info(
            "Adding expense",
            extra={'attendee': attendee, 'amount': amount, 'description': description}
        )
        attendee.add_credit(amount, self.EXPENSE, description=description)
        self.event.hidden_host.add_debit(amount, self.EXPENSE, description=description)

    def add_payment(self, nickname: str, amount: str, to_nickname: str = None):
        payment_to_found = to_nickname is None

        attendee = self._find_attendee(nickname.title())
        to_attendee = None
        if not payment_to_found:
            to_attendee = self._find_attendee(to_nickname.title())
        hidden_host = self.event.hidden_host

        amount = self._get_amount(amount)
        logger.info(
            "Adding payment",
            extra={'from': attendee, 'to': to_attendee, 'amount': amount}
        )
        attendee.add_credit(amount, self.REFOUND)
        hidden_host.add_debit(amount, self.EXPENSE)
        if not payment_to_found:
            to_attendee.add_debit(amount, self.REFOUND)
            hidden_host.add_cebit(amount, self.EXPENSE)

    def add_refound(self, nickname: str, amount: str):
        attendee = self._find_attendee(nickname.title())
        amount = self._get_amount(amount)
        logger.info(
            "Adding refound",
            extra={'attendee': attendee, 'amount': amount,}
        )
        attendee.add_debit(amount, self.REFOUND)
        self.event.hidden_host.add_credit(amount, self.REFOUND)
