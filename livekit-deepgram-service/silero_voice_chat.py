"""
Professional Voice Chat using Silero VAD (Direct PyTorch Model)

Uses the original Silero VAD PyTorch model for professional speech detection:
- Excellent background noise filtering
- Accurate speech detection
- Fast and efficient
- Works standalone without LiveKit
"""
import asyncio
import logging
import os
from datetime import datetime
import sys
import torch
import numpy as np
import sounddevice as sd
import aiohttp
import wave
import tempfile
import time

from voice_pipeline import VoicePipeline

# Create logs directory if it doesn't exist
log_dir = os.path.join(os.path.dirname(__file__), "logs")
os.makedirs(log_dir, exist_ok=True)

# Setup logging
log_filename = os.path.join(log_dir, f"voice_chat_performance_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_filename),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("silero-voice-chat")
perf_logger = logging.getLogger("performance")


class SileroVoiceChat:
    """Voice chat with Silero VAD for professional speech detection"""
    
    def __init__(self):
        self.pipeline = VoicePipeline(
            adk_api_url="http://localhost:8000",
            app_name="loan_recovery_agent",
            user_id="voice_user",
            session_id="voice_session_silero",
        )
        
        # Audio settings
        self.sample_rate = 16000  # Silero VAD requires 16kHz
        self.channels = 1
        self.chunk_duration = 0.032  # 32ms chunks (512 samples at 16kHz)
        self.chunk_size = int(self.sample_rate * self.chunk_duration)
        
        # Load Silero VAD model
        print("🔄 Loading Silero VAD model...")
        self.vad_model, utils = torch.hub.load(
            repo_or_dir='snakers4/silero-vad',
            model='silero_vad',
            force_reload=False,
            onnx=False
        )
        self.get_speech_timestamps = utils[0]
        print("✅ Silero VAD loaded successfully!")
        
        # VAD settings
        self.speech_threshold = 0.5  # Confidence threshold (0-1)
        self.silence_duration_for_stop = 0.8  # 800ms silence = end of speech
        self.min_speech_duration = 0.3  # Minimum 300ms of speech
        
        # State
        self.is_processing = False
        self.conversation_count = 0
        self.is_speaking = False
        self.speech_frames = []
        self.silence_start_time = None
        self.speech_start_time = None
        
        # Deepgram for STT
        self.deepgram_key = os.getenv('DEEPGRAM_API_KEY')
        if not self.deepgram_key:
            raise ValueError("DEEPGRAM_API_KEY not set")
        
        perf_logger.info("="*80)
        perf_logger.info("SILERO VAD VOICE CHAT SESSION STARTED")
        perf_logger.info(f"Log file: {log_filename}")
        perf_logger.info("="*80)
    
    def get_audio_level(self, audio_data):
        """Calculate audio level for visualization"""
        audio_float = audio_data.astype(np.float32) / 32768.0
        rms = np.sqrt(np.mean(audio_float ** 2))
        return rms
    
    def draw_volume_bar(self, level, is_speech=False, max_level=0.15):
        """Draw a volume bar in the terminal"""
        bar_length = 50
        filled = int((level / max_level) * bar_length)
        filled = min(filled, bar_length)
        filled = max(0, filled)
        
        bar = "█" * filled + "░" * (bar_length - filled)
        percentage = int((level / max_level) * 100)
        percentage = min(100, percentage)
        
        # Color based on Silero VAD detection
        if is_speech:
            color = "\033[92m"  # Green - Silero confirmed speech
            indicator = "🗣️ "
        elif percentage > 20:
            color = "\033[93m"  # Yellow - Sound but not speech
            indicator = "🔊"
        else:
            color = "\033[90m"  # Gray - Quiet
            indicator = "👂"
        
        reset = "\033[0m"
        
        sys.stdout.write(f"\r{indicator} {color}{bar}{reset} {percentage:3d}%")
        sys.stdout.flush()
    
    def detect_speech(self, audio_chunk):
        """Use Silero VAD to detect speech in audio chunk"""
        # Convert to float32 tensor normalized to -1 to 1
        audio_float = audio_chunk.astype(np.float32) / 32768.0
        audio_tensor = torch.from_numpy(audio_float)
        
        # Get speech probability from Silero
        speech_prob = self.vad_model(audio_tensor, self.sample_rate).item()
        
        return speech_prob > self.speech_threshold, speech_prob
    
    async def listen_with_silero(self):
        """Listen continuously with Silero VAD"""
        
        print("\n" + "="*60)
        print("🎤 SILERO VAD - Professional Voice Detection")
        print("="*60)
        print("\n✨ Using Silero VAD (PyTorch Direct Model)")
        print("💡 Speak naturally - Silero filters all background noise\n")
        print("Press Ctrl+C to stop\n")
        
        # Get the event loop for threading
        loop = asyncio.get_event_loop()
        
        def audio_callback(indata, frames, time_info, status):
            """Capture and process audio with VAD"""
            if status:
                logger.warning(f"Audio status: {status}")
            
            # Calculate level for visualization
            level = self.get_audio_level(indata)
            
            # Show volume bar
            if not self.is_processing:
                self.draw_volume_bar(level, self.is_speaking)
            
            # Process with VAD if not already processing a response
            if not self.is_processing:
                # Flatten the audio data
                audio_chunk = indata.flatten()
                
                # Detect speech with Silero
                is_speech, confidence = self.detect_speech(audio_chunk)
                
                current_time = time.time()
                
                if is_speech:
                    # Speech detected
                    if not self.is_speaking:
                        self.is_speaking = True
                        self.speech_start_time = current_time
                        self.speech_frames = []
                        self.silence_start_time = None
                        print(f"\n\n🗣️  Silero: Speech started (confidence: {confidence:.2f})\n")
                        logger.info(f"Silero VAD: Speech started (confidence: {confidence:.2f})")
                    
                    # Collect speech frames
                    self.speech_frames.append(audio_chunk.copy())
                    self.silence_start_time = None
                
                else:
                    # No speech detected
                    if self.is_speaking:
                        # Track silence duration
                        if self.silence_start_time is None:
                            self.silence_start_time = current_time
                        
                        silence_duration = current_time - self.silence_start_time
                        speech_duration = current_time - self.speech_start_time if self.speech_start_time else 0
                        
                        # Check if we should stop
                        if (silence_duration >= self.silence_duration_for_stop and 
                            speech_duration >= self.min_speech_duration):
                            
                            self.is_speaking = False
                            logger.info(f"Silero VAD: Speech ended (duration: {speech_duration:.2f}s)")
                            
                            # Process the collected speech
                            if self.speech_frames:
                                print(f"\n✅ Speech ended ({speech_duration:.1f}s) - Processing...\n")
                                audio_array = np.concatenate(self.speech_frames)
                                
                                # Schedule coroutine in the event loop (thread-safe)
                                asyncio.run_coroutine_threadsafe(
                                    self.process_speech(audio_array),
                                    loop
                                )
                                
                                self.speech_frames = []
                                self.silence_start_time = None
                                self.speech_start_time = None
        
        # Start audio stream
        with sd.InputStream(
            callback=audio_callback,
            samplerate=self.sample_rate,
            channels=self.channels,
            dtype='int16',
            blocksize=self.chunk_size
        ):
            print("🎧 Listening with Silero VAD...\n")
            
            try:
                # Keep running
                while True:
                    await asyncio.sleep(0.1)
            except KeyboardInterrupt:
                print("\n\n⏹️  Stopping...")
    
    async def process_speech(self, audio_data):
        """Transcribe and send to ADK"""
        if self.is_processing:
            return
        
        self.is_processing = True
        self.conversation_count += 1
        turn_start = time.time()
        
        print("="*60)
        perf_logger.info("")
        perf_logger.info("="*80)
        perf_logger.info(f"CONVERSATION TURN #{self.conversation_count}")
        perf_logger.info("="*80)
        
        try:
            # Transcribe with Deepgram
            print("🎯 Transcribing...")
            stt_start = time.time()
            transcript = await self.transcribe_deepgram(audio_data)
            stt_time = time.time() - stt_start
            
            if not transcript:
                print("❌ No transcript\n")
                self.is_processing = False
                print("\n" + "="*60)
                print("👂 Listening...\n")
                return
            
            perf_logger.info(f"[STT] Time: {stt_time:.3f}s")
            perf_logger.info(f"[STT] Transcript: \"{transcript}\"")
            print(f"\n📝 You: \"{transcript}\"")
            
            # Send to ADK
            print("\n🤔 Agent: ", end="", flush=True)
            
            adk_start = time.time()
            first_chunk_time = None
            full_response = ""
            chunk_count = 0
            
            async for text in self.pipeline.send_to_adk_agent(transcript, use_streaming=True):
                if first_chunk_time is None:
                    first_chunk_time = time.time() - adk_start
                    perf_logger.info(f"[ADK AGENT] Time to first chunk: {first_chunk_time:.3f}s")
                
                full_response += text
                chunk_count += 1
                print(text, end="", flush=True)
            
            adk_time = time.time() - adk_start
            print()
            
            perf_logger.info(f"[ADK AGENT] Total streaming time: {adk_time:.3f}s")
            perf_logger.info(f"[ADK AGENT] Chunks received: {chunk_count}")
            
            if full_response:
                # TTS
                print("\n🔊 Playing response...")
                tts_start = time.time()
                audio_bytes = await self.pipeline.tts_service.synthesize_to_audio(full_response)
                tts_time = time.time() - tts_start
                
                perf_logger.info(f"[TTS] Generation time: {tts_time:.3f}s")
                
                playback_start = time.time()
                self.play_audio(audio_bytes)
                playback_time = time.time() - playback_start
                
                perf_logger.info(f"[PLAYBACK] Duration: {playback_time:.2f}s")
                
                total_time = time.time() - turn_start
                perf_logger.info(f"\n[SUMMARY] Total: {total_time:.2f}s")
                perf_logger.info(f"  - STT: {stt_time:.2f}s")
                perf_logger.info(f"  - ADK (first chunk): {first_chunk_time:.2f}s ⚡")
                perf_logger.info(f"  - TTS: {tts_time:.2f}s")
                
                print("\n" + "="*60)
                print("👂 Listening...\n")
        
        except Exception as e:
            logger.error(f"Error: {e}")
            print(f"\n❌ Error: {e}")
            print("\n" + "="*60)
            print("👂 Listening...\n")
        finally:
            self.is_processing = False
    
    async def transcribe_deepgram(self, audio_data):
        """Transcribe with Deepgram REST API"""
        # Save to WAV
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
            wav_path = f.name
        
        with wave.open(wav_path, 'wb') as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(self.sample_rate)
            wav_file.writeframes(audio_data.tobytes())
        
        # Call Deepgram
        url = "https://api.deepgram.com/v1/listen"
        headers = {
            "Authorization": f"Token {self.deepgram_key}",
            "Content-Type": "audio/wav"
        }
        params = {
            "model": "nova-2-general",
            "smart_format": "true"
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                with open(wav_path, 'rb') as audio:
                    async with session.post(url, headers=headers, params=params, data=audio) as resp:
                        if resp.status == 200:
                            result = await resp.json()
                            transcript = result['results']['channels'][0]['alternatives'][0]['transcript']
                            os.unlink(wav_path)
                            return transcript
                        else:
                            os.unlink(wav_path)
                            return ""
        except Exception as e:
            logger.error(f"Transcription error: {e}")
            if os.path.exists(wav_path):
                os.unlink(wav_path)
            return ""
    
    def play_audio(self, audio_bytes, sample_rate=24000):
        """Play audio"""
        try:
            audio_array = np.frombuffer(audio_bytes, dtype=np.int16)
            audio_float = audio_array.astype(np.float32) / 32768.0
            
            sd.play(audio_float, samplerate=sample_rate)
            sd.wait()
        except Exception as e:
            logger.error(f"Playback error: {e}")
    
    async def cleanup(self):
        """Cleanup"""
        perf_logger.info("")
        perf_logger.info("="*80)
        perf_logger.info(f"SESSION ENDED - Conversations: {self.conversation_count}")
        perf_logger.info(f"Log: {log_filename}")
        perf_logger.info("="*80)
        
        await self.pipeline.close()
        print(f"\n📊 Performance log: {log_filename}")


async def main():
    """Main entry point"""
    print("\n" + "="*70)
    print("🎙️  SILERO VAD VOICE CHAT (PyTorch Direct)")
    print("="*70)
    print("\n📋 Configuration:")
    print("   - VAD: Silero VAD (PyTorch Model)")
    print("   - STT: Deepgram Nova 2")
    print("   - TTS: Deepgram Aura")
    print("   - ADK Server: http://localhost:8000")
    print("   - Agent: loan_recovery_agent")
    print(f"   - Log: {log_filename}")
    print("\n✨ Silero VAD Features:")
    print("   - Professional speech detection")
    print("   - Excellent background noise filtering")
    print("   - 0.8s silence threshold")
    print("   - Automatic speech start/end detection")
    print("   - Confidence-based detection")
    print("\n" + "="*70)
    
    if not os.getenv('DEEPGRAM_API_KEY'):
        print("\n❌ ERROR: DEEPGRAM_API_KEY not set!")
        return
    
    chat = SileroVoiceChat()
    
    try:
        print("\n🚀 Starting Silero VAD listener...\n")
        await chat.listen_with_silero()
    except KeyboardInterrupt:
        print("\n\n⏹️  Stopped by user")
    finally:
        await chat.cleanup()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
