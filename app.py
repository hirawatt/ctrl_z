import streamlit as st
from google.generativeai import GenerativeModel, list_models
import google.generativeai as genai
from pathlib import Path
import toml
import requests
import PyPDF2
import io

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

def main():
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
        audio_value = st.audio_input("Record conversation")
        if audio_value:
            st.info("Live Conversation Analysis in process")
            transcript = audio_value.read()
            if st.button("🔍 Analyze Live Recording", use_container_width=True, type="primary"):
                with st.spinner("🔄 Analyzing conversation..."):
                    analysis = analyze_conversation(model, transcript, assistant_prompt, user_input, additional_context)
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
    

if __name__ == "__main__":
    main()