import click

from elram.config import load_config
from elram.logger import setup_logger
import logging
from .commands import run_bot
from ..repository.models import init_db

CONFIG = load_config()
log = logging.getLogger('main')


@click.group(name='elram')
@click.pass_context
def main(ctx):
    """El Ram CLI"""
    init_db(**CONFIG['DB'])
    ctx.ensure_object(dict)
    setup_logger()
    log.info("Init the main application")


main.add_command(run_bot)
