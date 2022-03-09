import datetime
import logging
import math

from peewee import (CharField, DateTimeField, IntegerField, Model, PostgresqlDatabase, BooleanField,
                    ForeignKeyField, DecimalField)

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
            .where(Attendance.is_host & (Event.datetime > datetime.datetime.now()) & ~User.hidden)\
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
    def total_expenses(self):
        return round(sum(a.credit for a in self.attendees), 2)

    @property
    def effective_attendees(self):
        return self.attendees.join(User).where(~User.hidden)

    @classmethod
    def get_next_event(cls):
        return cls.select().where(cls.datetime > datetime.datetime.now()).order_by(cls.code).first()

    @classmethod
    def get_active(cls):
        return cls.select().join(Attendance).where(cls.datetime > datetime.datetime.now()).first()

    @classmethod
    def get_last_event(cls):
        return cls.select().order_by(cls.created.desc()).first()

    def find_attendee(self, nickname):
        attendee = self.effective_attendees.where(User.nickname == nickname).first()
        if attendee is None:
            raise AttendeeNotFound(f'{nickname} no es asistente de esta peña.')
        return attendee

    def add_host(self, host):
        if host.hidden:
            return

        if not self.is_attendee(host):
            # Add new host if not attendee already
            Attendance.create(event_id=self.id, attendee=host, is_host=True)
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
            Attendance.create(event_id=self.id, attendee=attendee, is_host=False)

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

    def display_expenses(self):
        per_capita = math.ceil(self.total_expenses / self.effective_attendees.count() / 100) * 100
        msg = f'En total se gastó `{self.total_expenses}`\n'
        msg += f'Cada peñero tiene que pagar `{per_capita}`\n\n'

        for attendance in self.effective_attendees:
            balance = round(attendance.balance + per_capita, 2)
            if not balance:
                msg += f'{attendance.attendee} 👍\n'
            elif balance > 0:
                msg += f'{attendance.attendee} tiene que pagar `{balance}`\n'
            else:
                msg += f'{attendance.attendee} tiene que recibir `{abs(balance)}`\n'
        return msg

    def __str__(self):
        msg = (
            f'*Peña \#{self.code} \- {self.datetime_display}*\n'
            f'La organiza {self.host}\n'
        )
        msg += self.display_attendees()
        msg += '\n'
        if self.total_expenses > 0:
            msg += self.display_expenses()
            msg += '\n'
        return msg


class Attendance(BaseModel):
    attendee = ForeignKeyField(User, related_name='attendances')
    event = ForeignKeyField(Event, related_name='attendees')
    is_host = BooleanField(default=False)
    debit = DecimalField(default=0)
    debit_description = CharField(default='')
    credit = DecimalField(default=0)
    credit_description = CharField(default='')

    class Meta:
        indexes = (
            (('attendee', 'event'), True),
        )

    @property
    def balance(self):
        return self.debit - self.credit

    def add_credit(self, amount, description=None):
        self.credit = amount
        self.credit_description = description or ''
        self.save()

    def increment_credit(self, amount, description=None):
        self.credit = amount
        self.credit_description = description or ''
        self.save()

    def add_debit(self, amount, description=None):
        self.debit = amount
        self.debit_description = description or ''
        self.save()

    def increment_debit(self, amount, description=None):
        self.debit += amount
        self.debit_description = description or ''
        self.save()

    def __str__(self):
        return f'<Attendee {self.event.id}#{self.attendee}>'
