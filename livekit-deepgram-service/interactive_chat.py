"""
Interactive Voice Chat - Talk to your Loan Recovery Agent using your voice!

This script allows you to have a voice conversation with the agent using:
- Your microphone for input (captured via browser/simple audio)
- Deepgram STT for speech-to-text
- ADK agent for responses
- Deepgram TTS for voice output
- Audio playback for responses

Requirements:
- pyaudio (for audio capture/playback)
- Or use browser-based solution
"""
import asyncio
import logging
import os
from voice_pipeline import VoicePipeline
import wave
import tempfile

# Try to import audio libraries
try:
    import pyaudio
    AUDIO_AVAILABLE = True
except ImportError:
    AUDIO_AVAILABLE = False
    print("⚠️  PyAudio not installed. Install with: pip install pyaudio")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("interactive-voice-chat")


class VoiceChat:
    """Interactive voice chat with the agent"""
    
    def __init__(self):
        self.pipeline = VoicePipeline(
            adk_api_url="http://localhost:8000",
            app_name="loan_recovery_agent",
            user_id="voice_user",
            session_id="voice_session_001",
        )
        self.audio = None
        if AUDIO_AVAILABLE:
            self.audio = pyaudio.PyAudio()
    
    def play_audio(self, audio_data: bytes, sample_rate: int = 24000):
        """Play audio data through speakers"""
        if not AUDIO_AVAILABLE:
            logger.warning("PyAudio not available, cannot play audio")
            return
        
        try:
            # Save to temporary WAV file
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_wav:
                temp_filename = temp_wav.name
                
                # Write WAV file
                with wave.open(temp_filename, 'wb') as wav_file:
                    wav_file.setnchannels(1)  # Mono
                    wav_file.setsampwidth(2)  # 16-bit
                    wav_file.setframerate(sample_rate)
                    wav_file.writeframes(audio_data)
            
            # Play the WAV file
            with wave.open(temp_filename, 'rb') as wav_file:
                stream = self.audio.open(
                    format=self.audio.get_format_from_width(wav_file.getsampwidth()),
                    channels=wav_file.getnchannels(),
                    rate=wav_file.getframerate(),
                    output=True
                )
                
                data = wav_file.readframes(1024)
                while data:
                    stream.write(data)
                    data = wav_file.readframes(1024)
                
                stream.stop_stream()
                stream.close()
            
            # Clean up temp file
            os.unlink(temp_filename)
            
        except Exception as e:
            logger.error(f"Error playing audio: {e}")
    
    async def text_conversation(self):
        """Text-based conversation (fallback if no audio)"""
        print("\n" + "="*60)
        print("💬 TEXT CHAT MODE - Type your messages")
        print("="*60)
        print("\nType 'quit' or 'exit' to end the conversation\n")
        
        while True:
            try:
                user_input = input("You: ").strip()
                
                if user_input.lower() in ['quit', 'exit', 'q']:
                    print("\n👋 Goodbye!")
                    break
                
                if not user_input:
                    continue
                
                print(f"\n🤔 Agent is thinking...")
                
                # Send to agent and get response
                full_response = ""
                async for agent_text in self.pipeline.send_to_adk_agent(user_input):
                    full_response += agent_text
                
                if full_response:
                    print(f"\n🤖 Agent: {full_response}\n")
                    
                    # Generate and play audio response
                    print("🔊 Generating voice response...")
                    audio_data = await self.pipeline.tts_service.synthesize_to_audio(full_response)
                    
                    if AUDIO_AVAILABLE:
                        print("▶️  Playing audio...")
                        self.play_audio(audio_data)
                    else:
                        print("⚠️  Audio playback not available (install pyaudio)")
                    
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
        if self.audio:
            self.audio.terminate()


async def main():
    """Main entry point"""
    print("\n" + "="*60)
    print("🎙️  VOICE CHAT WITH LOAN RECOVERY AGENT")
    print("="*60)
    print("\n📋 Configuration:")
    print("   - ADK Server: http://localhost:8000")
    print("   - Agent: loan_recovery_agent")
    print("   - STT: Deepgram (nova-2-general)")
    print("   - TTS: Deepgram (aura-asteria-en)")
    print("\n⚠️  Make sure ADK api_server is running!")
    print("   Run in another terminal: cd adk-streaming-ws && adk api_server")
    
    chat = VoiceChat()
    
    try:
        # For now, use text input with voice output
        # TODO: Add microphone input support
        await chat.text_conversation()
    finally:
        await chat.cleanup()


if __name__ == "__main__":
    asyncio.run(main())

