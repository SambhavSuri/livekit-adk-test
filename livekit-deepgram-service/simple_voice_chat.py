"""
Simple Streaming Voice Chat using LiveKit Deepgram Plugins

Direct integration:
1. Microphone → Deepgram STT → Text
2. Text → ADK Agent → Response
3. Response → Deepgram TTS → Audio playback

With detailed performance logging
"""
import asyncio
import logging
import os
import sounddevice as sd
import numpy as np
from voice_pipeline import VoicePipeline
import time
from datetime import datetime

# Setup logging to both console and file
log_filename = f"voice_chat_performance_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_filename),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("simple-voice-chat")

# Performance logger (detailed timing)
perf_logger = logging.getLogger("performance")
perf_logger.setLevel(logging.INFO)


class SimpleVoiceChat:
    """Simplified voice chat using LiveKit Deepgram"""
    
    def __init__(self):
        self.pipeline = VoicePipeline(
            adk_api_url="http://localhost:8000",
            app_name="loan_recovery_agent",
            user_id="voice_user",
            session_id="voice_session",
        )
        self.sample_rate = 16000
        self.conversation_count = 0
        
        # Log session start
        perf_logger.info("="*80)
        perf_logger.info("NEW VOICE CHAT SESSION STARTED")
        perf_logger.info(f"Log file: {log_filename}")
        perf_logger.info("="*80)
        
    def record_audio(self, duration=5):
        """Record audio from microphone"""
        print(f"\n🎤 Recording for {duration} seconds... Speak now!")
        
        start_time = time.time()
        
        recording = sd.rec(
            int(duration * self.sample_rate),
            samplerate=self.sample_rate,
            channels=1,
            dtype='int16'
        )
        sd.wait()
        
        recording_time = time.time() - start_time
        
        print("✅ Recording complete!")
        perf_logger.info(f"[RECORDING] Duration: {recording_time:.2f}s")
        
        return recording
    
    def play_audio(self, audio_bytes, sample_rate=24000):
        """Play audio through speakers"""
        try:
            audio_array = np.frombuffer(audio_bytes, dtype=np.int16)
            audio_float = audio_array.astype(np.float32) / 32768.0
            
            sd.play(audio_float, samplerate=sample_rate)
            sd.wait()
        except Exception as e:
            logger.error(f"Error playing audio: {e}")
    
    async def transcribe_with_deepgram_api(self, audio_data):
        """Transcribe using Deepgram REST API"""
        import aiohttp
        import wave
        import tempfile
        
        stt_start = time.time()
        
        deepgram_key = os.getenv('DEEPGRAM_API_KEY')
        if not deepgram_key:
            print("⚠️  DEEPGRAM_API_KEY not set!")
            return input("Type what you said: ")
        
        # Save to WAV file
        wav_prep_start = time.time()
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
            wav_path = f.name
            
        with wave.open(wav_path, 'wb') as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(self.sample_rate)
            wav_file.writeframes(audio_data.tobytes())
        
        wav_prep_time = time.time() - wav_prep_start
        perf_logger.info(f"[STT] WAV file preparation: {wav_prep_time:.3f}s")
        
        # Send to Deepgram
        url = "https://api.deepgram.com/v1/listen"
        headers = {
            "Authorization": f"Token {deepgram_key}",
            "Content-Type": "audio/wav"
        }
        params = {
            "model": "nova-2-general",
            "smart_format": "true"
        }
        
        try:
            api_start = time.time()
            async with aiohttp.ClientSession() as session:
                with open(wav_path, 'rb') as audio:
                    async with session.post(url, headers=headers, params=params, data=audio) as resp:
                        if resp.status == 200:
                            result = await resp.json()
                            transcript = result['results']['channels'][0]['alternatives'][0]['transcript']
                            
                            api_time = time.time() - api_start
                            total_stt_time = time.time() - stt_start
                            
                            perf_logger.info(f"[STT] Deepgram API call: {api_time:.3f}s")
                            perf_logger.info(f"[STT] TOTAL STT TIME: {total_stt_time:.3f}s")
                            perf_logger.info(f"[STT] Transcript: \"{transcript}\"")
                            
                            os.unlink(wav_path)
                            return transcript
                        else:
                            logger.error(f"Deepgram error: {resp.status}")
                            os.unlink(wav_path)
                            return ""
        except Exception as e:
            logger.error(f"Error transcribing: {e}")
            if os.path.exists(wav_path):
                os.unlink(wav_path)
            return ""
    
    async def conversation_loop(self):
        """Main conversation loop"""
        print("\n" + "="*60)
        print("🎙️  VOICE CHAT WITH LOAN RECOVERY AGENT")
        print("="*60)
        print("\n💡 Instructions:")
        print("   1. Press ENTER to record (5 seconds)")
        print("   2. Speak your message")
        print("   3. Agent responds with voice")
        print("   4. Type 'quit' to exit")
        print(f"\n📊 Performance log: {log_filename}")
        print("\n" + "="*60 + "\n")
        
        while True:
            try:
                user_input = input("Press ENTER to record (or 'quit'): ").strip()
                
                if user_input.lower() in ['quit', 'exit', 'q']:
                    print("\n👋 Goodbye!")
                    break
                
                self.conversation_count += 1
                turn_start = time.time()
                
                perf_logger.info("")
                perf_logger.info("="*80)
                perf_logger.info(f"CONVERSATION TURN #{self.conversation_count}")
                perf_logger.info("="*80)
                
                # Record audio
                audio_data = self.record_audio(duration=5)
                
                # Transcribe
                print("\n🎯 Transcribing your speech...")
                transcript = await self.transcribe_with_deepgram_api(audio_data)
                
                if not transcript:
                    print("❌ Could not transcribe. Try again.\n")
                    continue
                
                print(f"\n📝 You said: \"{transcript}\"")
                
                # Send to agent
                print("\n🤔 Agent is thinking...")
                
                adk_start = time.time()
                full_response = ""
                async for text in self.pipeline.send_to_adk_agent(transcript):
                    full_response += text
                
                adk_time = time.time() - adk_start
                perf_logger.info(f"[ADK AGENT] Processing time: {adk_time:.3f}s")
                perf_logger.info(f"[ADK AGENT] Response: \"{full_response}\"")
                
                if full_response:
                    print(f"\n🤖 Agent: {full_response}")
                    
                    # Generate TTS
                    print("\n🔊 Generating voice response...")
                    tts_start = time.time()
                    audio_bytes = await self.pipeline.tts_service.synthesize_to_audio(full_response)
                    tts_time = time.time() - tts_start
                    
                    perf_logger.info(f"[TTS] Audio generation time: {tts_time:.3f}s")
                    perf_logger.info(f"[TTS] Audio size: {len(audio_bytes)} bytes")
                    
                    print("▶️  Playing response...")
                    playback_start = time.time()
                    self.play_audio(audio_bytes, sample_rate=24000)
                    playback_time = time.time() - playback_start
                    
                    perf_logger.info(f"[PLAYBACK] Duration: {playback_time:.2f}s")
                    
                    total_turn_time = time.time() - turn_start
                    perf_logger.info("")
                    perf_logger.info(f"[SUMMARY] Total turn time: {total_turn_time:.2f}s")
                    perf_logger.info(f"  - STT: ~{transcript and 'completed' or 'N/A'}")
                    perf_logger.info(f"  - ADK Agent: {adk_time:.2f}s")
                    perf_logger.info(f"  - TTS: {tts_time:.2f}s")
                    perf_logger.info(f"  - Playback: {playback_time:.2f}s")
                    
                    print("\n" + "-"*60 + "\n")
                else:
                    print("\n⚠️  No response from agent\n")
                    
            except KeyboardInterrupt:
                print("\n\n👋 Goodbye!")
                break
            except Exception as e:
                logger.error(f"Error: {e}")
                print(f"\n❌ Error: {e}\n")
    
    async def cleanup(self):
        """Cleanup resources"""
        perf_logger.info("")
        perf_logger.info("="*80)
        perf_logger.info(f"SESSION ENDED - Total conversations: {self.conversation_count}")
        perf_logger.info(f"Log saved to: {log_filename}")
        perf_logger.info("="*80)
        
        await self.pipeline.close()
        
        print(f"\n📊 Performance log saved to: {log_filename}")


async def main():
    """Main entry point"""
    print("\n" + "="*60)
    print("🎙️  SIMPLE VOICE CHAT")
    print("="*60)
    print("\n📋 Configuration:")
    print("   - ADK Server: http://localhost:8000")
    print("   - Agent: loan_recovery_agent")
    print("   - STT: Deepgram API")
    print("   - TTS: Deepgram (via LiveKit)")
    print("\n⚠️  Requirements:")
    print("   1. ADK api_server running")
    print("   2. DEEPGRAM_API_KEY environment variable")
    
    # Check for API key
    if not os.getenv('DEEPGRAM_API_KEY'):
        print("\n❌ ERROR: DEEPGRAM_API_KEY not set!")
        print("   Set it with: export DEEPGRAM_API_KEY='your_key'")
        return
    
    chat = SimpleVoiceChat()
    
    try:
        await chat.conversation_loop()
    finally:
        await chat.cleanup()


if __name__ == "__main__":
    asyncio.run(main())

