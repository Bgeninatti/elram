import logging

from telegram.ext import CommandHandler, Filters, MessageHandler, Updater

logger = logging.getLogger(__name__)


class RamBot(object):
    def __init__(self, bot_key):
        self._updater = Updater(bot_key, use_context=True)
        self._dp = self._updater.dispatcher

        self._dp.add_handler(CommandHandler("start", self._start, pass_user_data=True))
        self._dp.add_handler(
            MessageHandler(Filters.text, self._start, pass_user_data=True)
        )
        self._dp.add_error_handler(self._error)

    def _start(self, update, context):
        logger.info("Message received: chat_id=%s", update.message.chat.id)
        update.message.reply_text(f"Vos dijiste: {update.message.text}")

    def _error(self, update, context):
        logger.warn('Update "%s" caused error "%s"' % (update, context.error))

    def run(self):
        logger.info("Starting server...")
        self._updater.start_polling()
        self._updater.idle()
