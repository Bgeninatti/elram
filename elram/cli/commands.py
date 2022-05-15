import logging
from pathlib import Path

import click

from elram import bot
from elram.config import load_config
from elram.repository.commands import populate_db
from elram.repository.models import Event
from elram.repository.services import EventService

log = logging.getLogger('main')
CONFIG = load_config()


@click.command()
@click.argument('bot_token', type=str, default=CONFIG['BOT_TOKEN'])
def run_bot(bot_token):
    bot.main(bot_token)


@click.command()
@click.argument('data_file', type=Path, default=CONFIG['INITIAL_USERS_FILE'])
def bootstrap(data_file):
    service = EventService()
    populate_db(data_file)
    service.create_first_event()
    service.create_future_events()


@click.command()
def create_next_events():
    service = EventService()
    service.create_future_events()
