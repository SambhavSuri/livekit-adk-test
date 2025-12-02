import asyncio
import logging
from typing import AsyncIterator, Optional
from livekit import rtc
from livekit.plugins import deepgram
from dotenv import load_dotenv
import os

# Load .env file if it exists
if os.path.exists('.env'):
    load_dotenv()

logger = logging.getLogger("deepgram-stt")
logger.setLevel(logging.INFO)


class DeepgramSTTService:
    """Standalone Speech-to-Text service using Deepgram"""
    
    def __init__(
        self,
        model: str = "nova-2-general",
        language: str = "en-US",
        smart_format: bool = True,
        interim_results: bool = True,
    ):
        """
        Initialize Deepgram STT service
        
        Args:
            model: Deepgram model to use (nova-2-general, base, enhanced, etc.)
            language: Language code (en-US, en-GB, etc.)
            smart_format: Enable automatic punctuation and capitalization
            interim_results: Return interim results before final transcription
        """
        self.model = model
        self.language = language
        self.smart_format = smart_format
        self.interim_results = interim_results
        self.stt = None
        
        logger.info(f"Initialized Deepgram STT with model: {model}, language: {language}")
        
    def initialize(self):
        """Initialize the Deepgram STT instance"""
        self.stt = deepgram.STT(
            model=self.model,
            language=self.language,
            smart_format=self.smart_format,
            interim_results=self.interim_results,
        )
        return self.stt
    
    async def transcribe_stream(
        self, 
        audio_stream: rtc.AudioStream
    ) -> AsyncIterator[dict]:
        """
        Transcribe audio stream in real-time
        
        Args:
            audio_stream: LiveKit audio stream
            
        Yields:
            dict with keys:
                - text: Transcribed text
                - is_final: Whether this is a final result
                - confidence: Confidence score (0-1)
        """
        if not self.stt:
            self.initialize()
            
        logger.info("Starting audio transcription stream")
        
        async for event in self.stt.stream(audio_stream):
            if event.alternatives:
                alternative = event.alternatives[0]
                result = {
                    "text": alternative.transcript,
                    "is_final": event.is_final,
                    "confidence": alternative.confidence if hasattr(alternative, 'confidence') else None,
                }
                
                if event.is_final:
                    logger.info(f"Final transcription: {result['text']}")
                else:
                    logger.debug(f"Interim transcription: {result['text']}")
                    
                yield result
    
    async def transcribe_audio_data(self, audio_data: bytes) -> str:
        """
        Transcribe audio data (one-shot transcription)
        
        Args:
            audio_data: Raw audio bytes
            
        Returns:
            Transcribed text
        """
        if not self.stt:
            self.initialize()
            
        logger.info("Transcribing audio data")
        
        # For one-shot transcription, we'd typically use Deepgram's REST API
        # This is a placeholder for streaming approach
        result = await self.stt.recognize(audio_data)
        
        if result.alternatives:
            text = result.alternatives[0].transcript
            logger.info(f"Transcription complete: {text}")
            return text
        
        return ""


# Example usage
async def main():
    """Example usage of DeepgramSTTService"""
    
    # Initialize STT service
    stt_service = DeepgramSTTService(
        model="nova-2-general",
        language="en-US",
    )
    
    # Example: Connect to LiveKit room and transcribe
    # (You would replace this with your actual audio source)
    logger.info("STT Service ready to transcribe audio")
    
    # In real usage, you would:
    # 1. Get audio stream from LiveKit room
    # 2. Pass it to transcribe_stream()
    # 3. Process the transcription results
    

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())

