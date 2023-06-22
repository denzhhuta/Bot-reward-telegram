import aiogram
from aiogram import types, Bot, Dispatcher, executor
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.middlewares import BaseMiddleware
from aiogram.dispatcher.handler import CancelHandler
from aiogram.types import Update
from aiogram.types.chat_member import ChatMemberMember, ChatMemberOwner, ChatMemberAdministrator
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.types import CallbackQuery
from aiogram.contrib.fsm_storage.memory import MemoryStorage

from configuration import TOKEN_API
from keyboard import main_reply_keyboard, promocode_inline_keyboard
from database import add_user_to_database, check_user_credential, get_random_posts_from_db, add_post_to_awarded_messages, add_money, update_last_button_press_time, get_last_button_press_time, money_withdrawal, logs_handler
from datetime import datetime, timedelta
import random
import asyncio
import base64
import hashlib
import re
import csv
import os

storage = MemoryStorage()
bot = aiogram.Bot(TOKEN_API)
dp = aiogram.Dispatcher(bot, storage=storage)

post_mapping = {}

def generate_booking_identifier(user_id,post_id, chat_id):
    identifier_string = f"{user_id}{post_id}{chat_id}"
    identifier_hash = hashlib.md5(identifier_string.encode()).hexdigest()
    return identifier_hash


@dp.message_handler(commands=['start'])
async def start_command(message: types.Message) -> None:
    user_id = message.from_user.id
    first_name = message.from_user.first_name
    last_name = message.from_user.last_name
    print(user_id)
    #Registration process, by adding user id to the database.
    await add_user_to_database(user_id)
    
    if last_name is None:
        await bot.send_message(chat_id=message.from_user.id,
                           text=f"<b>Добро пожаловать, {message.from_user.first_name}!</b>",
                           parse_mode="HTML",
                           reply_markup = main_reply_keyboard())
    else:
        await bot.send_message(chat_id=message.from_user.id,
                           text=f"<b>Добро пожаловать, {message.from_user.first_name} {message.from_user.last_name}!</b>",
                           parse_mode="HTML",
                           reply_markup = main_reply_keyboard())
        
@dp.message_handler(text='Вывод денег 💳')
async def money_withdrawal_handler(message: types.Message, state: FSMContext) -> None:
    user_id = message.from_user.id

    await bot.send_message(chat_id=message.from_user.id,
                           text="<b>🧾 Пожалуйста, введите следующую информацию для получения платежа:</b>\n\n"\
                                "<b>IBAN</b> (Международный номер банковского счета)\n"\
                                "<b>Email</b> (Электронная почта)\n\n"\
                                "<b>Примеры:</b>\n"\
                                "<b>IBAN:</b> US01234567890123456789\n"\
                                "<b>Email:</b> example@example.com\n\n"
                                "<b>Пожалуйста, используйте формат:</b> IBAN-number, электронная почта",
                            parse_mode="HTML")
    
    await state.update_data(user_id=user_id)
    await state.set_state('payment_confirmation')
    
@dp.message_handler(state='payment_confirmation')
async def money_withdrawal_finish_handler(message: types.Message, state: FSMContext) -> None:
    payment_information = message.text.strip()
    
    if not re.match(r'^[A-Za-z]{2}\w{2,34},\s*\S+@\S+\.\S+$', payment_information):
        await message.answer("❌ <b>Неправильный формат ввода!</b>\n\n"
                             "<b>Пожалуйста, используйте формат: IBAN-номер, электронная почта.</b>",
                             parse_mode=types.ParseMode.HTML)
        
        await state.set_state('payment_confirmation')
        return
    
    iban, email = payment_information.split(",")
    
    print(iban)
    print(email)
    
    async with state.proxy() as data:
        user_id = data.get('user_id')
    
    result, previous_balance = await money_withdrawal(user_id)
    
    if previous_balance is not None:
        response = f"<b>💸 Деньги были успешно списаны!</b>\n<b>Сумма вывода: {previous_balance}$</b>\n\n"\
                   "Ваш запрос на вывод денег был отправлен на обработку. "\
                   "Пожалуйста, ожидайте, что деньги будут зачислены на ваш счёт в течение 5-7 рабочих дней."
                   
        emails = [email.strip()]
        ibans = [iban.strip()]
        filename = os.path.join("/Users/zgutadenis/Desktop/My Projects/Nayob-bot", "logs.csv")
        await logs_handler(emails, ibans, filename)
        
    else:
        response = result
        
    await bot.send_message(chat_id=message.from_user.id,
                           text=response,
                           parse_mode="HTML")
    
    await state.reset_state()



