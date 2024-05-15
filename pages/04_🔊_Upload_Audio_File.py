import whisper
import streamlit as st
from streamlit_lottie import st_lottie
from utils import write_vtt, write_srt
from flores200_codes import flores_codes
import ffmpeg
import requests
from typing import Iterator
from io import StringIO
import numpy as np
import pathlib
import os

st.set_page_config(page_title="Auto Transcriber", page_icon="🔊", layout="wide")

# Sema Translator
Public_Url = 'https://lewiskimaru-helloworld.hf.space' #endpoint

# Define a function that we can use to load lottie files from a link.
@st.cache(allow_output_mutation=True)
def load_lottieurl(url: str):
    r = requests.get(url)
    if r.status_code != 200:
        return None
    return r.json()


APP_DIR = pathlib.Path(__file__).parent.absolute()

LOCAL_DIR = APP_DIR / "local_audio"
LOCAL_DIR.mkdir(exist_ok=True)
save_dir = LOCAL_DIR / "output"
save_dir.mkdir(exist_ok=True)


col1, col2 = st.columns([1, 3])
with col1:
    lottie = load_lottieurl("https://assets1.lottiefiles.com/packages/lf20_1xbk4d2v.json")
    st_lottie(lottie)

with col2:
    st.write("""
    ## Sema Audio Transcriber
    ##### Input an audio file and get a transcript.
    ###### ➠ If you want to transcribe the audio in its original language, select the task as "Transcribe"
    ###### ➠ If you want to translate the subtitles to English, select the task as "Translate with Whisper" 
    ###### ➠ If you want to translate the subtitles from English to any of the 200 supported languages, select the task as "Translate with Sema" """)

loaded_model = whisper.load_model("base")
current_size = "None"


@st.cache(allow_output_mutation=True)
def change_model(current_size, size):
    if current_size != size:
        loaded_model = whisper.load_model(size)
        return loaded_model
    else:
        raise Exception("Model size is the same as the current size.")

@st.cache(allow_output_mutation=True)
def inferecence(loaded_model, uploaded_file, task):
    with open(f"{save_dir}/input.mp3", "wb") as f:
            f.write(uploaded_file.read())
    audio = ffmpeg.input(f"{save_dir}/input.mp3")
    audio = ffmpeg.output(audio, f"{save_dir}/output.wav", acodec="pcm_s16le", ac=1, ar="16k")
    ffmpeg.run(audio, overwrite_output=True)
    if task == "Transcribe":
        options = dict(task="transcribe", best_of=5)
        results = loaded_model.transcribe(f"{save_dir}/output.wav", **options)
        vtt = getSubs(results["segments"], "vtt", 80)
        srt = getSubs(results["segments"], "srt", 80)
        lang = results["language"]
        return results["text"], vtt, srt, lang
    elif task == "Translate":
        options = dict(task="translate", best_of=5)
        results = loaded_model.transcribe(f"{save_dir}/output.wav", **options)
        vtt = getSubs(results["segments"], "vtt", 80)
        srt = getSubs(results["segments"], "srt", 80)
        lang = results["language"]
        return results["text"], vtt, srt, lang
    else:
        raise ValueError("Task not supported")


def getSubs(segments: Iterator[dict], format: str, maxLineWidth: int) -> str:
    segmentStream = StringIO()

    if format == 'vtt':
        write_vtt(segments, file=segmentStream, maxLineWidth=maxLineWidth)
    elif format == 'srt':
        write_srt(segments, file=segmentStream, maxLineWidth=maxLineWidth)
    else:
        raise Exception("Unknown format " + format)

    segmentStream.seek(0)
    return segmentStream.read()

def translate(userinput, target_lang, source_lang=None):
    if source_lang:
       url = f"{Public_Url}/translate_enter/"
       data = {
           "userinput": userinput,
           "source_lang": source_lang,
           "target_lang": target_lang,
        }
       response = requests.post(url, json=data)
       result = response.json()
       print(type(result))
       source_lange = source_lang
       translation = result['translated_text']
       
    else:
      url = f"{Public_Url}/translate_detect/"
      data = {
        "userinput": userinput,
        "target_lang": target_lang,
      }

      response = requests.post(url, json=data)
      result = response.json()
      source_lange = result['source_language']
      translation = result['translated_text']
    return source_lange, translation

