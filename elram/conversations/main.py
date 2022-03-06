import logging

from telegram import Update, Chat
from telegram.ext import CallbackContext, ConversationHandler, CommandHandler, Filters, MessageHandler
from elram.conversations.command_parser import CommandParser
from elram.repository.commands import sign_up, sign_in
from elram.repository.services import EventService, AttendanceService, CommandException

logger = logging.getLogger(__name__)


class MainConversation:
    _event_service = EventService()
    _command_parser = CommandParser()

    LOGIN, LISTENING = range(2)

    def _set_main_event(self, chat: Chat, context: CallbackContext):
        event = self._event_service.get_next_event()
        event_message = chat.send_message(text=str(event))
        context.user_data['event'] = event
        context.user_data['emsg'] = event_message

    @staticmethod
    def _refresh_main_event(context: CallbackContext):
        event = context.user_data['event'].refresh()
        new_msg_text = str(event)
        if new_msg_text != context.user_data['emsg'].text:
            context.user_data['emsg'].edit_text(new_msg_text)

    def _wrong_command(self, message):
        return message.reply_text("mmm... no te entendí.")

    def main(self, update: Update, context: CallbackContext):
        telegram_user = update.message.from_user
        user = sign_in(telegram_user)
        if user:
            context.user_data['user'] = user
            update.message.reply_text(
                f'Que haces {user.first_name}?'
            )
            self._set_main_event(update.effective_chat, context)
            return self.LISTENING
        else:
            update.message.reply_text(
                'Ey Ram. No te registro. Como es la contraseña?'
            )
            return self.LOGIN

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
            return self.LOGIN
        else:
            context.user_data['user'] = user
            update.message.reply_text(
                f'A si, de una. Vos sos {user.first_name}'
            )
            self._set_main_event(update.effective_chat, context)
            return self.LISTENING

    def listen(self, update: Update, context: CallbackContext):
        message = update.message
        to_delete = [message]

        try:
            command, kwargs = self._command_parser(message.text)
            attendance_service = AttendanceService(context.user_data['event'])
            if command == 'add_attendee':
                attendance_service.add_attendance(**kwargs)
            elif command == 'remove_attendee':
                attendance_service.remove_attendance(**kwargs)
            elif command == 'replace_host':
                attendance_service.replace_host(**kwargs)
            else:
                reply_message = self._wrong_command(message)
                to_delete.append(reply_message)
            self._refresh_main_event(context)
        except CommandException as ex:
            msg = message.reply_text(str(ex))
            to_delete.append(msg)
        finally:
            for msg in to_delete:
                msg.delete()
            return self.LISTENING

    def cancel(self, update: Update, context: CallbackContext) -> int:
        user = context.user_data['user']
        logger.info('Conversation canceled', extra={'telegram_id': user.telegram_id})
        update.message.reply_text(
            'Bueno, listo. Tomate el palo\n'
            'Si querés volvera hablar mandá /start'
        )

        return ConversationHandler.END

    def get_handler(self):
        return ConversationHandler(
            entry_points=[CommandHandler('start', self.main)],
            states={
                self.LOGIN: [MessageHandler(Filters.text, self.login)],
                self.LISTENING: [
                    MessageHandler(Filters.text & (~Filters.command), self.listen)
                ],
            },
            fallbacks=[CommandHandler('cancel', self.cancel)],
        )
