import datetime
import logging
import math

import attr
from peewee import (CharField, DateTimeField, IntegerField, Model, PostgresqlDatabase, BooleanField,
                    ForeignKeyField, DecimalField, fn)

from elram.config import load_config

database = PostgresqlDatabase(None)
CONFIG = load_config()
logger = logging.getLogger(__name__)


class NotFound(Exception):
    ...


class AttendeeNotFound(NotFound):
    ...


class BaseModel(Model):
    updated: datetime = DateTimeField(default=datetime.datetime.now)
    created: datetime = DateTimeField(default=datetime.datetime.now)

    class Meta:
        database = database

    def save(self, *args, **kwargs):
        self.updated = datetime.datetime.now()
        super().save(*args, **kwargs)


class User(BaseModel):
    telegram_id = IntegerField(null=True, unique=True)
    first_name = CharField(null=True)
    last_name = CharField(null=True)
    nickname = CharField(unique=True)
    is_staff = BooleanField(default=False)
    hidden = BooleanField(default=False)
    is_host = BooleanField(default=False)

    def __str__(self):
        return self.nickname

    @classmethod
    def get_future_hosts(cls):
        return User.select() \
            .join(Attendance) \
            .join(Event) \
            .where(Attendance.is_host & (Event.datetime >= datetime.datetime.now()) & ~User.hidden)\
            .order_by(User.last_name.desc())

    @classmethod
    def get_hosts(cls):
        return User.select().where(cls.is_host & ~cls.hidden)

    @classmethod
    def get_hidden_host(cls):
        return cls.select().where(cls.hidden).first()


class Event(BaseModel):
    SPANISH_WEEKDAYS = {
        0: 'Lunes',
        1: 'Martes',
        2: 'Miércoles',
        3: 'Jueves',
        4: 'Viernes',
        5: 'Sábado',
        6: 'Domingo',
    }
    SPANISH_MONTHS = {
        1: 'Enero',
        2: 'Febrero',
        3: 'Marzo',
        4: 'Abril',
        5: 'Mayo',
        6: 'Junio',
        7: 'Julio',
        8: 'Agosto',
        9: 'Septiembre',
        10: 'Octubre',
        11: 'Noviembre',
        12: 'Diciembre',
    }
    DRAFT, ACTIVE, CLOSED, ABANDONED = range(4)

    datetime: datetime = DateTimeField()
    code: int = IntegerField()

    def refresh(self):
        return type(self).get(self._pk_expr())

    @property
    def hidden_host(self):
        return self.attendees.join(User).where(User.hidden).first()

    @property
    def datetime_display(self):
        spanish_weekday = self.SPANISH_WEEKDAYS[self.datetime.weekday()]
        spanish_month = self.SPANISH_MONTHS[self.datetime.month]
        return f'{spanish_weekday} {self.datetime.day} de {spanish_month}'

    @property
    def host(self):
        return self.attendees.where(Attendance.is_host == True).first().attendee

    @property
    def effective_attendees(self):
        return self.attendees.join(User).where(~User.hidden)

    @classmethod
    def get_next_event(cls):
        return cls.select().where(cls.datetime > datetime.datetime.now()).order_by(cls.code).first()

    @classmethod
    def get_last_event(cls):
        return cls.select().order_by(cls.created.desc()).first()

    def find_attendee(self, nickname):
        attendee = self.effective_attendees.where(User.nickname == nickname).first()
        if attendee is None:
            raise AttendeeNotFound(f'{nickname} no es asistente de esta peña.')
        return attendee

    def add_host(self, host):
        """
        Make a user that already attend the event, event host
        """
        if host.hidden:
            return

        if not self.is_attendee(host):
            # Add new host if not attendee already
            return Attendance.create(event_id=self.id, attendee=host, is_host=True)
        else:
            # Update attendee to host if already exists
            Attendance.update(is_host=True)\
                .where(Attendance.event == self, Attendance.attendee == host)\
                .execute()

    def replace_host(self, host):
        if host.hidden:
            return

        # Make old host normal attendee
        Attendance.update(is_host=False)\
            .where(Attendance.event == self, Attendance.attendee == self.host)\
            .execute()
        self.add_host(host)

    def is_attendee(self, attendee: User):
        return Attendance.select()\
            .where(Attendance.event == self, Attendance.attendee == attendee)\
            .exists()

    def add_attendee(self, attendee: User):
        if not self.is_attendee(attendee):
            return Attendance.create(event_id=self.id, attendee=attendee, is_host=False)

    def remove_attendee(self, attendee: User):
        if attendee.hidden:
            return

        Attendance.delete()\
            .where(Attendance.event == self, Attendance.attendee == attendee)\
            .execute()

    def display_attendees(self):
        attendees = self.effective_attendees
        attendees_names = '\n'.join([f'{i + 1}\- {a.attendee.nickname}' for i, a in enumerate(attendees)])
        return f'Hasta ahora van:\n{attendees_names}\n'

    def __str__(self):
        financial_status = EventFinancialStatus(
            event=self,
            cost_account=Account.get(name='Expenses'),
            refund_account=Account.get(name='Refunds'),
            social_fee_account=Account.get(name='Social Fees'),
            contribution_account=Account.get(name='Contributions'),
        )
        msg = (
            f'*Peña \#{self.code} \- {self.datetime_display}*\n'
            f'La organiza {self.host}\n'
        )
        msg += self.display_attendees()
        msg += '\n'
        if financial_status.total_cost > 0:
            msg += financial_status.display()
            msg += '\n'
        return msg


