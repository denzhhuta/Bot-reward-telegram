@dp.message_handler(text='Зарабатывать 💸')
async def earn_money_handler(message: types.Message):
    # Get two random posts from the database
    user_id = message.from_user.id
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