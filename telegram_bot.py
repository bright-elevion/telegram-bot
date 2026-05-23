import os
import subprocess
import telebot
from telebot import types

# --- CONFIGURATION ---
# We use environment variables for security on Railway
API_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

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
    
    # Common yt-dlp arguments to handle errors and redirects
    # --ignore-errors: continue even if some formats/embeds fail
    # --no-playlist: usually we want just one video, but myanime.live links are treated as playlists
    # --playlist-items 1,2,3...: we'll try to get the first working one
    common_args = [
        "yt-dlp",
        "-f", "best[height<=360]/best",
        "-o", output_template,
        "--ignore-errors",
        "--no-warnings",
        "--playlist-items", "1,2,3,4,5", # Try first 5 items in case some embeds are broken
    ]

    try:
        # 1. Get the expected filename
        # We use --get-filename to know what file will be created
        # Since we might have multiple items, we take the first line that looks like a filename
        command_get_name = common_args + ["--get-filename", url]
        output = subprocess.check_output(command_get_name).decode('utf-8').strip()
        
        # Filter output to get the first non-empty line (filename)
        filenames = [line.strip() for line in output.split('\n') if line.strip() and not line.startswith('WARNING')]
        if not filenames:
            raise Exception("Could not determine output filename. The link might be protected or unsupported.")
        
        filename = filenames[0]
        
        # 2. Actually download
        bot.edit_message_text("📥 Downloading video... This may take a minute.", chat_id=msg.chat.id, message_id=msg.message_id)
        download_command = common_args + [url]
        subprocess.run(download_command, check=True)
        
        # Check if file exists (it might have a slightly different name if yt-dlp changed it)
        if not os.path.exists(filename):
            # Try to find the file in the current directory starting with the prefix
            prefix = f"video_{message.chat.id}_"
            possible_files = [f for f in os.listdir('.') if f.startswith(prefix)]
            if possible_files:
                filename = possible_files[0]
            else:
                raise Exception("Download finished but video file not found.")

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
        # Try to clean up any partial files
        prefix = f"video_{message.chat.id}_"
        for f in os.listdir('.'):
            if f.startswith(prefix):
                try: os.remove(f)
                except: pass
        
        bot.edit_message_text(f"❌ Error: {str(e)}\n\nNote: Some videos on myanime.live use protected players (like Dailymotion) that may block downloads. Try another link if this persists.", chat_id=msg.chat.id, message_id=msg.message_id)

print("Bot is running...")
bot.infinity_polling()

