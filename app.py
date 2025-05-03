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

# Load data files
def load_data():
    transcript_path = Path("data/sample_audio_transcription.txt")
    assistant_prompt_path = Path("data/assistant_prompt.txt")
    
    transcript = transcript_path.read_text() if transcript_path.exists() else ""
    assistant_prompt = assistant_prompt_path.read_text() if assistant_prompt_path.exists() else ""
    return transcript, assistant_prompt

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
        return response.text
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
    st.title("Sales Call Analysis Dashboard")
    
    # models = list_models()
    # for model in models:
    #     st.write(model.name)

    # Initialize Gemini
    model = init_gemini()
    if not model:
        return
    
    # Load data
    transcript, assistant_prompt = load_data()
    
    # Sidebar for user input
    st.sidebar.header("Analysis Parameters")
    user_input = st.sidebar.text_area(
        "What would you like to analyze about this call?",
        "Analyze the key moments and success factors in this sales call."
    )
    
    uploaded_file = st.sidebar.file_uploader("Upload additional document for context", type=["txt", "pdf"])
    url_input = st.sidebar.text_input("Or enter a URL for additional context")
    
    # Process additional context
    additional_context = ""
    if uploaded_file:
        additional_context = process_uploaded_file(uploaded_file)
    elif url_input:
        additional_context = process_url(url_input)
    
    # Main content
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("Call Transcript")
        st.text_area("Transcript", transcript, height=400, disabled=True)
    
    with col2:
        st.subheader("Assistant Prompt")
        st.text_area("Prompt", assistant_prompt, height=400, disabled=True)
    
    # Analysis button
    if st.button("Analyze Call"):
        with st.spinner("Analyzing conversation..."):
            analysis = analyze_conversation(model, transcript, assistant_prompt, user_input, additional_context)
            
            st.subheader("Analysis Results")
            st.write(analysis)

if __name__ == "__main__":
    st.set_page_config(
        page_title="Sales Call Assistant App",
        page_icon="🧊",
        layout="wide",
        initial_sidebar_state="expanded",
        menu_items={
            'Get Help': 'https://www.extremelycoolapp.com/help',
            'About': "# This is a header. This is an *extremely* cool app!"
        }
    )
    main()