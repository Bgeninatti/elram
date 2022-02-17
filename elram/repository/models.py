from datetime import datetime

from peewee import (CharField, DateTimeField, IntegerField, Model, DateField, PostgresqlDatabase, BooleanField)


database = PostgresqlDatabase(None)


class BaseModel(Model):
    updated = DateTimeField(default=datetime.now)
    created = DateTimeField(default=datetime.now)

    class Meta:
        database = database

    def save(self, *args, **kwargs):
        self.updated = datetime.now()
        super().save(*args, **kwargs)


class User(BaseModel):
    telegram_id = IntegerField(null=True, unique=True)
    first_name = CharField()
    last_name = CharField(null=True)
    is_staff = BooleanField(default=False)


class Event(BaseModel):
    ...


def init_db(db_name, user, password, host, port):
    database.init(database=db_name, user=user, password=password, host=host, port=port)
    database.connect()
    database.create_tables([User, ])
    return database
