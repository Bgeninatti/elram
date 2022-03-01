from typing import List, Optional

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ConversationHandler

from elram.conversations.states import MAIN_MENU, NEW_EVENT, CLOSE_EVENT, LIST_EVENTS, SHOW_BALANCE
from elram.repository.models import User, Event


def ask_user(
    message,
    exclude: Optional[List[User]] = None,
    optional: bool = False,
    hosts_only: bool = False,
    allow_create: bool = False,
):
    users = User.select()

    if hosts_only:
        users = users.where(User.is_host)

    if exclude is not None:
        excluded_ids = [u.id for u in exclude]
        users = users.where(User.not_in(excluded_ids))

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

    if allow_create:
        msg = 'Si el nombre no aparece en la lista escribilo y yo lo agrego.'
    else:
        msg = 'Elegí un nombre de la lista.'

    message.reply_text(msg, reply_markup=keyboard)


def show_main_menu(message):
    event = Event.get_active()
    if event is None:
        event = Event.get_next_event()
        message.reply_text(
            'Ahora no hay ninguna peña activa.'
        )
        message.reply_text(
            f'La próxima sería la {event}'
        )

        buttons = [[InlineKeyboardButton(text='Activar próxima peña', callback_data=NEW_EVENT)]]
    else:
        message.reply_text(
            f'La próxima peña es la {event}'
        )
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
