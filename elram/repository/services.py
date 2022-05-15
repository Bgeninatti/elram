import logging
from datetime import datetime, timedelta, date, time
from decimal import Decimal, InvalidOperation
from typing import Optional

import attr
from peewee import DoesNotExist

from elram.repository.models import Event, User, AttendeeNotFound, Account, EventFinancialStatus, Transaction, \
    Attendance
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
    accountability_service = attr.ib(default=None)

    def __attrs_post_init__(self):
        self.accountability_service = AccountabilityService(event=self.event)

    def _add_attendance_for_user(self, user):
        attendee = self.event.add_attendee(user)
        self.accountability_service.create_social_fee_transaction(attendee)
        self.accountability_service.refresh_social_fees()

    def add_attendance(self, nickname):
        user = self.users_service.find_user(nickname)
        self._add_attendance_for_user(user)

    def remove_attendance(self, nickname):
        user = self.users_service.find_user(nickname)
        if user == self.event.host:
            raise CommandException(f'Primero decime quien organiza la peña si no va {user.nickname}')
        self.event.remove_attendee(user)
        self.accountability_service.refresh_social_fees()

    def replace_host(self, nickname):
        user = self.users_service.find_user(nickname)
        if not self.event.is_attendee(user):
            self._add_attendance_for_user(user)
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
        if today.weekday() == CONFIG['EVENT_WEEKDAY']:
            day = today
        else:
            day = today + timedelta(weeks=offset, days=CONFIG['EVENT_WEEKDAY'] - today.weekday())
        return datetime.combine(day, time(23, 59))

    def create_event(self, host, offset=1):
        last_event = Event.get_last_event()
        assert last_event is not None
        next_code = last_event.code + 1
        event = Event.create(
            code=next_code,
            datetime=self.get_next_event_date(offset)
        )
        accountability_service = AccountabilityService(event=event)
        attendee = event.add_host(host)
        accountability_service.create_social_fee_transaction(attendee)
        logger.info(
            'Event created',
            extra={
                'code': event.code,
                'host': host.nickname,
            }
        )
        hidden_host = User.get_hidden_host()
        hidden_host_attendee = event.add_attendee(hidden_host)
        accountability_service.create_social_fee_transaction(hidden_host_attendee)
        return event

    def create_first_event(self):
        # FIXME: The first event should be created by `create_future_event` somehow
        host = User.get(nickname=CONFIG['FIRST_EVENT_HOST_NICKNAME'])
        event = Event.create(
            code=CONFIG['FIRST_EVENT_CODE'],
            datetime=self.get_next_event_date()
        )
        accountability_service = AccountabilityService(event=event)
        attendee = event.add_host(host)
        accountability_service.create_social_fee_transaction(attendee)
        logger.info(
            'Event created',
            extra={
                'code': event.code,
                'host': host.nickname,
            }
        )
        hidden_host = User.get_hidden_host()
        hidden_host_attendee = event.add_attendee(hidden_host)
        accountability_service.create_social_fee_transaction(hidden_host_attendee)
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

    def display_event(self, event):
        financial_status = EventFinancialStatus(
            event=event,
            cost_account=Account.get(name='Expenses'),
            refund_account=Account.get(name='Refunds'),
            social_fee_account=Account.get(name='Social Fees'),
            contribution_account=Account.get(name='Contributions'),
        )
        msg = (
            f'*Peña \#{event.code} \- {event.datetime_display}*\n'
            f'La organiza {event.host}\n'
        )
        msg += event.display_attendees()
        msg += '\n'
        if financial_status.total_cost > 0:
            msg += financial_status.display()
            msg += '\n'
        return msg



@attr.s
class AccountabilityService:
    event: Event = attr.ib()
    _EXPENSE = None
    _REFUND = None
    _CONTRIBUTION = None
    _SOCIAL_FEE = None

    @property
    def EXPENSE(self):
        if self._EXPENSE is None:
            self._EXPENSE = Account.get(name='Expenses')
        return self._EXPENSE

    @property
    def REFUND(self):
        if self._REFUND is None:
            self._REFUND = Account.get(name='Refunds')
        return self._REFUND

    @property
    def CONTRIBUTION(self):
        if self._CONTRIBUTION is None:
            self._CONTRIBUTION = Account.get(name='Contributions')
        return self._CONTRIBUTION

    @property
    def SOCIAL_FEE(self):
        if self._SOCIAL_FEE is None:
            self._SOCIAL_FEE = Account.get(name='Social Fees')
        return self._SOCIAL_FEE

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

    def create_social_fee_transaction(self, attendee):
        Transaction.create(
            attendance=attendee,
            account=self.SOCIAL_FEE,
            description=f'Cuota peña #{self.event.code}',
        )
        Transaction.create(
            attendance=attendee,
            account=self.CONTRIBUTION,
            description=f'Contribución peña #{self.event.code}',
        )

    def refresh_social_fees(self):
        financial_status = EventFinancialStatus(
            event=self.event,
            cost_account=self.EXPENSE,
            refund_account=self.REFUND,
            social_fee_account=self.SOCIAL_FEE,
            contribution_account=self.CONTRIBUTION,
        )
        cost = financial_status.cost_per_capita
        contribution = financial_status.per_capita_contribution
        logger.info(
            "Setting social fee",
            extra={'cost': cost, 'contribution': contribution, 'event': self.event}
        )
        for attendee in self.event.effective_attendees:
            Transaction.update(debit=financial_status.cost_per_capita) \
                .where((Transaction.attendance == attendee) & (Transaction.account == self.SOCIAL_FEE))\
                .execute()
            Transaction.update(debit=financial_status.per_capita_contribution) \
                .where((Transaction.attendance == attendee) & (Transaction.account == self.CONTRIBUTION))\
                .execute()
        hidden_host = self.event.hidden_host
        Transaction.update(credit=financial_status.total_cost) \
            .where((Transaction.attendance == hidden_host) & (Transaction.account == self.SOCIAL_FEE)) \
            .execute()
        Transaction.update(credit=financial_status.total_contribution) \
            .where((Transaction.attendance == hidden_host) & (Transaction.account == self.CONTRIBUTION)) \
            .execute()

    def add_expense(self, nickname: str, amount: str, description: str = None):
        attendee = self._find_attendee(nickname.title())
        amount = self._get_amount(amount)
        logger.info(
            "Adding expense",
            extra={'attendee': attendee, 'amount': amount, 'description': description, 'event': self.event}
        )
        attendee.add_credit(amount, self.EXPENSE, description=description)
        self.event.hidden_host.add_debit(amount, self.EXPENSE, description=description)
        self.refresh_social_fees()

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
            extra={'from': attendee, 'to': to_attendee, 'amount': amount, 'event': self.event}
        )
        attendee.add_credit(amount, self.REFUND)
        hidden_host.add_debit(amount, self.REFUND)
        if not payment_to_found:
            to_attendee.add_debit(amount, self.REFUND)
            hidden_host.add_credit(amount, self.REFUND)

    def add_refound(self, nickname: str, amount: str):
        attendee = self._find_attendee(nickname.title())
        amount = self._get_amount(amount)
        logger.info(
            "Adding refound",
            extra={'attendee': attendee, 'amount': amount,}
        )
        attendee.add_debit(amount, self.REFUND)
        self.event.hidden_host.add_credit(amount, self.REFUND)
