import logging

import click

from elram import bot
from elram.config import load_config

log = logging.getLogger('main')
CONFIG = load_config()


@click.command()
@click.argument('bot_token', type=str, default=CONFIG['BOT_TOKEN'])
def run_bot(bot_token):
    bot.main(bot_token)
