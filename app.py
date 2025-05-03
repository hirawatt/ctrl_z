import streamlit as st
from google.generativeai import GenerativeModel, list_models
import google.generativeai as genai
from pathlib import Path
import toml

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

def analyze_conversation(model, transcript, assistant_prompt, user_input):
    prompt = f"""
    Assistant Prompt:
    {assistant_prompt}
    
    Conversation Transcript:
    {transcript}
    
    User Context/Question:
    {user_input}
    
    Please analyze this sales call and provide insights based on the user's question.
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
            analysis = analyze_conversation(model, transcript, assistant_prompt, user_input)
            
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