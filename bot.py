import streamlit as st
import os
import httpx
import httpcore
import re
from autodubs import dub_yt_video
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters

TELEGRAM_API_KEY = st.secrets["telegram_key"]

async def start(update, context):
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Welcome to the Telegram bot!")

async def handle_message(update, context):
    print(update.effective_chat.id)
    user_message = update.message.text

    # Check if the message contains a YouTube video link
    youtube_regex = r'(https?://)?(www\.)?(youtube|youtu|youtube-nocookie)\.(com|be)/(watch\?v=|embed/|v/|.+\?v=)?([^&=%\?]{11})'
    match = re.search(youtube_regex, user_message)

    if match:
        yt_video_link = match.group()
        try:
            print("dubbing...")
            output_filename = dub_yt_video(yt_video_link, "Russian")
            file_size = os.path.getsize(output_filename) / (1024 * 1024)  # Size in MB
            
            if file_size <= 50:
                video_to_send = output_filename
            else:
                from autodubs import compress_video_advanced
                compressed_filename = "output_compressed.mp4"
                compress_video_advanced(output_filename, compressed_filename)
                video_to_send = compressed_filename
            with open(video_to_send, "rb") as video_file:
                await context.bot.send_video(chat_id=update.effective_chat.id, video=video_file, caption="Here is your dub!")
                video_file.close()
            await context.bot.send_message(chat_id=update.effective_chat.id, text="Here is your dub!")
        except (httpx.TimeoutException, httpcore.WriteTimeout) as e:
            error_message = f"Sorry, there was a network timeout. Please try again later. Error: {str(e)}"
            await context.bot.send_message(chat_id=update.effective_chat.id, text=error_message)
        except Exception as e:
            error_message = f"An unexpected error occurred. Please try again later. Error: {str(e)}"
            await context.bot.send_message(chat_id=update.effective_chat.id, text=error_message)
    else:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="No Youtube video attached")


def main() -> None:
    application = ApplicationBuilder().token(TELEGRAM_API_KEY).build()

    start_handler = CommandHandler("start", start)
    message_handler = MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message)

    application.add_handler(start_handler)
    application.add_handler(message_handler)

    application.run_polling()


if __name__ == "__main__":
    main()