import streamlit as st
import asyncio
import nest_asyncio
import atexit
import sys
from google.generativeai import GenerativeModel, list_models
import google.generativeai as genai
from pathlib import Path
import toml
import requests
import PyPDF2
import io
import numpy as np
import queue
import threading
import sounddevice as sd
from faster_whisper import WhisperModel
import contextlib

# Apply nest_asyncio to handle nested event loops
nest_asyncio.apply()

def cleanup_resources():
    if 'transcription_manager' in st.session_state:
        with contextlib.suppress(Exception):
            st.session_state.transcription_manager.stop()

# Register cleanup on normal exit
atexit.register(cleanup_resources)

# Load configuration
def load_secrets():
    try:
        secrets = toml.load(Path(".streamlit/secrets.toml"))
        return secrets["GEMINI_API_KEY"]
    except:
        st.error("Please set up your .streamlit/secrets.toml with GEMINI_API_KEY")
        return None

# Initialize Gemini
def init_gemini():
    api_key = load_secrets()
    if api_key:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.0-flash')
        return model
    return None

# Load transcript
def load_transcript():
    transcript_path = Path("data/sample_audio_transcription.txt")
    return transcript_path.read_text() if transcript_path.exists() else ""

# Load assistant prompt
def load_assistant_prompt():
    assistant_prompt_path = Path("data/assistant_prompt.txt")
    return assistant_prompt_path.read_text() if assistant_prompt_path.exists() else ""

def process_uploaded_file(uploaded_file):
    if uploaded_file is None:
        return ""
    
    if uploaded_file.type == "application/pdf":
        pdf_reader = PyPDF2.PdfReader(io.BytesIO(uploaded_file.getvalue()))
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text() + "\n"
        return text
    else:
        return uploaded_file.getvalue().decode("utf-8")

def process_url(url):
    if not url:
        return ""
    try:
        response = requests.get(url)
        return response.text()
    except:
        st.error("Failed to fetch content from URL")
        return ""

def analyze_conversation(model, transcript, assistant_prompt, user_input, additional_context=""):
    prompt = f"""
    Assistant Prompt:
    {assistant_prompt}
    
    Conversation Transcript:
    {transcript}
    
    Additional Context:
    {additional_context}
    
    User Context/Question:
    {user_input}
    
    Please analyze this sales call and provide insights based on the user's question and additional context provided.
    """
    
    response = model.generate_content(prompt)
    return response.text

class TranscriptionManager:
    def __init__(self, model_size="base", sample_rate=16000):
        try:
            self.model = WhisperModel(model_size, device="cpu", compute_type="int8")
            self.audio_queue = queue.Queue()
            self.text_queue = queue.Queue()
            self.running = False
            self.sample_rate = sample_rate
            self.buffer = np.array([], dtype=np.float32)
            self.min_audio_length = 0.5
            self.stream = None
            self.process_thread = None
        except Exception as e:
            st.error(f"Failed to initialize transcription: {str(e)}")
            raise

    def audio_callback(self, indata, frames, time, status):
        if status:
            print(f"Status: {status}")
        audio_chunk = np.squeeze(indata)
        if audio_chunk.dtype == np.float32:
            audio_chunk = (audio_chunk * 32768).astype(np.int16)
        if np.abs(audio_chunk).mean() > 10:  # Basic noise gate
            self.audio_queue.put(audio_chunk)
    
    def start(self):
        if self.running:
            return
            
        self.running = True
        try:
            self.stream = sd.InputStream(
                channels=1,
                samplerate=self.sample_rate,
                callback=self.audio_callback,
                dtype=np.float32
            )
            self.stream.start()
            self.process_thread = threading.Thread(target=self._process_audio)
            self.process_thread.daemon = True
            self.process_thread.start()
        except Exception as e:
            self.running = False
            st.error(f"Failed to start audio stream: {str(e)}")
            raise

    def stop(self):
        self.running = False
        
        if self.stream:
            with contextlib.suppress(Exception):
                self.stream.stop()
                self.stream.close()
                self.stream = None
        
        if self.process_thread:
            with contextlib.suppress(Exception):
                self.process_thread.join(timeout=2.0)
                self.process_thread = None
        
        # Clear queues
        while not self.audio_queue.empty():
            self.audio_queue.get()
        while not self.text_queue.empty():
            self.text_queue.get()

    def _process_audio(self):
        while self.running:
            chunks = []
            while not self.audio_queue.empty():
                chunk = self.audio_queue.get()
                chunks.append(chunk)
            
            if chunks:
                audio_data = np.concatenate(chunks)
                audio_data = audio_data.astype(np.float32) / 32768.0
                self.buffer = np.append(self.buffer, audio_data)
            
            buffer_duration = len(self.buffer) / self.sample_rate
            if buffer_duration >= self.min_audio_length:
                try:
                    segments, _ = self.model.transcribe(
                        self.buffer,
                        beam_size=5,
                        language="en",
                        vad_filter=True,
                        vad_parameters=dict(min_silence_duration_ms=500)
                    )
                    
                    text = ""
                    for segment in segments:
                        text += segment.text
                    
                    if text.strip():
                        self.text_queue.put(text.strip())
                    
                    keep_duration = 0.5
                    if buffer_duration > keep_duration:
                        self.buffer = self.buffer[-int(keep_duration * self.sample_rate):]
                    
                except Exception as e:
                    print(f"Transcription error: {e}")
            
            threading.Event().wait(0.1)
    
    def get_transcription(self):
        if not self.text_queue.empty():
            return self.text_queue.get()
        return None

    def __del__(self):
        self.stop()

