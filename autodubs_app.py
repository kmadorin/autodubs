import os
import subprocess
import streamlit as st
import whisper
import pandas as pd
import anthropic
from pytubefix import YouTube
from pytubefix.cli import on_progress
from pydub import AudioSegment
from elevenlabs.client import ElevenLabs, Voice, VoiceSettings
from moviepy.video.io.ffmpeg_tools import ffmpeg_extract_subclip

import os
from pydub import AudioSegment

def shorten_audio(filename):    
    # Check if the file exists, if not create an empty file
    if not os.path.exists(filename):
        open(filename, 'a').close()
    
    # Load the audio file
    audio = AudioSegment.from_file(filename)
    
    # Cut the audio to 60 seconds
    cut_audio = audio[:60 * 1000]
    
    # Export the shortened audio
    cut_audio.export(filename, format="mp4")
    
    return filename

def generate_translation(original_text, destination_language):
    prompt = (f"{anthropic.HUMAN_PROMPT} Please translate this video transcript into {destination_language}. You will get to the translation directly after I prompted 'the translation:'"
    f"{anthropic.AI_PROMPT} Understood, I will get to the translation without any opening lines."
    f"{anthropic.HUMAN_PROMPT} Great! this is the transcript: {original_text}; the translation:")
    
    c = anthropic.Anthropic(api_key=st.secrets["claude_key"])

    resp = c.completions.create(
        prompt=f"{prompt} {anthropic.AI_PROMPT}",
        stop_sequences=[anthropic.HUMAN_PROMPT],
        model="claude-v1.3-100k",
        max_tokens_to_sample=900,
    )

    return resp.completion

def generate_dubs(client, text):
    filename = "output.mp3"

    response = client.generate(
        text=text,
        voice=Voice(
        voice_id='ZXaNFwkRMa3G1wQ3tCeJ',
            settings=VoiceSettings(stability=0.43, similarity_boost=0.65, style=0.46, use_speaker_boost=False)
        ),
        # voice="Aria",
        model='eleven_multilingual_v2'
    )

    with open(filename, "wb") as f:
        for chunk in response:
            if chunk:
                f.write(chunk)

    # Writing the audio stream to the file

    return filename

def combine_video(video_filename, audio_filename):
    ffmpeg_extract_subclip(video_filename, 0, 60, targetname="cut_video.mp4")
    output_filename = "output.mp4"
    command = ["ffmpeg", "-y", "-i", "cut_video.mp4", "-i", audio_filename, "-c:v", "copy", "-c:a", "aac", output_filename]
    subprocess.run(command)
    return output_filename


client = ElevenLabs(
  api_key=st.secrets['xi_api_key'],
)

st.title("AutoDubs 📺🎵")

link = st.text_input("Link to Youtube Video", key="link")

language = st.selectbox("Translate to", ("French", "German", "Hindi", "Italian", "Russian", "Serbian", "Polish", "Portuguese", "Spanish"))

if st.button("Transcribe!"):
    print(f"downloading from link: {link}")
    model = whisper.load_model("base")
    yt = YouTube(link, on_progress_callback = on_progress)

    if yt is not None:
        st.subheader(yt.title)
        st.image(yt.thumbnail_url)
        audio_name = st.caption("Downloading audio stream...")
        audio_streams = yt.streams.filter(only_audio=True)
        filename = audio_streams.first().download()
        print(f"filename: {filename}");
        if filename:
            audio_name.caption(filename)
            cut_audio = shorten_audio(filename)
            transcription = model.transcribe(cut_audio)
            print(transcription)
        if transcription:
            df = pd.DataFrame(transcription['segments'], columns=['start', 'end', 'text'])
            st.dataframe(df)
            dubbing_caption = st.caption("Generating translation...")
            translation = generate_translation(transcription['text'], language)
            dubbing_caption = st.caption("Begin dubbing...")
            dubs_audio = generate_dubs(client, translation)
            dubbing_caption.caption("Dubs generated! combining with the video...")
            video_streams = yt.streams.filter(only_video=True)
            video_filename = video_streams.first().download()
            if video_filename:
                dubbing_caption.caption("Video downloaded! combining the video and the dubs...")
                output_filename = combine_video(video_filename, dubs_audio)
                if os.path.exists(output_filename):
                    dubbing_caption.caption("Video  successfully dubbed! Enjoy! 😀")
                    st.video(output_filename)
        