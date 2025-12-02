"""
Example usage of standalone STT and TTS services
"""
import asyncio
import logging
from stt_service import DeepgramSTTService
from tts_service import DeepgramTTSService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("example")


async def stt_example():
    """Example: Using STT service to transcribe audio"""
    logger.info("=== STT Example ===")
    
    # Initialize STT service
    stt = DeepgramSTTService(
        model="nova-2-general",
        language="en-US",
        smart_format=True,
    )
    
    logger.info("STT service initialized and ready to transcribe")
    # In real usage, you would pass an audio stream to stt.transcribe_stream()


async def tts_example():
    """Example: Using TTS service to generate speech"""
    logger.info("=== TTS Example ===")
    
    # Initialize TTS service
    tts = DeepgramTTSService(
        model="aura-asteria-en",
        sample_rate=24000,
    )
    
    # Synthesize some text
    text = "Hello! This is a test of the Deepgram text to speech service."
    audio_data = await tts.synthesize_to_audio(text)
    
    logger.info(f"Generated {len(audio_data)} bytes of audio")
    
    # List available voices
    voices = await tts.get_available_voices()
    logger.info(f"Available voices: {', '.join(voices[:3])}...")


async def main():
    """Run all examples"""
    await stt_example()
    print()
    await tts_example()


if __name__ == "__main__":
    asyncio.run(main())

