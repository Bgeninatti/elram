import attr
from peewee import DoesNotExist
from telegram import InlineKeyboardMarkup, InlineKeyboardButton, Update
from telegram.ext import CallbackContext, ConversationHandler, CallbackQueryHandler, MessageHandler, Filters, \
    CommandHandler

from elram.conversations.views import ask_user, show_main_menu
from elram.repository.datetime import get_from_text
from elram.repository.models import Event, User
from elram.conversations.states import NEW_EVENT, HOME


@attr.s
class NewEventConversation:

    CONFIRM_WHEN, ASK_WHEN, SAVE_WHEN, CONFIRM_HOST, ASK_HOST, SAVE_HOST = range(8, 14)
    confirm_when_menu = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton(text='Si, vamos con esa fecha', callback_data=SAVE_WHEN)],
            [InlineKeyboardButton(text='No. La hacemos en otra fecha', callback_data=ASK_WHEN)],
        ]
    )
    confirm_host_menu = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton(text='Si, dale', callback_data=SAVE_HOST)],
            [InlineKeyboardButton(text='No, la hace otro', callback_data=ASK_HOST)],
        ]
    )

    def main(self, update: Update, context: CallbackContext):
        message = update.callback_query.message
        message.reply_text(
            'Listo. Vamos a activar la próxima peña.'
        )
        event = Event.get_next_event()
        event.activate()
        context.user_data['event'] = event
        return self.confirm_when(update, context)

    def confirm_when(self, update: Update, context: CallbackContext):
        message = update.callback_query.message if update.callback_query is not None else update.message

        message.reply_text(
            f'La próxima peña es la del {context.user_data["event"].datetime_display}.\n'
            'La hacemos ese día?',
            reply_markup=self.confirm_when_menu

        )
        return self.CONFIRM_WHEN

    def ask_when(self, update: Update, context: CallbackContext):
        message = update.callback_query.message
        message.reply_text(
            'Cuando va a ser?'
        )
        message.reply_text(
            'Escribí la fecha usando día y mes con dos dígitos.'
        )
        message.reply_text(
            'Por ejemplo, el 12 de junio sería 12/06.\n'
            'También podés escribirlo como 12-06 o 12 06'
        )
        return self.SAVE_WHEN

    def save_when(self, update: Update, context: CallbackContext):
        message = update.callback_query.message if update.message is None else update.message

        if update.message is not None:
            event_date = get_from_text(message.text)
            if event_date is None:
                message.reply_text(
                    'mmm... no te entendí que fecha va a ser.'
                )
                message.reply_text(
                    'Escribí la fecha usando día y mes con dos dígitos.'
                )
                message.reply_text(
                    'Por ejemplo, el 12 de junio sería 12/06.\n'
                    'También podés escribirlo como 12-06 o 12 06'
                )
                return self.SAVE_WHEN
            context.user_data['event'].datetime = event_date
            context.user_data['event'].save()
        when_display = context.user_data['event'].datetime_display
        message.reply_text(
            f'Listo. La próxima peña es el {when_display}'
        )
        return self.confirm_host(update, context)

    def confirm_host(self, update: Update, context: CallbackContext):
        message = update.callback_query.message if update.message is None else update.message
        host = context.user_data['event'].host
        message.reply_text(
            f'El organizador es {host}.\n'
            'Está bien?',
            reply_markup=self.confirm_host_menu
        )
        return self.CONFIRM_HOST

    def ask_host(self, update: Update, context: CallbackContext):
        message = update.callback_query.message
        message.reply_text(
            'Quien organiza la peña?',
        )
        ask_user(message, optional=False, hosts_only=True, allow_create=False)
        return self.SAVE_HOST

    def save_host(self, update: Update, context: CallbackContext):
        message = update.callback_query.message if update.message is None else update.message
        event = context.user_data['event']

        print(update.message)
        print()
        if update.message is not None:
            try:
                host = User.get(nickname=message.text)
            except DoesNotExist:
                message.reply_text(f'Mmmm no encontré a ningún peñero con el nombre {message.text}.')
                return self.ASK_HOST

            print(host)
            print()
            event.replace_host(host)

        return show_main_menu(message)

    def cancel(self, update: Update, context: CallbackContext):
        update.message.reply_text(
            'Bueno, chau.'
        )
        return ConversationHandler.END

    def get_handler(self):
        return ConversationHandler(
            entry_points=[
                CallbackQueryHandler(self.main, pattern=f'^{NEW_EVENT}$'),
            ],
            states={
                self.CONFIRM_WHEN: [
                    CallbackQueryHandler(self.ask_when, pattern=f'^{self.ASK_WHEN}$'),
                    CallbackQueryHandler(self.save_when, pattern=f'^{self.SAVE_WHEN}$'),
                ],
                self.SAVE_WHEN: [
                    MessageHandler(Filters.text, self.save_when),
                ],
                self.CONFIRM_HOST: [
                    CallbackQueryHandler(self.ask_host, pattern=f'^{self.ASK_HOST}$'),
                    CallbackQueryHandler(self.save_host, pattern=f'^{self.SAVE_HOST}$'),
                ],
                self.SAVE_HOST: [
                    MessageHandler(Filters.text, self.save_host),
                ],
            },
            fallbacks=[CommandHandler('cancel', self.cancel)],
            map_to_parent={
                ConversationHandler.END: HOME
            },
        )
