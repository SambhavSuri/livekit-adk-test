import asyncio
import logging
from typing import Optional
import aiohttp
from livekit import rtc
from livekit.plugins import deepgram
from dotenv import load_dotenv
import os

# Load .env file if it exists
if os.path.exists('.env'):
    load_dotenv()

logger = logging.getLogger("deepgram-tts")
logger.setLevel(logging.INFO)


class DeepgramTTSService:
    """Standalone Text-to-Speech service using Deepgram"""
    
    def __init__(
        self,
        model: str = "aura-asteria-en",
        sample_rate: int = 24000,
        encoding: str = "linear16",
    ):
        """
        Initialize Deepgram TTS service
        
        Args:
            model: Deepgram voice model (aura-asteria-en, aura-luna-en, aura-stella-en, etc.)
            sample_rate: Audio sample rate (8000, 16000, 24000, 48000)
            encoding: Audio encoding format (linear16, mulaw, alaw)
        """
        self.model = model
        self.sample_rate = sample_rate
        self.encoding = encoding
        self.tts = None
        self.http_session = None
        
        logger.info(f"Initialized Deepgram TTS with model: {model}, sample_rate: {sample_rate}")
        
    async def _ensure_http_session(self):
        """Ensure HTTP session exists for standalone usage"""
        if self.http_session is None:
            self.http_session = aiohttp.ClientSession()
        return self.http_session
        
    def initialize(self):
        """Initialize the Deepgram TTS instance"""
        # For standalone usage, we need to provide our own HTTP session
        self.tts = deepgram.TTS(
            model=self.model,
            sample_rate=self.sample_rate,
            encoding=self.encoding,
            http_session=self.http_session,
        )
        return self.tts
    
    async def synthesize_to_audio(self, text: str) -> bytes:
        """
        Synthesize text to audio data
        
        Args:
            text: Text to convert to speech
            
        Returns:
            Raw audio bytes
        """
        await self._ensure_http_session()
        
        if not self.tts:
            self.initialize()
            
        logger.info(f"Synthesizing text: {text[:50]}...")
        
        # Synthesize the text - this returns a ChunkedStream
        audio_stream = self.tts.synthesize(text)
        
        # Collect all audio chunks
        audio_data = b""
        async for chunk in audio_stream:
            audio_data += chunk.frame.data.tobytes()
        
        logger.info(f"Synthesis complete, generated {len(audio_data)} bytes of audio")
        return audio_data
    
    async def synthesize_to_stream(
        self, 
        text: str,
        audio_source: rtc.AudioSource
    ) -> None:
        """
        Synthesize text and stream to LiveKit audio source
        
        Args:
            text: Text to convert to speech
            audio_source: LiveKit audio source to stream to
        """
        if not self.tts:
            self.initialize()
            
        logger.info(f"Synthesizing and streaming text: {text[:50]}...")
        
        # Synthesize the text
        audio_data = await self.tts.synthesize(text)
        
        # Stream to audio source
        await audio_source.capture_frame(audio_data)
        
        logger.info("Audio streaming complete")
    
    async def synthesize_streaming(self, text: str):
        """
        Synthesize text with streaming (word-by-word generation)
        
        Args:
            text: Text to convert to speech
            
        Yields:
            Audio chunks as they are generated
        """
        await self._ensure_http_session()
        
        if not self.tts:
            self.initialize()
            
        logger.info(f"Starting streaming synthesis: {text[:50]}...")
        
        # Stream audio chunks as they are generated
        # The TTS.synthesize() returns a ChunkedStream, iterate over it
        stream = self.tts.synthesize(text)
        async for chunk in stream:
            logger.debug(f"Generated audio chunk: {len(chunk.frame.data)} samples")
            yield chunk.frame.data.tobytes()
    
    async def get_available_voices(self) -> list:
        """
        Get list of available Deepgram voice models
        
        Returns:
            List of available voice model names
        """
        # Deepgram Aura voices (as of latest)
        voices = [
            "aura-asteria-en",  # Female, American English
            "aura-luna-en",     # Female, American English
            "aura-stella-en",   # Female, American English
            "aura-athena-en",   # Female, British English
            "aura-hera-en",     # Female, American English
            "aura-orion-en",    # Male, American English
            "aura-arcas-en",    # Male, American English
            "aura-perseus-en",  # Male, American English
            "aura-angus-en",    # Male, Irish English
            "aura-orpheus-en",  # Male, American English
            "aura-helios-en",   # Male, British English
            "aura-zeus-en",     # Male, American English
        ]
        return voices
    async def close(self):
        """Close HTTP session"""
        if self.http_session:
            await self.http_session.close()


# Example usage
async def main():
    """Example usage of DeepgramTTSService"""
    
    # Initialize TTS service
    tts_service = DeepgramTTSService(
        model="aura-asteria-en",
        sample_rate=24000,
    )
    
    # Example: Synthesize text to audio
    text = "Hello! This is a test of the Deepgram text to speech service."
    audio_data = await tts_service.synthesize_to_audio(text)
    
    logger.info(f"Generated {len(audio_data)} bytes of audio")
    
    # Get available voices
    voices = await tts_service.get_available_voices()
    logger.info(f"Available voices: {voices}")
    
    # Clean up
    await tts_service.close()
    

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())

