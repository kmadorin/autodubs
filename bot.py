import streamlit as st
import os
import httpx
import httpcore
import re
from autodubs import dub_yt_video, dub_video_file, compress_video, combine_video
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from telegram import Update

TELEGRAM_API_KEY = st.secrets["telegram_key"]


async def process_youtube_video(update: Update, context: ContextTypes.DEFAULT_TYPE, yt_video_link: str):
    try:
        print("Dubbing YouTube video...")
        output_filename = dub_yt_video(yt_video_link, "Russian")
        await send_processed_video(update, context, output_filename)
    except Exception as e:
        await handle_error(update, context, e)

async def process_telegram_video(update, context):
    try:
        print("Processing Telegram video...")
        video_file = await context.bot.get_file(update.message.video.file_id)
        video_path = f"temp_video_{update.effective_chat.id}.mp4"
        await video_file.download_to_drive(video_path)
        output_filename = dub_video_file(video_path, "Russian")
        os.remove(video_path)  # Remove the temporary video file
        await send_processed_video(update, context, output_filename)
    except Exception as e:
        await handle_error(update, context, e)

async def send_processed_video(update: Update, context: ContextTypes.DEFAULT_TYPE, output_filename: str):
    file_size = os.path.getsize(output_filename) / (1024 * 1024)  # Size in MB

    if file_size <= 50:
        video_to_send = output_filename
    else:
        compressed_filename = f"output_compressed_{update.effective_chat.id}.mp4"
        compress_video(output_filename, compressed_filename)
        video_to_send = compressed_filename

    with open(video_to_send, "rb") as video_file:
        await context.bot.send_video(chat_id=update.effective_chat.id, video=video_file, caption="Here is your dub!")

    # Clean up files
    # os.remove(output_filename)
    # if video_to_send != output_filename:
    #     os.remove(video_to_send)

    await context.bot.send_message(chat_id=update.effective_chat.id, text="Here is your dub!")

async def handle_error(update: Update, context: ContextTypes.DEFAULT_TYPE, error: Exception):
    if isinstance(error, (httpx.TimeoutException, httpcore.WriteTimeout)):
        error_message = f"Sorry, there was a network timeout. Please try again later. Error: {str(error)}"
    else:
        error_message = f"An unexpected error occurred. Please try again later. Error: {str(error)}"
    await context.bot.send_message(chat_id=update.effective_chat.id, text=error_message)

async def start(update, context):
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Welcome to the Telegram bot!")

async def handle_message(update, context):
    print(update.effective_chat.id)

    if update.message.text:
        # Handle text messages with YouTube links
        user_message = update.message.text
        youtube_regex = r'(https?://)?(www\.)?(youtube|youtu|youtube-nocookie)\.(com|be)/(watch\?v=|embed/|v/|.+\?v=)?([^&=%\?]{11})'
        match = re.search(youtube_regex, user_message)

        if match:
            yt_video_link = match.group()
            await process_youtube_video(update, context, yt_video_link)
        else:
            await context.bot.send_message(chat_id=update.effective_chat.id, text="No YouTube video link found in the message.")

    elif update.message.video:
        # Handle video messages
        await process_telegram_video(update, context)

    else:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Please send a YouTube link or a video message.")

def main() -> None:
    application = ApplicationBuilder().token(TELEGRAM_API_KEY).build()

    start_handler = CommandHandler("start", start)
    message_handler = MessageHandler(filters.TEXT | filters.VIDEO & (~filters.COMMAND), handle_message)

    application.add_handler(start_handler)
    application.add_handler(message_handler)

    application.run_polling()


if __name__ == "__main__":
    main()
