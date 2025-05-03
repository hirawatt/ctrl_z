# Deepgram Live Audio Transcription App

This Streamlit application uses Deepgram's API to transcribe audio in real-time. It captures audio from your microphone, sends it to Deepgram's streaming API, and displays the transcription results instantly.

## Features

- Real-time audio transcription
- Support for multiple languages
- Configurable audio settings
- Smart formatting option
- Choice of Deepgram AI models
- Complete transcript history

## Setup Instructions

### 1. Install Required Packages

```bash
pip install -r requirements.txt
```

### 2. Get a Deepgram API Key

Sign up at [console.deepgram.com](https://console.deepgram.com/) to obtain your API key.

### 3. Run the Application

```bash
streamlit run app.py
```

## How to Use

1. Enter your Deepgram API key in the sidebar
2. Configure your audio and model settings
3. Click 'Start Recording' to begin transcription
4. Speak into your microphone
5. Click 'Stop Recording' when finished
6. View your transcription history below

## Notes

- PyAudio may require additional system dependencies depending on your operating system:
  - **Windows**: Should work with pip install
  - **macOS**: `brew install portaudio` before pip install
  - **Linux**: `sudo apt-get install python3-pyaudio` or `sudo apt-get install portaudio19-dev` before pip install

- The app requires microphone access in your browser.

## Troubleshooting

If you encounter issues with the audio recording:

1. Make sure your microphone is properly connected and has permission in your browser
2. Try adjusting the sample rate in the sidebar
3. Ensure you've installed all dependencies correctly

## Advanced Options

The sidebar provides options to customize:

- **Sample Rate**: Choose between 16kHz, 44.1kHz, and 48kHz
- **Language**: Select from English, Spanish, French, German, Japanese, Korean, or Chinese
- **Smart Formatting**: Formats numbers, dates, and other entities more readably
- **Model**: Choose between Nova-2 (fastest), Nova (balanced), or Enhanced (most accurate)
- **Interim Results**: Shows partial transcripts as you speak

## How It Works

The application uses:

1. **Streamlit** for the web interface
2. **PyAudio** to capture audio from your microphone
3. **Deepgram SDK** to stream audio and receive transcriptions
4. **Threading** to handle audio processing without blocking the UI

The audio is processed in chunks and sent to Deepgram in real-time, with results displayed as they become available.