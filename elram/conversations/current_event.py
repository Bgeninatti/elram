from telegram import Update
from telegram.ext import CallbackContext

from elram.conversations.views import ask_user, show_main_menu
from elram.repository.models import User, Event


class CurrentEventConversation:

    ASK_ATTENDEES, MAIN_MENU = range(10, 12)

    def ask_atteendees(self, update: Update, context: CallbackContext):
        # Build initial message
        is_first_iteration = update.callback_query is not None
        message = update.callback_query.message if is_first_iteration else update.message
        attendees = context.user_data.get('attendees', [])
        if attendees:
            message.reply_text(
                'Hasta ahora a la peña van:\n'
                '\n'.join([a.nickname for a in attendees]),
            )

        if is_first_iteration:
            context.user_data['attendees'] = []
            ask_user(message, optional=True)
            return self.ASK_ATTENDEES
        if message.text == 'Por ahora no va nadie mas.':
            return self.MAIN_MENU

        new_attendee, _ = User.get_or_create(nickname=message.text.title())
        context.user_data['attendees'].append(new_attendee)
        ask_user(message, exclude=context.user_data['attendees'], optional=True)
        return self.ASK_ATTENDEES
