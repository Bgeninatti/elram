from typing import List, Optional

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ConversationHandler

from elram.conversations.states import MAIN_MENU, NEW_EVENT, CLOSE_EVENT, LIST_EVENTS, SHOW_BALANCE
from elram.repository.models import User, Event


def ask_user(message, exclude: Optional[List[User]] = None, optional: bool = False):

    if exclude is not None:
        excluded_ids = [u.id for u in exclude]
        users = User.select(User.not_in(excluded_ids))
    else:
        users = User.select()

    buttons = [
        [KeyboardButton(text=u.nickname)]
        for u in users
    ]
    if optional:
        buttons.append([KeyboardButton(text='Ya terminé.')])

    keyboard = ReplyKeyboardMarkup(
        keyboard=buttons,
        one_time_keyboard=True,
    )
    message.reply_text(
        'Si el nombre no aparece en la lista escribilo y yo lo agrego.',
        reply_markup=keyboard
    )


def show_main_menu(message):
    event = Event.get_active()
    if event is None:
        message.reply_text(
            'Ahora no hay ninguna peña activa. Están todos re tirados.'
        )
        buttons = [[InlineKeyboardButton(text='Crear una peña', callback_data=NEW_EVENT)]]

    else:
        message.reply_text(
            'La próxima peña es esta.'
        )
        message.reply_text(str(event))
        buttons = [[InlineKeyboardButton(text='Cerrar peña actual', callback_data=CLOSE_EVENT)]]

    buttons += [
        [InlineKeyboardButton(text='Ver peñas viejas', callback_data=LIST_EVENTS)],
        [InlineKeyboardButton(text='Ver saldos', callback_data=SHOW_BALANCE)],
        [InlineKeyboardButton(text='Tomarme el palo', callback_data=ConversationHandler.END)],
    ]
    main_menu = InlineKeyboardMarkup(buttons)
    message.reply_text(
        'Bueno, que querés hacer?',
        reply_markup=main_menu,
    )
    return MAIN_MENU
