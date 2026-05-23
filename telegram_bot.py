import os
import subprocess
import telebot
from telebot import types

# --- CONFIGURATION ---
# We use environment variables for security on Railway
API_TOKEN = os.getenv('8919213509:AAFchvoOBEHhwFg9WrEDj8cGQuBA6As58Cg')

if not API_TOKEN:
    print("Error: TELEGRAM_BOT_TOKEN environment variable not set.")
    exit(1)

bot = telebot.TeleBot(API_TOKEN)

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message, "Welcome! Send me a link from myanime.live and I will download the video for you in 360p.")

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    url = message.text
    if "myanime.live" not in url:
        bot.reply_to(message, "Please send a valid link from myanime.live")
        return

    msg = bot.reply_to(message, "🔍 Analyzing link and starting download (360p)... Please wait.")
    
    # Define output filename
    # Using a unique name to avoid conflicts
    output_template = f"video_{message.chat.id}_%(title)s.%(ext)s"
    
    try:
        # 1. Get the expected filename
        command_get_name = [
            "yt-dlp",
            "-f", "best[height=360]",
            "-o", output_template,
            "--get-filename",
            url
        ]
        filename = subprocess.check_output(command_get_name).decode('utf-8').strip()
        
        # 2. Actually download
        download_command = [
            "yt-dlp",
            "-f", "best[height=360]",
            "-o", output_template,
            url
        ]
        subprocess.run(download_command, check=True)
        
        # 3. Send the file to the user
        bot.edit_message_text("✅ Download complete! Uploading to Telegram...", chat_id=msg.chat.id, message_id=msg.message_id)
        
        with open(filename, 'rb') as video:
            bot.send_video(message.chat.id, video, caption=f"Here is your video: {os.path.basename(filename)}")
            
        # Clean up the file after sending
        if os.path.exists(filename):
            os.remove(filename)
        bot.delete_message(chat_id=msg.chat.id, message_id=msg.message_id)

    except Exception as e:
        print(f"Error: {e}")
        bot.edit_message_text(f"❌ Error: {str(e)}", chat_id=msg.chat.id, message_id=msg.message_id)

print("Bot is running...")
bot.infinity_polling()
