import datetime
import logging
import math

from peewee import (CharField, DateTimeField, IntegerField, Model, PostgresqlDatabase, BooleanField,
                    ForeignKeyField, DecimalField)

from elram.config import load_config

database = PostgresqlDatabase(None)
CONFIG = load_config()
logger = logging.getLogger(__name__)


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

    @classmethod
    def get_next_event_date(cls, offset=1):
        today = datetime.date.today()
        return today + datetime.timedelta(
            weeks=offset,
            days=CONFIG['EVENT_WEEKDAY'] - today.weekday(),
            hours=23,
            minutes=59,
        )

    @classmethod
    def create_first_event(cls):
        host = User.get(nickname=CONFIG['FIRST_EVENT_HOST_NICKNAME'])
        event = cls(
            code=CONFIG['FIRST_EVENT_CODE'],
            datetime=cls.get_next_event_date()
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
        return event

    @classmethod
    def get_next_event(cls):
        return cls.select().where(cls.datetime > datetime.datetime.now()).order_by(cls.code).first()

    @classmethod
    def create_event(cls, host, offset=1):
        last_event = cls.get_last_event()
        assert last_event is not None
        next_code = last_event.code + 1
        event = cls.create(
            code=next_code,
            datetime=cls.get_next_event_date(offset)
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

    @classmethod
    def get_active(cls):
        return cls.select().join(Attendance).where(cls.datetime > datetime.datetime.now()).first()

    @classmethod
    def get_last_event(cls):
        return cls.select().order_by(cls.created.desc()).first()

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
        Attendance.delete()\
            .where(Attendance.event == self, Attendance.attendee == attendee)\
            .execute()

    def display_attendees(self):
        attendees = self.effective_attendees
        if len(attendees) == 1:
            return f'Hasta ahora va {attendees[0].attendee.nickname} solo\n'
        else:
            attendees_names = '\n'.join([f'{i + 1}\- {a.attendee.nickname}' for i, a in enumerate(attendees)])
            return f'Hasta ahora van:\n{attendees_names}\n'

    def add_debit(self, user, amount, description=None):
        Attendance\
            .update(debit=amount, debit_description=description or '')\
            .where(Attendance.event == self, Attendance.attendee == user)\
            .execute()

    def add_credit(self, user, amount, description=None):
        Attendance\
            .update(credit=amount, credit_description=description or '')\
            .where(Attendance.event == self, Attendance.attendee == user)\
            .execute()

    def display_expenses(self):
        per_capita = math.ceil(self.total_expenses / self.attendees.count() / 100) * 100
        msg = f'En total se gastó `{self.total_expenses}`\n'
        msg += f'Cada peñero tiene que pagar `{per_capita}`\n\n'

        for attendance in self.attendees:
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
            f'La organiza {self.host.nickname}\n'
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
