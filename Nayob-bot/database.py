import aiogram
import aiomysql
import asyncio
from datetime import datetime
from configuration import DB_HOST, DB_USER, DB_NAME, DB_PASSWORD
from datetime import datetime
import random
import json
import csv
import os

#Connect to the Database;
async def connect_to_db():
    try:
        conn = await aiomysql.connect(
            host=DB_HOST,
            port=3306,
            user=DB_USER,
            password=DB_PASSWORD,
            db=DB_NAME,
            cursorclass=aiomysql.DictCursor)
    
        print("Connected successfully...")
        return conn
     
    except Exception as ex:
        print("Connection to DataBase refused...")
        print(ex)

#Function to add a user to the bot, when he/she reg + сheck, whea. user exists in the DB;
async def add_user_to_database(user_id: int):
    conn = await connect_to_db()
    async with conn.cursor() as cursor:
        select_query = "SELECT user_id FROM users WHERE user_id = %s"
        await cursor.execute(select_query, (user_id,))
        result = await cursor.fetchone()
        
        if result is None:
            registration_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            insert_query = "INSERT INTO users (user_id, registration_date) VALUES (%s, %s)"
            await cursor.execute(insert_query, (user_id, registration_date))
            await conn.commit()
        
        else:
            pass
            print("Already in DB")

    conn.close()

#Function to check user's credential for the field "Профиль"
async def check_user_credential(user_id: int):
    conn = await connect_to_db()
    async with conn.cursor() as cursor:
        select_query = "SELECT * FROM users WHERE user_id = %s"
        await cursor.execute(select_query, (user_id, ))
        result = await cursor.fetchone()

    conn.close()

    STRUCTURED_MESSAGE = """
<b>👤 Ваш профиль</b>

<b>🆔 ID: {user_id}</b>
<b>📆 Дата регистрации: {registration_date}</b>
<b>💰 Баланс: {money}$</b>
    """

    if result:
        registration_date = result['registration_date'].date()  # Extracting only the date
        message_text = STRUCTURED_MESSAGE.format(
            user_id=result['user_id'],
            registration_date=registration_date,
            money=result['money']
        )
        return message_text

    else:
        return '<b>😔 Ошибка! Обратитесь к администратору бота!</b>'

#Function to get random posts from the DB (to modify!!!!!)
async def get_random_posts_from_db(user_id: int, limit=2):
    conn = await connect_to_db()
    async with conn.cursor() as cursor:
        select_query = """
        SELECT *
        FROM posts
        WHERE active = 0
          AND (JSON_CONTAINS(
            (SELECT awarded_messages FROM users WHERE user_id = %s),
            CAST(id AS JSON),
            '$'
          ) = 0
          OR (SELECT awarded_messages FROM users WHERE user_id = %s) IS NULL)
          AND ((SELECT last_post_time FROM users WHERE user_id = %s) IS NULL
               OR (SELECT last_post_time FROM users WHERE user_id = %s) <= DATE_SUB(NOW(), INTERVAL 1 DAY))
        ORDER BY RAND()
        LIMIT %s
        """
        # The additional condition in the query checks if the last_post_time is either NULL or more than 24 hours ago

        await cursor.execute(select_query, (user_id, user_id, user_id, user_id, limit))
        rows = await cursor.fetchall()
        
    conn.close()
    return rows


#Function to add awarded (used post) to the json array
async def add_post_to_awarded_messages(user_id: int, post_id: int):
    conn = await connect_to_db()
    async with conn.cursor() as cursor:
        select_query = """
        SELECT awarded_messages
        FROM users
        WHERE user_id = %s
        """
        await cursor.execute(select_query, (user_id,))
        result = await cursor.fetchone()
        
        if result is not None:
            awarded_messages = result['awarded_messages']
            if awarded_messages is not None:
                awarded_messages = json.loads(awarded_messages)
            else:
                awarded_messages = []
        else:
            awarded_messages = []
        
        if post_id not in awarded_messages:
            awarded_messages.append(post_id)
        else:
            raise Exception("The post is already awarded.")
        
        update_query = """
        UPDATE users
        SET awarded_messages = %s
        WHERE user_id = %s
        """
        await cursor.execute(update_query, (json.dumps(awarded_messages), user_id))
        
        await conn.commit()
        
    conn.close()

#Adding money to the database corresponding to user's id
async def add_money(user_id: int):
    conn = await connect_to_db()
    async with conn.cursor() as cursor:
        update_query = """
        UPDATE users
        SET money = money + 0.50
        WHERE user_id = %s
        """
        await cursor.execute(update_query, (user_id,))
        
        await conn.commit()

    conn.close()
    
#Function to update last time button pressed to earn money
async def update_last_button_press_time(user_id: int):
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    conn = await connect_to_db()
    async with conn.cursor() as cursor:
        update_query = """
        UPDATE users
        SET last_post_time = %s
        WHERE user_id = %s
        """
        await cursor.execute(update_query, (current_time, user_id))
        await conn.commit()

    conn.close()

#Function to check when user last time receiver posts
async def get_last_button_press_time(user_id: int):
    conn = await connect_to_db()
    async with conn.cursor() as cursor:
        select_query = """
        SELECT last_post_time
        FROM users
        WHERE user_id = %s
        """
        await cursor.execute(select_query, (user_id,))
        result = await cursor.fetchone()

    conn.close()

    if result is not None:
        last_press_time = result['last_post_time']
        if last_press_time is not None:
            return last_press_time

    return None

#Function to withdraw money
async def money_withdrawal(user_id: int):
    conn = await connect_to_db()
    async with conn.cursor() as cursor:
        select_query = """
        SELECT money
        FROM users
        WHERE user_id = %s
        """
        await cursor.execute(select_query, (user_id,))
        balance = await cursor.fetchone()
        if balance['money'] >= 17:
            previous_balance = balance['money']
            new_balance = 0

            update_query = """
            UPDATE users
            SET money = %s
            WHERE user_id = %s
            """
            await cursor.execute(update_query, (new_balance, user_id))
            await conn.commit()

            return "<b>Деньги были успешно списаны!</b>", previous_balance

        else:
            return "<b>😔 На вашем балансе недостаточно денег для списания!</b>", None

async def logs_handler(emails, ibans, filename):
    try:
        with open(filename, 'a+', newline='') as file:
            if file.tell() == 0:  # Check if the file is empty
                writer = csv.writer(file)
                writer.writerow(['Emails', 'IBANs'])  # Write header if the file is empty
            file.seek(0, os.SEEK_END)  # Move the file pointer to the end
            writer = csv.writer(file)
            writer.writerows(zip(emails, ibans))  # Write email and IBAN data
        print(f"Successfully appended emails and IBANs to CSV file: {filename}")
    except Exception as e:
        print(f"Error appending emails and IBANs to CSV file: {filename}\n{e}")

   