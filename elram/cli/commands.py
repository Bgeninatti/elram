import logging
from pathlib import Path

import click

from elram import bot
from elram.config import load_config
from elram.repository.models import populate_db

log = logging.getLogger('main')
CONFIG = load_config()


@click.command()
@click.argument('bot_token', type=str, default=CONFIG['BOT_TOKEN'])
def run_bot(bot_token):
    bot.main(bot_token)


@click.command()
@click.argument('data_file', type=Path, default=CONFIG['INITIAL_USERS_FILE'])
def init_data(data_file):
    populate_db(data_file)
