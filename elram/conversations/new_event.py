import attr
from telegram import InlineKeyboardMarkup, InlineKeyboardButton, Update
from telegram.ext import CallbackContext, ConversationHandler, CallbackQueryHandler, MessageHandler, Filters, \
    CommandHandler

from elram.conversations.views import ask_user, show_main_menu
from elram.repository.datetime import get_from_text
from elram.repository.models import Event, User
from elram.conversations.states import NEW_EVENT, HOME


@attr.s
class NewEventConversation:

    ASK_WHEN, SAVE_WHEN, ASK_HOST, SAVE_HOST = range(8, 12)
    main_menu = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton(text='Si, vamos con esa fecha', callback_data=SAVE_WHEN)],
            [InlineKeyboardButton(text='No. La hacemos en otra fecha', callback_data=ASK_WHEN)],
        ]
    )

    def main(self, update: Update, context: CallbackContext):
        message = update.callback_query.message
        message.reply_text(
            'Listo. Vamos a armar la próxima peña.'
        )
        event = Event.get_next_event()
        context.user_data['event'] = event

        message.reply_text(
            f'La próxima peña es el la {event.datetime_display}.\n'
            'La hacemos ese día?',
            reply_markup=self.main_menu

        )
        return NEW_EVENT

    def ask_when(self, update: Update, context: CallbackContext):
        message = update.callback_query.message if update.callback_query is not None else update.message
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
        return self.ask_host(update, context)

    def ask_host(self, update: Update, context: CallbackContext):
        message = update.callback_query.message if update.message is None else update.message
        message.reply_text(
            'Quien organiza la peña?',
        )
        ask_user(message)
        return self.SAVE_HOST

    def save_host(self, update: Update, context: CallbackContext):
        message = update.callback_query.message if update.message is None else update.message
        event = context.user_data['event']
        host, _ = User.get_or_create(nickname=message.text.title())
        event.add_attendee(host, is_host=True)

        message.reply_text(
            f'La próxima peña es la #{event.id} la organiza {event.host.nickname}\n'
            'Vamos a ver si le da la pera.'
        )
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
                NEW_EVENT: [
                    CallbackQueryHandler(self.ask_when, pattern=f'^{self.ASK_WHEN}$'),
                    CallbackQueryHandler(self.save_when, pattern=f'^{self.SAVE_WHEN}$'),
                ],
                self.SAVE_WHEN: [
                    MessageHandler(Filters.text, self.save_when),
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
