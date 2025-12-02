"""
Full Voice-to-Voice Chat - Talk using your microphone!

Flow:
1. User speaks → Microphone captures audio
2. Audio → Deepgram STT → Text
3. Text → ADK Agent → Response text
4. Response text → Deepgram TTS → Audio
5. Audio → Speakers (play back)
"""
import asyncio
import logging
import os
import wave
import tempfile
from voice_pipeline import VoicePipeline
import sounddevice as sd
import numpy as np
from collections import deque

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("voice-to-voice-chat")


class VoiceToVoiceChat:
    """Full voice-to-voice conversation with the agent"""
    
    def __init__(self):
        self.pipeline = VoicePipeline(
            adk_api_url="http://localhost:8000",
            app_name="loan_recovery_agent",
            user_id="voice_user",
            session_id="voice_session_001",
        )
        
        # Audio settings
        self.sample_rate = 16000  # 16kHz for STT
        self.channels = 1  # Mono
        self.recording = False
        self.audio_buffer = deque(maxlen=100)  # Keep last 100 chunks
        
    def play_audio(self, audio_data: bytes, sample_rate: int = 24000):
        """Play audio through speakers"""
        try:
            # Convert bytes to numpy array
            audio_array = np.frombuffer(audio_data, dtype=np.int16)
            
            # Normalize to float32
            audio_float = audio_array.astype(np.float32) / 32768.0
            
            # Play audio
            sd.play(audio_float, samplerate=sample_rate)
            sd.wait()  # Wait for playback to finish
            
        except Exception as e:
            logger.error(f"Error playing audio: {e}")
    
    def record_audio_chunk(self, duration_seconds: float = 5.0) -> bytes:
        """Record audio from microphone for specified duration"""
        print(f"\n🎤 Recording for {duration_seconds} seconds...")
        print("   (Speak now!)")
        
        try:
            # Record audio
            audio_data = sd.rec(
                int(duration_seconds * self.sample_rate),
                samplerate=self.sample_rate,
                channels=self.channels,
                dtype='int16'
            )
            sd.wait()  # Wait for recording to finish
            
            print("✅ Recording complete!")
            
            # Convert to bytes
            return audio_data.tobytes()
            
        except Exception as e:
            logger.error(f"Error recording audio: {e}")
            return b""
    
    async def save_audio_to_wav(self, audio_data: bytes, filename: str):
        """Save audio data to WAV file"""
        with wave.open(filename, 'wb') as wav_file:
            wav_file.setnchannels(self.channels)
            wav_file.setsampwidth(2)  # 16-bit
            wav_file.setframerate(self.sample_rate)
            wav_file.writeframes(audio_data)
    
    async def transcribe_audio(self, audio_data: bytes) -> str:
        """Transcribe audio using Deepgram STT"""
        try:
            # Save to temporary WAV file
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_wav:
                temp_filename = temp_wav.name
                await self.save_audio_to_wav(audio_data, temp_filename)
            
            # For now, use Deepgram's REST API directly
            # The livekit plugin expects a stream, so we'll use a simpler approach
            import aiohttp
            
            deepgram_api_key = os.getenv('DEEPGRAM_API_KEY')
            if not deepgram_api_key:
                print("⚠️  DEEPGRAM_API_KEY not set! Using fallback text input.")
                user_text = input("Type what you said: ")
                return user_text
            
            url = "https://api.deepgram.com/v1/listen"
            headers = {
                "Authorization": f"Token {deepgram_api_key}",
                "Content-Type": "audio/wav"
            }
            
            params = {
                "model": "nova-2-general",
                "language": "en-US",
                "smart_format": "true"
            }
            
            async with aiohttp.ClientSession() as session:
                with open(temp_filename, 'rb') as audio_file:
                    async with session.post(url, headers=headers, params=params, data=audio_file) as response:
                        if response.status == 200:
                            result = await response.json()
                            transcript = result['results']['channels'][0]['alternatives'][0]['transcript']
                            
                            # Clean up temp file
                            os.unlink(temp_filename)
                            
                            return transcript
                        else:
                            logger.error(f"Deepgram API error: {response.status}")
                            os.unlink(temp_filename)
                            return ""
            
        except Exception as e:
            logger.error(f"Error transcribing audio: {e}")
            return ""
    
    async def voice_conversation(self):
        """Main voice conversation loop"""
        print("\n" + "="*60)
        print("🎙️  VOICE-TO-VOICE CHAT MODE")
        print("="*60)
        print("\n⚠️  Make sure you have set DEEPGRAM_API_KEY in your environment!")
        print("\nCommands:")
        print("  - Press ENTER to start recording")
        print("  - Type 'quit' or 'exit' to end")
        print("\n" + "="*60 + "\n")
        
        while True:
            try:
                # Wait for user to press Enter
                user_input = input("Press ENTER to speak (or 'quit' to exit): ").strip()
                
                if user_input.lower() in ['quit', 'exit', 'q']:
                    print("\n👋 Goodbye!")
                    break
                
                # Record audio from microphone
                audio_data = self.record_audio_chunk(duration_seconds=5.0)
                
                if not audio_data:
                    print("❌ No audio recorded, try again\n")
                    continue
                
                # Transcribe audio
                print("\n🎯 Transcribing your speech...")
                user_text = await self.transcribe_audio(audio_data)
                
                if not user_text:
                    print("❌ Could not transcribe audio, try again\n")
                    continue
                
                print(f"\n📝 You said: \"{user_text}\"")
                
                # Send to agent
                print(f"🤔 Agent is thinking...")
                
                full_response = ""
                async for agent_text in self.pipeline.send_to_adk_agent(user_text):
                    full_response += agent_text
                
                if full_response:
                    print(f"\n🤖 Agent: {full_response}\n")
                    
                    # Generate voice response
                    print("🔊 Generating voice response...")
                    audio_data = await self.pipeline.tts_service.synthesize_to_audio(full_response)
                    
                    print("▶️  Playing response...")
                    self.play_audio(audio_data)
                    
                    print("\n" + "-"*60 + "\n")
                else:
                    print("\n⚠️  No response from agent\n")
                    
            except KeyboardInterrupt:
                print("\n\n👋 Goodbye!")
                break
            except Exception as e:
                logger.error(f"Error in conversation: {e}")
                print(f"\n❌ Error: {e}\n")
    
    async def cleanup(self):
        """Clean up resources"""
        await self.pipeline.close()


async def main():
    """Main entry point"""
    print("\n" + "="*60)
    print("🎙️  VOICE-TO-VOICE CHAT WITH LOAN RECOVERY AGENT")
    print("="*60)
    print("\n📋 Configuration:")
    print("   - ADK Server: http://localhost:8000")
    print("   - Agent: loan_recovery_agent")
    print("   - STT: Deepgram (nova-2-general)")
    print("   - TTS: Deepgram (aura-asteria-en)")
    print("\n⚠️  Requirements:")
    print("   1. ADK api_server must be running")
    print("   2. DEEPGRAM_API_KEY must be set in environment")
    print("   3. Microphone access enabled")
    
    # Check for Deepgram API key
    if not os.getenv('DEEPGRAM_API_KEY'):
        print("\n❌ ERROR: DEEPGRAM_API_KEY not found!")
        print("   Set it with: export DEEPGRAM_API_KEY='your_key_here'")
        print("   Or create a .env file with: DEEPGRAM_API_KEY=your_key_here")
        return
    
    chat = VoiceToVoiceChat()
    
    try:
        await chat.voice_conversation()
    finally:
        await chat.cleanup()


if __name__ == "__main__":
    asyncio.run(main())

