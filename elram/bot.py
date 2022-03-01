import logging

from telegram import Update
from telegram.ext import CallbackContext, ConversationHandler, Updater

from elram.conversations.main import MainConversation

logger = logging.getLogger("main")


def error(update: Update, context: CallbackContext):
    logger.warning(
        "Something bad happened", extra={"error": context.error, "update": update}
    )
    update.message.reply_text("Uh, pasó la mala. Me tengo que ir\n" "Después hablamos")

    return ConversationHandler.END


def main(bot_key):
    updater = Updater(bot_key, use_context=True)
    dispatcher = updater.dispatcher

    dispatcher.add_handler(MainConversation().get_handler())
    dispatcher.add_error_handler(error)

    # Start the Bot
    updater.start_polling()

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()