class Account(BaseModel):
    name = CharField(unique=True)

    def __str__(self):
        return f'<Account {self.name}>'


class Attendance(BaseModel):
    attendee = ForeignKeyField(User, related_name='attendances')
    event = ForeignKeyField(Event, related_name='attendees')
    is_host = BooleanField(default=False)

    class Meta:
        indexes = (
            (('attendee', 'event'), True),
        )

    @property
    def debit(self):
        return self.get_debit()

    @property
    def credit(self):
        return self.get_credit()

    def get_debit(self, account: Account = None):
        debit = Transaction\
            .select(fn.SUM(Transaction.debit))\
            .where(Transaction.attendance == self)
        if account is not None:
            debit = debit.where(Transaction.account == account)
        debit = debit.scalar()
        return debit or 0

    def get_credit(self, account: Account = None):
        credit = Transaction\
            .select(fn.SUM(Transaction.credit))\
            .where(Transaction.attendance == self)
        if account is not None:
            credit = credit.where(Transaction.account == account)
        credit = credit.scalar()
        return credit or 0

    def get_account_balance(self, account: Account = None):
        return self.get_debit(account) - self.get_credit(account)

    def get_transactions(self, account: Account = None):
        transactions = Transaction.select().where(Transaction.attendance == self)
        if account is not None:
            transactions = transactions.where(Transaction.account == account)
        return transactions

    @property
    def balance(self):
        return self.debit - self.credit

    def add_credit(self, amount, account, description=None):
        return Transaction.create(
            attendance=self,
            account=account,
            credit=amount,
            description=description or '',
        )

    def add_debit(self, amount, account, description=None):
        return Transaction.create(
            attendance=self,
            account=account,
            debit=amount,
            description=description or '',
        )

    def __str__(self):
        return f'<Attendee {self.event.id}#{self.attendee}>'


class Transaction(BaseModel):
    attendance = ForeignKeyField(Attendance, related_name='transactions', on_delete='cascade')
    account = ForeignKeyField(Account, related_name='transactions')
    description = CharField(default='')
    debit = DecimalField(default=0)
    credit = DecimalField(default=0)


@attr.s
class EventFinancialStatus:
    event: Event = attr.ib()
    cost_account: Account = attr.ib()
    refund_account: Account = attr.ib()
    social_fee_account: Account = attr.ib()
    contribution_account: Account = attr.ib()
    _total_expense = attr.ib(init=False, default=None)
    _cost_per_capita = attr.ib(init=False, default=None)
    _per_capita_contribution = attr.ib(init=False, default=None)
    _effective_cost_per_capita = attr.ib(init=False, default=None)
    _attendees_count = attr.ib(init=False, default=None)
    _hidden_host_balance = attr.ib(init=False, default=None)

    @property
    def attendees_count(self):
        if self._attendees_count is None:
            self._attendees_count = self.event.effective_attendees.count()
        return self._attendees_count

    @property
    def total_cost(self):
        if self._total_expense is None:
            self._total_expense = round(sum(
                a.get_credit(account=self.cost_account)
                for a in self.event.attendees
            ), 2)
        return self._total_expense

    @property
    def total_contribution(self):
        return self.attendees_count * self.per_capita_contribution

    @property
    def cost_per_capita(self):
        if self._cost_per_capita is None:
            self._cost_per_capita = self.total_cost / self.attendees_count
        return self._cost_per_capita

    @property
    def per_capita_contribution(self):
        if self._per_capita_contribution is None:
            self._per_capita_contribution = self.effective_cost_per_capita - self.cost_per_capita
        return self._per_capita_contribution

    @property
    def effective_cost_per_capita(self):
        if self._effective_cost_per_capita is None:
            self._effective_cost_per_capita = math.ceil(self.cost_per_capita / 100) * 100
        return self._effective_cost_per_capita

    def display(self):
        effective_attendees = self.event.effective_attendees
        msg = f'En total se gastó `{self.total_cost}`\n'
        for attendance in effective_attendees:
            credit = round(attendance.get_credit(self.cost_account), 2)
            if credit > 0:
                msg += f'\* {attendance.attendee} gastó `{credit}`\n'

        msg += f'\nCada peñero tiene que pagar `{self.effective_cost_per_capita}`\n'
        debts = 0
        incomming = 0

        for attendance in effective_attendees:
            balance = round(attendance.balance, 2)
            if not balance:
                msg += f'\* {attendance.attendee} 👍\n'
            elif balance > 0:
                incomming += balance
                msg += f'\* {attendance.attendee} tiene que pagar `{balance}`\n'
            else:
                debts += balance
                msg += f'\* {attendance.attendee} tiene que recibir `{abs(balance)}`\n'

        hidden_host = self.event.hidden_host
        refund_balance = hidden_host.get_account_balance(self.refund_account)
        contribution_balance = abs(hidden_host.get_account_balance(self.contribution_account))

        msg += f'\nEstado del fondo:\n'
        msg += f'\* le falta pagar: `{abs(debts)}`\n'
        msg += f'\* le falta recibir: `{incomming}`\n'
        msg += f'\* disponible: `{round(refund_balance, 2)}`\n'
        msg += f'\* tiene que recaudar: `{round(contribution_balance, 2)}`\n'

        return msg

    def __str__(self):
        return f'<EventFinancialStatus #{self.event}>'
