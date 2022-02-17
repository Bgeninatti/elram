import logging

from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import CommandHandler, Filters, MessageHandler, Updater, ConversationHandler, CallbackContext

from elram.repository.queries import sign_up, sign_in

logger = logging.getLogger('main')

LOGIN, MENU, LISTAR_EVENTOS, VER_EVENTO, CARGAR_GASTO, CARGAR_PAGO = range(6)


def show_menu(update):
    update.message.reply_text(
        'Mirá, ahora no hay ninguna peña activa. Están todos re tirados.'
    )
    menu_keyboard = [
        ['Crear una peña'],
        ['Ver peñas viejas'],
        ['Ver saldos'],
        ['Tomarme el palo'],
    ]
    menu_markup = ReplyKeyboardMarkup(
        menu_keyboard,
        one_time_keyboard=True,
        input_field_placeholder='Decime en que te doy una mano.'
    )
    update.message.reply_text(
        'Bueno, que querés hacer?',
        reply_markup=menu_markup,
    )
    return MENU


def start(update: Update, context: CallbackContext):
    telegram_user = update.message.from_user
    user = sign_in(telegram_user)
    if user:
        context.user_data['user'] = user
        update.message.reply_text(
            f'Que haces {user.first_name}?'
        )
        return show_menu(update)
    else:
        update.message.reply_text(
            'Ey Ram. No te registro. Como es la contraseña?'
        )
        return LOGIN


def login(update: Update, context: CallbackContext):
    telegram_user = update.message.from_user
    password = update.message.text
    user = sign_up(telegram_user, password)
    if user is None:
        logger.warning(
            'Wrong password',
            extra={
                'telegram_id': telegram_user.id,
                'username': telegram_user.username,
            }
        )
        update.message.reply_text(
            'No, nada que ver. Como es la contraseña?'
        )
        return LOGIN
    else:
        context.user_data['user'] = user
        update.message.reply_text(
            f'A si, de una. Vos sos {user.first_name}'
        )
        return show_menu(update)


def menu(update: Update, context: CallbackContext):
    update.message.reply_text(
        'Hasta acá todo legal.'
    )
    return ConversationHandler.END


def cancel(update: Update, context: CallbackContext) -> int:
    user = context.user_data['user']
    logger.info('Conversation canceled', extra={'telegram_id': user.telegram_id})
    update.message.reply_text(
        'Bueno, listo. Tomate el palo\n'
        'Si querés volvera hablar mandá /start'
    )

    return ConversationHandler.END


def error(update: Update, context: CallbackContext):
    logger.warning(
        'Something bad happened',
        extra={
            'error': context.error,
            'update': update
        }
    )
    update.message.reply_text(
        'Uh, pasó la mala. Me tengo que ir\n'
        'Después hablamos'
    )

    return ConversationHandler.END


def main(bot_key):
    updater = Updater(bot_key, use_context=True)
    dispatcher = updater.dispatcher

    conversation = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            LOGIN: [MessageHandler(Filters.text, login)],
            MENU: [MessageHandler(Filters.text, menu)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
        conversation_timeout=10,
    )

    dispatcher.add_handler(conversation)
    dispatcher.add_error_handler(error)

    # Start the Bot
    updater.start_polling()

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()
