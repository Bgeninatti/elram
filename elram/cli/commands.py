import logging

import click

from elram.bot import RamBot
from elram.config import load_config

log = logging.getLogger(__name__)
CONFIG = load_config()


@click.command()
@click.argument('bot_token', type=str, default=CONFIG['BOT_TOKEN'])
def run_bot(bot_token):
    bot = RamBot(bot_token)
    bot.run()
