import datetime
import json
import logging

from peewee import (CharField, DateTimeField, IntegerField, Model, PostgresqlDatabase, BooleanField,
                    ForeignKeyField, DecimalField, ManyToManyField, DeferredThroughModel)

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
    nickname: str = CharField()
    is_staff: bool = BooleanField(default=False)
    is_host: bool = BooleanField(default=False)


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

    datetime: datetime = DateTimeField()
    is_active: bool = BooleanField(default=True)

    @classmethod
    def get_next_event(cls):
        today = datetime.date.today()
        next_event_date = today + datetime.timedelta(weeks=1, days=CONFIG['EVENT_WEEKDAY'] - today.weekday())
        event = cls(
            datetime=next_event_date
        )
        return event

    @classmethod
    def get_active(cls):
        return cls.select().where(Event.is_active == True).first()

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

    def add_attendee(self, attendee: User, is_host: bool = False):
        Attendance.create(event_id=self.id, attendee=attendee, is_host=is_host)

    def close(self):
        if not self.is_active:
            return
        self.is_active = False
        self.save()

    def __str__(self):
        attendees_names = '\n'.join([a.attendee.nickname for a in self.attendees])
        return (
            f'Peña #{self.id} el {self.datetime_display}.\n'
            f'La organiza {self.host.nickname} y hasta ahora van:\n'
            f'{attendees_names}'
        )


class Attendance(BaseModel):
    attendee = ForeignKeyField(User, related_name='attendances')
    event = ForeignKeyField(Event, related_name='attendees')
    is_host = BooleanField(default=False)
    debit = DecimalField(default=0)
    credit = DecimalField(default=0)

    @property
    def balance(self):
        """
        If negative the attendee borrow money.
        If positive the attendee contribute to the fund.
        :return: int
        """
        return self.debit - self.credit


def populate_db(data_file):
    models_mapping = {
        'users': User,
    }

    with open(data_file) as f:
        data = json.load(f)

    for model_key, model_data in data.items():
        model_class = models_mapping.get(model_key)
        if model_class is None:
            logger.error('No model class found', extra={'model_key': model_key})
            continue
        models = (model_class(**data) for data in model_data)
        model_class.bulk_create(models)
        logger.info(
            'Records created',
            extra={'model': model_class.__name__, 'records': len(model_data)},
        )


def init_db(db_name, user, password, host, port):
    database.init(database=db_name, user=user, password=password, host=host, port=port)
    database.connect()
    database.create_tables([User, Event, Attendance])
    return database