def main():
    # Initialize asyncio for the main thread
    try:
        asyncio.get_event_loop()
    except RuntimeError:
        asyncio.set_event_loop(asyncio.new_event_loop())
    
    try:
        st.set_page_config(
            page_title="Sales Call Analysis Dashboard",
            page_icon="📞",
            layout="wide",
            initial_sidebar_state="expanded"
        )
        
        st.markdown("# 📞 Sales Call Analysis Dashboard")
        
        # Initialize Gemini
        model = init_gemini()
        if not model:
            return
        
        assistant_prompt = load_assistant_prompt()
        
        # Initialize transcription manager in session state
        if 'transcription_manager' not in st.session_state:
            try:
                st.session_state.transcription_manager = TranscriptionManager()
                st.session_state.live_transcript = ""
            except Exception as e:
                st.error(f"Failed to initialize audio system: {str(e)}")
                return
        
        # Sidebar
        with st.sidebar:
            st.markdown("### 🎯 Analysis Parameters")
            
            user_input = st.text_area(
                "What would you like to analyze?",
                "Analyze and list all the improvements in this sales call.",
                help="Enter your specific analysis request here"
            )
            with st.expander("Data connection"):
                if st.button("Connect with CRM", use_container_width=True):
                    st.info("Work in Progress")
            
            st.markdown("### 📄 Additional Context")
            uploaded_file = st.file_uploader(
                "Upload document",
                type=["txt", "pdf"],
                help="Upload additional context documents"
            )
            url_input = st.text_input(
                "Or enter a URL",
                help="Provide a URL for additional context"
            )
        
        additional_context = ""
        if uploaded_file:
            additional_context = process_uploaded_file(uploaded_file)
        elif url_input:
            additional_context = process_url(url_input)

        # Create tabs for input methods
        input_tab1, input_tab2 = st.tabs(["🎙️ Live Recording", "📝 Existing Transcript"])
        
        with input_tab1:
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("Start Recording", key="start_record"):
                    st.session_state.transcription_manager.start()
                    st.session_state.recording = True
            
            with col2:
                if st.button("Stop Recording", key="stop_record"):
                    if hasattr(st.session_state, 'recording') and st.session_state.recording:
                        st.session_state.transcription_manager.stop()
                        st.session_state.recording = False
            
            # Real-time transcription display
            if hasattr(st.session_state, 'recording') and st.session_state.recording:
                transcript_placeholder = st.empty()
                
                # Get new transcription
                new_text = st.session_state.transcription_manager.get_transcription()
                if new_text:
                    st.session_state.live_transcript += " " + new_text
                
                # Display current transcript
                transcript_placeholder.text_area(
                    "Live Transcript",
                    st.session_state.live_transcript,
                    height=200
                )
                
                if st.button("🔍 Analyze Live Recording", use_container_width=True, type="primary"):
                    with st.spinner("🔄 Analyzing conversation..."):
                        analysis = analyze_conversation(
                            model,
                            st.session_state.live_transcript,
                            assistant_prompt,
                            user_input,
                            additional_context
                        )
                        st.success("Analysis Complete!")
                        st.markdown("### 🎯 Analysis Results")
                        st.write(analysis)
        
        with input_tab2:
            st.info("Using pre-loaded transcripts")
            transcript = load_transcript()
            
            if transcript and st.button("🔍 Analyze Call", use_container_width=True, type="primary"):
                with st.spinner("🔄 Analyzing conversation..."):
                    analysis = analyze_conversation(model, transcript, assistant_prompt, user_input, additional_context)
                    st.success("Analysis Complete!")
                    st.markdown("### 🎯 Analysis Results")
                    st.write(analysis)

        # Display Tabs
        
        with st.expander("📝 Transcript"):
            st.text_area("Call Transcript", transcript, height=400, disabled=True)
        
        with st.expander("🤖 Assistant Prompt"):
            st.text_area("AI Assistant Prompt", assistant_prompt, height=400, disabled=True)
        
    except Exception as e:
        st.error(f"An error occurred: {str(e)}")
        cleanup_resources()
    finally:
        # Ensure cleanup happens when the app exits
        cleanup_resources()

if __name__ == "__main__":
    with contextlib.suppress(KeyboardInterrupt):
        main()