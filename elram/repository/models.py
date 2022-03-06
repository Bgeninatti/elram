import datetime
import logging

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
    telegram_id: int = IntegerField(null=True, unique=True)
    first_name: str = CharField(null=True)
    last_name: str = CharField(null=True)
    nickname: str = CharField(unique=True)
    is_staff: bool = BooleanField(default=False)
    is_host: bool = BooleanField(default=False)

    def __str__(self):
        return self.nickname


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

    def add_host(self, host):
        if not self.is_attendee(host):
            # Add new host if not attendee already
            Attendance.create(event_id=self.id, attendee=host, is_host=True)
        else:
            # Update attendee to host if already exists
            Attendance.update(is_host=True)\
                .where(Attendance.event == self, Attendance.attendee == host)\
                .execute()

    def replace_host(self, host):
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

    def get_attendees(self):
        return [
            a.attendee for a in self.attendees
        ]

    def display_attendees(self):
        attendees = list(self.attendees)
        if len(attendees) == 1:
            return f'Hasta ahora va {attendees[0].attendee.nickname} solo. Flojo.'
        else:
            attendees_names = '\n'.join([f'{i + 1}. {a.attendee.nickname}' for i, a in enumerate(attendees)])
            return f'Hasta ahora van:\n{attendees_names}'

    def __str__(self):
        msg = (
            f'Peña #{self.code} el {self.datetime_display}.\n'
            f'La organiza {self.host.nickname}. \n'
        )
        msg += self.display_attendees()
        return msg


class Attendance(BaseModel):
    attendee = ForeignKeyField(User, related_name='attendances')
    event = ForeignKeyField(Event, related_name='attendees')
    is_host = BooleanField(default=False)
    debit = DecimalField(default=0)
    credit = DecimalField(default=0)

    class Meta:
        indexes = (
            (('attendee', 'event'), True),
        )

    @property
    def balance(self):
        """
        If negative the attendee borrow money.
        If positive the attendee contribute to the fund.
        :return: int
        """
        return self.debit - self.credit
