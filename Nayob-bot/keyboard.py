from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup

def main_reply_keyboard() -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    b1 = KeyboardButton(text="Профиль 👤")
    b2 = KeyboardButton(text="Зарабатывать 💸")
    b3 = KeyboardButton(text="Вывод денег 💳")
    kb.add(b1).add(b2).insert(b3)
    return kb

def promocode_inline_keyboard() -> InlineKeyboardMarkup:
    ikb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton('🎁 Реферальная система', callback_data='referral_system' )]
    ])
    return ikb