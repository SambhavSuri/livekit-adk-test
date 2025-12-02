"""
Full Streaming Voice Chat - Everything in real-time!

Flow (all streaming):
1. Microphone → Deepgram STT (streaming) → Text chunks
2. On final transcription → ADK Agent (streaming) → Response chunks
3. Response text chunks → Deepgram TTS (streaming) → Audio chunks
4. Audio chunks → Speakers (immediate playback)
"""
import asyncio
import logging
import os
from voice_pipeline import VoicePipeline
import sounddevice as sd
import numpy as np
from queue import Queue
import threading

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("streaming-voice-chat")


class StreamingVoiceChat:
    """Real-time streaming voice conversation"""
    
    def __init__(self):
        self.pipeline = VoicePipeline(
            adk_api_url="http://localhost:8000",
            app_name="loan_recovery_agent",
            user_id="streaming_user",
            session_id="streaming_session",
        )
        
        # Audio settings for STT (16kHz for optimal STT)
        self.stt_sample_rate = 16000
        self.tts_sample_rate = 24000
        self.channels = 1
        
        # Streaming buffers
        self.audio_input_queue = Queue()
        self.audio_output_queue = Queue()
        self.is_recording = False
        self.is_playing = False
        
        logger.info("Streaming Voice Chat initialized")
    
    def audio_input_callback(self, indata, frames, time_info, status):
        """Callback for microphone input (runs in separate thread)"""
        if status:
            logger.warning(f"Input status: {status}")
        if self.is_recording:
            self.audio_input_queue.put(indata.copy())
    
    def audio_output_callback(self, outdata, frames, time_info, status):
        """Callback for speaker output (runs in separate thread)"""
        if status:
            logger.warning(f"Output status: {status}")
        
        if not self.audio_output_queue.empty():
            data = self.audio_output_queue.get()
            if len(data) < len(outdata):
                # Pad with zeros if needed
                outdata[:len(data)] = data
                outdata[len(data):] = 0
            else:
                outdata[:] = data[:len(outdata)]
        else:
            outdata.fill(0)
    
    async def stream_microphone_to_deepgram(self):
        """Stream microphone audio to Deepgram STT in real-time"""
        import aiohttp
        import base64
        
        deepgram_api_key = os.getenv('DEEPGRAM_API_KEY')
        if not deepgram_api_key:
            logger.error("DEEPGRAM_API_KEY not set!")
            return
        
        url = "wss://api.deepgram.com/v1/listen"
        params = {
            "encoding": "linear16",
            "sample_rate": self.stt_sample_rate,
            "channels": self.channels,
            "model": "nova-2-general",
            "language": "en-US",
            "smart_format": "true",
            "interim_results": "true"
        }
        
        headers = {
            "Authorization": f"Token {deepgram_api_key}"
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.ws_connect(
                    url + "?" + "&".join([f"{k}={v}" for k, v in params.items()]),
                    headers=headers
                ) as ws:
                    logger.info("Connected to Deepgram STT WebSocket")
                    
                    # Task to send audio to Deepgram
                    async def send_audio():
                        while self.is_recording:
                            if not self.audio_input_queue.empty():
                                audio_data = self.audio_input_queue.get()
                                # Send as binary
                                await ws.send_bytes(audio_data.tobytes())
                            await asyncio.sleep(0.01)
                        
                        # Send close message
                        await ws.send_json({"type": "CloseStream"})
                    
                    # Task to receive transcriptions from Deepgram
                    async def receive_transcriptions():
                        final_transcript = ""
                        async for msg in ws:
                            if msg.type == aiohttp.WSMsgType.TEXT:
                                result = msg.json()
                                
                                if "channel" in result:
                                    transcript = result["channel"]["alternatives"][0]["transcript"]
                                    is_final = result["is_final"]
                                    
                                    if transcript:
                                        if is_final:
                                            print(f"\n✅ [FINAL TRANSCRIPT]: {transcript}\n")
                                            logger.info(f"[FINAL] You said: {transcript}")
                                            final_transcript = transcript
                                            
                                            # Stop recording and process
                                            self.is_recording = False
                                            
                                            # Send to agent
                                            await self.process_user_speech(transcript)
                                            return  # Exit after processing
                                        else:
                                            # Show interim results in real-time
                                            print(f"\r💬 [INTERIM]: {transcript}     ", end="", flush=True)
                            elif msg.type == aiohttp.WSMsgType.ERROR:
                                logger.error(f"WebSocket error: {ws.exception()}")
                                break
                    
                    # Run both tasks concurrently
                    await asyncio.gather(
                        send_audio(),
                        receive_transcriptions()
                    )
                    
        except Exception as e:
            logger.error(f"Error in Deepgram streaming: {e}")
    
    async def process_user_speech(self, text: str):
        """Process user's speech and get agent response"""
        print(f"\n📝 You said: {text}")
        print("\n🤔 Agent is thinking...")
        
        try:
            # Get streaming response from agent
            print("🤖 Agent: ", end="", flush=True)
            full_response = ""
            async for agent_text in self.pipeline.send_to_adk_agent(text):
                full_response += agent_text
                print(agent_text, end="", flush=True)
            
            print()  # New line after response
            
            if full_response:
                # Stream TTS
                await self.stream_tts(full_response)
            
        except Exception as e:
            logger.error(f"Error processing speech: {e}")
            print(f"\n❌ Error: {e}")
    
    async def stream_tts(self, text: str):
        """Stream TTS audio and play in real-time"""
        print("\n🔊 Generating and playing voice response...")
        
        try:
            self.is_playing = True
            
            # Get audio stream from TTS
            async for audio_chunk in self.pipeline.tts_service.synthesize_streaming(text):
                # Convert to numpy array
                audio_array = np.frombuffer(audio_chunk, dtype=np.int16)
                audio_float = audio_array.astype(np.float32) / 32768.0
                
                # Add to playback queue
                self.audio_output_queue.put(audio_float)
            
            # Wait for playback to finish
            while not self.audio_output_queue.empty():
                await asyncio.sleep(0.1)
            
            self.is_playing = False
            print("✅ Playback complete\n")
            
        except Exception as e:
            logger.error(f"Error in TTS streaming: {e}")
            self.is_playing = False
    
    async def start_conversation(self):
        """Start the streaming conversation"""
        print("\n" + "="*60)
        print("🎙️  REAL-TIME STREAMING VOICE CHAT")
        print("="*60)
        print("\n💡 How it works:")
        print("   1. Press ENTER to start speaking")
        print("   2. See your words transcribed in real-time")
        print("   3. Stop speaking - it will auto-detect")
        print("   4. Agent responds with voice")
        print("\nType 'quit' to exit\n")
        print("="*60 + "\n")
        
        # Start output stream for playback
        output_stream = sd.OutputStream(
            callback=self.audio_output_callback,
            samplerate=self.tts_sample_rate,
            channels=self.channels,
            dtype='float32'
        )
        output_stream.start()
        
        # Start input stream for recording
        input_stream = sd.InputStream(
            callback=self.audio_input_callback,
            samplerate=self.stt_sample_rate,
            channels=self.channels,
            dtype='int16'
        )
        input_stream.start()
        
        try:
            while True:
                user_input = input("Press ENTER to speak (or 'quit'): ").strip()
                
                if user_input.lower() in ['quit', 'exit', 'q']:
                    print("\n👋 Goodbye!")
                    break
                
                # Start recording
                print("\n🎤 Listening... (speak now, will auto-detect when you stop)\n")
                self.is_recording = True
                
                # Stream to Deepgram (increased timeout)
                try:
                    await asyncio.wait_for(
                        self.stream_microphone_to_deepgram(),
                        timeout=30.0  # Longer timeout
                    )
                except asyncio.TimeoutError:
                    print("\n⏱️  Recording timeout - please try again")
                    self.is_recording = False
                
                print("\n" + "-"*60)
                
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
        finally:
            self.is_recording = False
            input_stream.stop()
            input_stream.close()
            output_stream.stop()
            output_stream.close()
    
    async def cleanup(self):
        """Clean up resources"""
        await self.pipeline.close()


async def main():
    """Main entry point"""
    print("\n" + "="*60)
    print("🎙️  STREAMING VOICE CHAT - EVERYTHING IN REAL-TIME!")
    print("="*60)
    print("\n📋 Features:")
    print("   ✅ Real-time STT (as you speak)")
    print("   ✅ Streaming agent responses")
    print("   ✅ Real-time TTS playback")
    print("\n⚠️  Requirements:")
    print("   1. ADK api_server running on port 8000")
    print("   2. DEEPGRAM_API_KEY environment variable")
    print("   3. Microphone and speakers enabled")
    
    # Check requirements
    if not os.getenv('DEEPGRAM_API_KEY'):
        print("\n❌ ERROR: DEEPGRAM_API_KEY not set!")
        print("   Set it with: export DEEPGRAM_API_KEY='your_key'")
        return
    
    chat = StreamingVoiceChat()
    
    try:
        await chat.start_conversation()
    finally:
        await chat.cleanup()


if __name__ == "__main__":
    asyncio.run(main())

