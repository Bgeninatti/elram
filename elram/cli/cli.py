import click

from elram.config import load_config
from elram.logger import setup_logger
import logging
from .commands import run_bot

CONFIG = load_config()
log = logging.getLogger(__name__)


@click.group(name='mwc')
@click.pass_context
def main(ctx):
    """El Ram CLI"""
    ctx.ensure_object(dict)
    setup_logger()
    log.info("Init the main application")


main.add_command(run_bot)
