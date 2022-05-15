import click

from elram.config import load_config
from elram.logger import setup_logger
import logging
from .commands import run_bot, bootstrap, create_next_events
from elram.repository.commands import init_db

CONFIG = load_config()
log = logging.getLogger('main')


@click.group(name='elram')
def main():
    """El Ram CLI"""
    init_db(**CONFIG['DB'])
    setup_logger()
    log.info("Init the main application")


main.add_command(run_bot)
main.add_command(bootstrap)
main.add_command(create_next_events)