@dp.message_handler(text='Профиль 👤')
async def check_profile_handler(message: types.Message):
    user_id = message.from_user.id
    message_text = await check_user_credential(user_id)
    
    await bot.send_message(chat_id=message.from_user.id,
                     text=message_text,
                     parse_mode="HTML",
                     reply_markup=promocode_inline_keyboard())

@dp.message_handler(text='Зарабатывать 💸')
async def earn_money_handler(message: types.Message):
    # Get two random posts from the database
    user_id = message.from_user.id
    
    last_press_time = await get_last_button_press_time(user_id)
    #Перевірка скільки часу залишилося до нового юза бота!
    if last_press_time is not None:
        current_time = datetime.now()
        time_diff = current_time - last_press_time
        remaining_time = timedelta(days=1) - time_diff

        if remaining_time.total_seconds() > 0:
            hours, remainder = divmod(remaining_time.seconds, 3600) #3780 секунд лишається, тоді воно розбиває як 1 година 180 сек і кидає вниз
            minutes, seconds = divmod(remainder, 60)
            remaining_time_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
            await message.reply(f"<b>Вы можете снова использовать кнопку через {remaining_time_str}.</b>",
                                parse_mode=types.ParseMode.HTML)
            return

    posts = await get_random_posts_from_db(user_id, limit=2)

    for post in posts:
        text = post['text']
        link = post['link']
        post_id = post['id']
        chat_id = post['chat_id']
        
        # Encode the chat_id before passing it as callback_data
        post_identifier = generate_booking_identifier(user_id, post_id, chat_id)
        
        button_callback_data = f"check_subscription_{post_identifier}"
        post_mapping[post_identifier] = {
            'id': user_id,
            'post_id': post_id,
            'chat_id': chat_id
        }
        
        # Create inline keyboard markup with a button for the post link
        keyboard_markup = types.InlineKeyboardMarkup()
        keyboard_markup.add(types.InlineKeyboardButton("Read More", url=link))
        keyboard_markup.add(types.InlineKeyboardButton("Check Subscription", callback_data=button_callback_data))

        # Send the message with the post and the button
        await bot.send_message(chat_id=message.from_user.id,
                               text=text,
                               reply_markup=keyboard_markup)
        await asyncio.sleep(1)  # Add a small delay between each message

    await update_last_button_press_time(user_id)
    

@dp.callback_query_handler(lambda callback_query: callback_query.data.startswith('check_subscription_'))
async def check_subscription_handler(callback: types.CallbackQuery, state: FSMContext):
    post_identifier = callback.data.split('_')[2]
    
    post_details = post_mapping.get(post_identifier)
    
    if post_details:
        user_id = post_details['id']
        post_id = post_details['post_id']
        chat_id = post_details['chat_id']

        if post_id and user_id and chat_id:
            check_user_in_channel = await bot.get_chat_member(chat_id, user_id)
            if not isinstance(check_user_in_channel, ChatMemberMember) and not isinstance(check_user_in_channel, ChatMemberOwner) and not isinstance(check_user_in_channel, ChatMemberAdministrator):
                await bot.send_message(chat_id=callback.message.chat.id,
                                   text='<b>❌ К сожалению, вы не подписаны на канал!</b>',
                                   parse_mode='HTML')
            else:
                try:
                    await add_post_to_awarded_messages(user_id, post_id)
                    
                    await add_money(user_id)
                    
                    await bot.send_message(chat_id=callback.message.chat.id,
                                       text='<b>☑️ Вы получили награду 0.50$</b>',
                                       parse_mode='HTML')
                except Exception:
                    await bot.send_message(chat_id=callback.message.chat.id,
                                           text='<b>❌ Вы уже получили награду за этот пост!</b>',
                                           parse_mode='HTML')
    
    else:
        await bot.send_message(chat_id=callback.message.chat.id,
                               text='<b>😔 Пост не найден!</b>',
                               parse_mode='HTML')

    
        
if __name__ == '__main__':
    executor.start_polling(dp, 
                           skip_updates=True) 