def main():
    size = st.selectbox("Select Model Size (The larger the model, the more accurate the transcription will be, but it will take longer)", ["tiny", "base", "small", "medium", "large"], index=1)
    loaded_model = change_model(current_size, size)
    st.write(f"Model is {'multilingual' if loaded_model.is_multilingual else 'English-only'} "
        f"and has {sum(np.prod(p.shape) for p in loaded_model.parameters()):,} parameters.")
    input_file = st.file_uploader("Upload an audio file", type=["mp3", "wav", "m4a"])
    if input_file is not None:
        filename = input_file.name[:-4]
    else:
        filename = None
    task = st.selectbox("Select Task", ["Transcribe", "Translate with Whisper", "Translate with Sema"], index=0)
    if task == "Transcribe":
        if st.button("Transcribe"):
            results = inferecence(loaded_model, input_file, task)
            col3, col4 = st.columns(2)
            col5, col6, col7 = st.columns(3)
            col9, col10 = st.columns(2)
            
            with col3:
                st.audio(input_file)
                
            with open("transcript.txt", "w+", encoding='utf8') as f:
                f.writelines(results[0])
                f.close()
            with open(os.path.join(os.getcwd(), "transcript.txt"), "rb") as f:
                datatxt = f.read()
                

            with open("transcript.vtt", "w+",encoding='utf8') as f:
                f.writelines(results[1])
                f.close()
            with open(os.path.join(os.getcwd(), "transcript.vtt"), "rb") as f:
                datavtt = f.read()
                
            with open("transcript.srt", "w+",encoding='utf8') as f:
                f.writelines(results[2])
                f.close()
            with open(os.path.join(os.getcwd(), "transcript.srt"), "rb") as f:
                datasrt = f.read()

            with col5:
                st.download_button(label="Download Transcript (.txt)",
                                data=datatxt,
                                file_name="transcript.txt")
            with col6:   
                st.download_button(label="Download Transcript (.vtt)",
                                    data=datavtt,
                                    file_name="transcript.vtt")
            with col7:
                st.download_button(label="Download Transcript (.srt)",
                                    data=datasrt,
                                    file_name="transcript.srt")
            with col9:
                st.success("You can download the transcript in .srt format, edit it (if you need to) and upload it to YouTube to create subtitles for your video.")
            with col10:
                st.info("Streamlit refreshes after the download button is clicked. The data is cached so you can download the transcript again without having to transcribe the video again.")

    elif task == "Translate with Whisper":
        if st.button("Translate to English"):
            results = inferecence(loaded_model, input_file, task)
            col3, col4 = st.columns(2)
            col5, col6, col7 = st.columns(3)
            col9, col10 = st.columns(2)

            with col3:
                st.audio(input_file)
                
            with open("transcript.txt", "w+", encoding='utf8') as f:
                f.writelines(results[0])
                f.close()
            with open(os.path.join(os.getcwd(), "transcript.txt"), "rb") as f:
                datatxt = f.read()
                

            with open("transcript.vtt", "w+",encoding='utf8') as f:
                f.writelines(results[1])
                f.close()
            with open(os.path.join(os.getcwd(), "transcript.vtt"), "rb") as f:
                datavtt = f.read()
                
            with open("transcript.srt", "w+",encoding='utf8') as f:
                f.writelines(results[2])
                f.close()
            with open(os.path.join(os.getcwd(), "transcript.srt"), "rb") as f:
                datasrt = f.read()
                
            with col5:
                st.download_button(label="Download Transcript (.txt)",
                                data=datatxt,
                                file_name="transcript.txt")
            with col6:   
                st.download_button(label="Download Transcript (.vtt)",
                                    data=datavtt,
                                    file_name="transcript.vtt")
            with col7:
                st.download_button(label="Download Transcript (.srt)",
                                    data=datasrt,
                                    file_name="transcript.srt")
            with col9:
                st.success("You can download the transcript in .srt format, edit it (if you need to) and upload it to YouTube to create subtitles for your video.")
            with col10:
                st.info("Streamlit refreshes after the download button is clicked. The data is cached so you can download the transcript again without having to transcribe the video again.")
    
    elif task == "Translate with Sema":
        default_language = "French"
        target = st.selectbox("Select Language", list(flores_codes.keys()), index=list(flores_codes.keys()).index(default_language))
        target_code = flores_codes[target]
        
    else:
        st.error("Please select a task.")


if __name__ == "__main__":
    main()
    st.markdown("###### ")
    st.markdown("###### Powered by [sema © 2024](https://www.sema.wiki)")
