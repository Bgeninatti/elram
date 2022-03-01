import logging

from peewee import DoesNotExist
from telegram import Update
from telegram.ext import CallbackContext, ConversationHandler, CommandHandler, Filters, MessageHandler, \
    CallbackQueryHandler
from elram.conversations.new_event import NewEventConversation
from elram.conversations.states import MAIN_MENU, HOME, LOGIN, CLOSE_EVENT, ASK_ATTENDEES
from elram.conversations.views import show_main_menu, ask_user
from elram.repository.models import Event, User
from elram.repository.commands import sign_up, sign_in


logger = logging.getLogger(__name__)


class MainConversation:
    myself = 'el_ram_bot'

    def _get_user_message(self, update):
        return update.callback_query.message if update.message is None else update.message

    def main(self, update: Update, context: CallbackContext):
        telegram_user = update.message.from_user
        user = sign_in(telegram_user)
        if user:
            context.user_data['user'] = user
            update.message.reply_text(
                f'Que haces {user.first_name}?'
            )
            return show_main_menu(update.message, context)
        else:
            update.message.reply_text(
                'Ey Ram. No te registro. Como es la contraseña?'
            )
            return LOGIN

    def login(self, update: Update, context: CallbackContext):
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
            return show_main_menu(update.message, context)

    def cancel(self, update: Update, context: CallbackContext) -> int:
        user = context.user_data['user']
        logger.info('Conversation canceled', extra={'telegram_id': user.telegram_id})
        update.message.reply_text(
            'Bueno, listo. Tomate el palo\n'
            'Si querés volvera hablar mandá /start'
        )

        return ConversationHandler.END

    def ask_atteendees(self, update: Update, context: CallbackContext):
        message = self._get_user_message(update)
        is_user_message = message.from_user.username != self.myself
        event = context.user_data['event']
        if is_user_message and message.text == 'Ya terminé.':
            message.reply_text('Ok')
            return show_main_menu(update.message, context)

        if is_user_message and message.text is not None:
            try:
                new_attendee = User.get(nickname=message.text)
                event.add_attendee(new_attendee)
            except DoesNotExist:
                message.reply_text(f'Mmmm no encontré a ningún peñero con el nombre {message.text}.')

        message.reply_text(event.display_attendees())

        ask_user(message, exclude=[a.attendee for a in event.attendees], optional=True)
        return ASK_ATTENDEES

    def close_event(self, update: Update, context: CallbackContext):
        message = update.callback_query.message if update.message is None else update.message

        active_event = Event.get_active()
        active_event.close()

        message.reply_text(f'Listo. Cerré la peña #{active_event.code}')
        return show_main_menu(message, context)

    def get_handler(self):
        new_event_conversation = NewEventConversation()

        return ConversationHandler(
            entry_points=[CommandHandler('start', self.main)],
            states={
                LOGIN: [MessageHandler(Filters.text, self.login)],
                HOME: [MessageHandler(Filters.text, self.main)],
                MAIN_MENU: [
                    new_event_conversation.get_handler(),
                    CallbackQueryHandler(self.close_event, pattern=f'^{CLOSE_EVENT}$'),
                    CallbackQueryHandler(self.ask_atteendees, pattern=f'^{ASK_ATTENDEES}$'),
                ],
                ASK_ATTENDEES: [
                    MessageHandler(Filters.text, self.ask_atteendees),
                ]
            },
            fallbacks=[CommandHandler('cancel', self.cancel)],
        )
