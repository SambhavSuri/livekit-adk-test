"""
Complete LiveKit agent that integrates STT → ADK → TTS pipeline
This runs as a LiveKit agent that users can connect to via LiveKit rooms
"""
import asyncio
import logging
from livekit import agents, rtc
from livekit.agents import JobContext, WorkerOptions, cli
from voice_pipeline import VoicePipeline

logger = logging.getLogger("livekit-voice-agent")
logger.setLevel(logging.INFO)


async def entrypoint(ctx: JobContext):
    """
    LiveKit agent entry point
    
    This agent:
    1. Connects to a LiveKit room
    2. Listens to user's audio (microphone)
    3. Transcribes using Deepgram STT
    4. Sends to ADK agent API
    5. Converts response to speech using Deepgram TTS
    6. Plays audio back to user
    """
    logger.info(f"Connecting to room: {ctx.room.name}")
    await ctx.connect()
    
    # Initialize voice pipeline
    pipeline = VoicePipeline(
        adk_api_url="http://localhost:8000",
        app_name="loan_recovery_agent",
        user_id="u_123",
        session_id="s_123",
    )
    
    # Create audio source for TTS output
    audio_source = rtc.AudioSource(24000, 1)
    audio_track = rtc.LocalAudioTrack.create_audio_track("agent-voice", audio_source)
    await ctx.room.local_participant.publish_track(audio_track)
    
    logger.info("Agent ready and listening for audio")
    
    # Listen for remote audio tracks (user's microphone)
    async for event in ctx.room.events():
        if isinstance(event, rtc.TrackPublished):
            track = event.track
            if track.kind == rtc.TrackKind.KIND_AUDIO:
                logger.info(f"Received audio track from user: {track.sid}")
                
                # Create audio stream
                audio_stream = rtc.AudioStream(track)
                
                # Process through pipeline
                async for transcription in pipeline.stt_service.transcribe_stream(audio_stream):
                    if transcription["is_final"]:
                        text = transcription["text"]
                        logger.info(f"User said: {text}")
                        
                        # Send to ADK and get response
                        full_response = ""
                        async for agent_text in pipeline.send_to_adk_agent(text):
                            full_response += agent_text
                        
                        if full_response:
                            logger.info(f"Agent responding: {full_response}")
                            
                            # Convert to speech and play
                            audio_data = await pipeline.tts_service.synthesize_to_audio(full_response)
                            await audio_source.capture_frame(audio_data)
    
    await pipeline.close()


if __name__ == "__main__":
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
        )
    )

