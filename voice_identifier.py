#!/usr/bin/env python3
"""
Simple Voice Language Identifier AI
Single file - just identify language and show transcription
"""

import json
import re
import ssl
import os
import asyncio
import tempfile
from typing import Dict, Any
# Load environment variables
from dotenv import load_dotenv
load_dotenv()
import speech_recognition as sr
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from flask import Flask, render_template, request, jsonify

# Disable SSL warnings
ssl._create_default_https_context = ssl._create_unverified_context

# Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

class SimpleVoiceIdentifier:
    """Simple voice language identifier"""
    
    def __init__(self):
        self.llm = None
        self.recognizer = None
    

        
    async def initialize(self):
        """Initialize the system"""
        if not OPENAI_API_KEY or OPENAI_API_KEY == "your_openai_api_key_here":
            print("⚠️  OPENAI_API_KEY not set. Please create a .env file with your API key.")
            print("   Get your key from: https://platform.openai.com/api-keys")
            print("   Add to .env file: OPENAI_API_KEY=your_actual_key_here")
            raise ValueError("OPENAI_API_KEY not set")
        
        self.llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.1, api_key=OPENAI_API_KEY)
        self.recognizer = sr.Recognizer()
        self.recognizer.energy_threshold = 4000
        
    async def identify_language(self, audio_file_path: str) -> Dict[str, Any]:
        """Identify language from audio file"""
        try:
            # Transcribe audio
            with sr.AudioFile(audio_file_path) as source:
                audio = self.recognizer.record(source)
            
            # Dynamic speech recognition - no language hints
            transcription = None
            
            try:
                transcription = self.recognizer.recognize_google(audio)
                print("🎯 Used dynamic language recognition")
                print(f"📝 Transcription: {transcription}")
            except sr.UnknownValueError:
                print(" Speech recognition failed: Could not understand audio")
                return {"error": "Could not understand audio. Please speak clearly."}
            except sr.RequestError as e:
                print(f" Speech recognition failed: Google service error - {e}")
                return {"error": "Speech recognition service error. Please try again."}
            except Exception as e:
                print(f" Speech recognition failed: {e}")
                return {"error": f"Speech recognition failed: {e}"}
            
            # Simple AI language detection
            system_prompt = """You are a language identification expert. Your role is to identify the language of any given text.

Return a JSON response with:
{
    "detected_language": "language_code",
    "language_name": "Language Name"
}

Text: "{transcription}" """

            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=f"Text to analyze: {transcription}")
            ]
            
            response = await self.llm.ainvoke(messages)
            
            # Parse AI response
            content = response.content
            print(f"🤖 AI Analysis: {content}")
            
          
            
            # Simple JSON parsing
            try:
                json_match = re.search(r'\{.*\}', content, re.DOTALL)
                if json_match:
                    result_data = json.loads(json_match.group())
                    detected_language = result_data.get("detected_language", "unknown")
                    language_name = result_data.get("language_name", "Unknown")
                    
                    print(f"🎯 AI Detected: {language_name} ({detected_language})")
                else:
                    detected_language = "unknown"
                    language_name = "Unknown"
                    
            except Exception as e:
                detected_language = "unknown"
                language_name = "Unknown"
            

            
            return {
                "detected_language": detected_language,
                "language_name": language_name,
                "transcription": transcription
            }
            
        except Exception as e:
            return {"error": str(e)}
    
    async def record_and_identify(self, duration: int = 10) -> Dict[str, Any]:
        """Record audio and identify language"""
        try:
            print("🎙️ Starting audio recording...")
            
            # Record audio
            mic = sr.Microphone()
            with mic as source:
                print("🔊 Adjusting for ambient noise...")
                self.recognizer.adjust_for_ambient_noise(source, duration=1)
                print("🎤 Listening for speech...")
                audio = self.recognizer.listen(source, timeout=duration, phrase_time_limit=duration)
            
            print("✅ Audio recording completed")
            
            # Save to temp file
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
                temp_file.write(audio.get_wav_data())
                temp_file_path = temp_file.name
                print(f"💾 Saved audio to: {temp_file_path}")
            
            # Identify language
            result = await self.identify_language(temp_file_path)
            
            # Clean up
            os.unlink(temp_file_path)
            
            return result
            
        except sr.WaitTimeoutError:
            print("⏰ Timeout: No speech detected")
            return {"error": "No speech detected. Please speak when recording."}
        except Exception as e:
            print(f" Recording error: {e}")
            return {"error": f"Recording failed: {str(e)}"}

# Flask app
app = Flask(__name__)
identifier = None



@app.route('/')
def index():
    return render_template('index.html')

@app.route('/record', methods=['POST'])
def record_audio():
    try:
        duration = request.json.get('duration', 10)
        
        if identifier is None:
            return jsonify({'error': 'Not initialized'}), 500
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(identifier.record_and_identify(duration))
        loop.close()
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

async def initialize():
    global identifier
    identifier = SimpleVoiceIdentifier()
    await identifier.initialize()

if __name__ == '__main__':
    print("🎤 Simple Voice Language Identifier")
    print("Initializing...")
    
    # Initialize in background
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(initialize())
    loop.close()
    
    print("✅ Ready! Open http://192.168.1.6:5000")
    app.run(debug=True, host='192.168.1.6', port=5000) 