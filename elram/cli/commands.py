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
@click.argument('bootstrap_file_url', default=CONFIG['BOOTSTRAP_FILE_URL'])
def bootstrap(bootstrap_file_url):
    service = EventService()
    bootstrap_data = service.get_bootstrap_data(bootstrap_file_url)
    populate_db(bootstrap_data)
    service.create_first_event()
    service.create_future_events()


@click.command()
def create_next_events():
    service = EventService()
    service.create_future_events()
