import attr
from peewee import DoesNotExist

from elram.repository import datetime
from elram.repository.models import Event, User


class CommandException(Exception):
    ...


@attr.s
class AttendanceService:
    event: Event = attr.ib()

    def find_user(self, nickname):
        nickname = nickname.title()
        try:
            return User.get(nickname=nickname.title())
        except DoesNotExist:
            raise CommandException(f'No conozco a ningún peñero con el nombre {nickname}')

    def add_attendance(self, nickname):
        user = self.find_user(nickname)
        self.event.add_attendee(user)

    def remove_attendance(self, nickname):
        user = self.find_user(nickname)
        self.event.remove_attendee(user)

    def replace_host(self, nickname):
        user = self.find_user(nickname)
        self.event.replace_host(user)


class EventService:

    def get_next_event(self):
        return Event.select()\
            .where(Event.datetime >= datetime.datetime.now())\
            .order_by(Event.datetime)\
            .first()

    def update_when(self, when):
        ...
