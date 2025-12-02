import asyncio
import logging
import httpx
import json
import os
from typing import AsyncIterator
from stt_service import DeepgramSTTService
from tts_service import DeepgramTTSService
from dotenv import load_dotenv

# Load .env file if it exists
if os.path.exists('.env'):
    load_dotenv()

logger = logging.getLogger("voice-pipeline")
logger.setLevel(logging.INFO)


class VoicePipeline:
    """
    Complete voice pipeline: STT → ADK Agent → TTS
    
    Flow:
    1. User speaks → Deepgram STT (streaming)
    2. Transcribed text → ADK API Server (streaming response)
    3. Agent response → Deepgram TTS (voice output)
    """
    
    def __init__(
        self,
        adk_api_url: str = "http://localhost:8000",
        app_name: str = "loan_recovery_agent",
        user_id: str = "u_123",
        session_id: str = "s_123",
        stt_model: str = "nova-2-general",
        tts_model: str = "aura-asteria-en",
    ):
        """
        Initialize the voice pipeline
        
        Args:
            adk_api_url: URL of the ADK API server
            app_name: ADK agent app name
            user_id: User ID for session
            session_id: Session ID
            stt_model: Deepgram STT model
            tts_model: Deepgram TTS voice model
        """
        self.adk_api_url = adk_api_url
        self.app_name = app_name
        self.user_id = user_id
        self.session_id = session_id
        
        # Initialize STT and TTS services
        self.stt_service = DeepgramSTTService(
            model=stt_model,
            language="en-US",
            interim_results=True,
        )
        
        self.tts_service = DeepgramTTSService(
            model=tts_model,
            sample_rate=24000,
        )
        
        self.http_client = httpx.AsyncClient(timeout=60.0)
        
        logger.info(f"Initialized Voice Pipeline: {app_name} | User: {user_id} | Session: {session_id}")
    
    async def ensure_session_exists(self) -> bool:
        """
        Ensure the session exists, create if it doesn't
        
        Returns:
            True if session exists or was created successfully
        """
        # Try to get the session
        get_url = f"{self.adk_api_url}/apps/{self.app_name}/users/{self.user_id}/sessions/{self.session_id}"
        
        try:
            response = await self.http_client.get(get_url)
            if response.status_code == 200:
                logger.info("Session already exists")
                return True
        except Exception as e:
            logger.debug(f"Session doesn't exist: {e}")
        
        # Create new session
        create_url = f"{self.adk_api_url}/apps/{self.app_name}/users/{self.user_id}/sessions/{self.session_id}"
        
        try:
            response = await self.http_client.post(create_url, json={})
            if response.status_code == 200:
                logger.info(f"Created new session: {self.session_id}")
                return True
            else:
                logger.error(f"Failed to create session: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            logger.error(f"Error creating session: {e}")
            return False
    
    async def send_to_adk_agent(self, text: str, use_streaming: bool = True) -> AsyncIterator[str]:
        """
        Send transcribed text to ADK agent and get streaming response
        
        Args:
            text: Transcribed text from STT
            use_streaming: Enable SSE streaming for faster responses
            
        Yields:
            Text responses from the agent
        """
        # Ensure session exists before sending
        await self.ensure_session_exists()
        
        if use_streaming:
            # Use SSE streaming endpoint for faster responses
            url = f"{self.adk_api_url}/run_sse"
            
            payload = {
                "appName": self.app_name,
                "userId": self.user_id,
                "sessionId": self.session_id,
                "newMessage": {
                    "role": "user",
                    "parts": [{"text": text}]
                },
                "streaming": True  # Enable token-level streaming
            }
            
            logger.info(f"Sending to ADK agent (SSE streaming): {text}")
            
            try:
                seen_texts = set()  # Track seen text to avoid duplicates
                
                async with self.http_client.stream("POST", url, json=payload) as response:
                    if response.status_code != 200:
                        logger.error(f"ADK API error: {response.status_code}")
                        return
                    
                    # Process Server-Sent Events
                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            data_str = line[6:]  # Remove "data: " prefix
                            try:
                                event = json.loads(data_str)
                                
                                # Extract text from the event
                                if "content" in event and "parts" in event["content"]:
                                    for part in event["content"]["parts"]:
                                        if "text" in part and part["text"]:
                                            text_response = part["text"].strip()
                                            
                                            # Only yield if we haven't seen this exact text before
                                            if text_response and text_response not in seen_texts:
                                                seen_texts.add(text_response)
                                                logger.debug(f"Agent response chunk: {text_response}")
                                                yield text_response
                            except json.JSONDecodeError:
                                logger.warning(f"Failed to parse JSON: {data_str}")
                                continue
                                
            except Exception as e:
                logger.error(f"Error calling ADK agent (SSE): {e}")
        else:
            # Fallback to non-streaming endpoint
            url = f"{self.adk_api_url}/run"
            
            payload = {
                "appName": self.app_name,
                "userId": self.user_id,
                "sessionId": self.session_id,
                "newMessage": {
                    "role": "user",
                    "parts": [{"text": text}]
                }
            }
            
            logger.info(f"Sending to ADK agent: {text}")
            
            try:
                response = await self.http_client.post(url, json=payload)
                
                if response.status_code != 200:
                    logger.error(f"ADK API error: {response.status_code} - {response.text}")
                    return
                
                # Parse the response (it returns a list of events)
                events = response.json()
                
                # Extract text from all events
                for event in events:
                    if "content" in event and "parts" in event["content"]:
                        for part in event["content"]["parts"]:
                            if "text" in part:
                                text_response = part["text"]
                                logger.info(f"Agent response: {text_response}")
                                yield text_response
                                
            except Exception as e:
                logger.error(f"Error calling ADK agent: {e}")
    
    async def process_transcription(self, transcription_result: dict) -> None:
        """
        Process transcription result and send to agent
        
        Args:
            transcription_result: Result from STT service
        """
        text = transcription_result.get("text", "").strip()
        is_final = transcription_result.get("is_final", False)
        
        if not text:
            return
        
        # Only process final transcriptions
        if is_final:
            logger.info(f"[USER SAID]: {text}")
            
            # Send to ADK agent and collect all response text
            full_response = ""
            async for agent_text in self.send_to_adk_agent(text):
                full_response += agent_text
            
            # Convert full response to speech
            if full_response:
                logger.info(f"[AGENT SAID]: {full_response}")
                audio_data = await self.tts_service.synthesize_to_audio(full_response)
                logger.info(f"Generated {len(audio_data)} bytes of audio output")
                
                # TODO: Play or stream audio_data to user
                # In LiveKit, you would stream this to an audio track
                return audio_data
    
    async def run_streaming_pipeline(self, audio_stream):
        """
        Run the complete streaming pipeline
        
        Args:
            audio_stream: LiveKit audio stream from user's microphone
        """
        logger.info("Starting streaming voice pipeline")
        
        # Stream audio through STT
        async for transcription_result in self.stt_service.transcribe_stream(audio_stream):
            # Process each transcription and send to agent
            await self.process_transcription(transcription_result)
    
    async def single_turn_conversation(self, user_audio_data: bytes) -> bytes:
        """
        Process a single turn of conversation (for testing without LiveKit)
        
        Args:
            user_audio_data: Raw audio bytes from user
            
        Returns:
            Audio response from agent
        """
        logger.info("Processing single turn conversation")
        
        # Transcribe user audio
        transcription = await self.stt_service.transcribe_audio_data(user_audio_data)
        logger.info(f"[USER SAID]: {transcription}")
        
        # Send to agent and collect response
        full_response = ""
        async for agent_text in self.send_to_adk_agent(transcription):
            full_response += agent_text
        
        logger.info(f"[AGENT SAID]: {full_response}")
        
        # Convert to speech
        audio_response = await self.tts_service.synthesize_to_audio(full_response)
        
        return audio_response
    
    async def close(self):
        """Cleanup resources"""
        await self.http_client.aclose()
        await self.tts_service.close()


# Example usage and testing
async def test_text_pipeline():
    """Test the pipeline with text input (simulating perfect STT)"""
    logger.info("=== Testing Voice Pipeline ===")
    
    pipeline = VoicePipeline(
        adk_api_url="http://localhost:8000",
        app_name="loan_recovery_agent",
        user_id="u_123",
        session_id="s_123",
    )
    
    # Simulate a transcription result
    test_message = "Hello, I need help with my loan"
    
    logger.info(f"Simulating user saying: {test_message}")
    
    # Send to agent and get response
    full_response = ""
    async for agent_text in pipeline.send_to_adk_agent(test_message):
        full_response += agent_text
    
    if full_response:
        logger.info(f"Agent responded: {full_response}")
        
        # Convert to speech
        audio_data = await pipeline.tts_service.synthesize_to_audio(full_response)
        logger.info(f"Generated {len(audio_data)} bytes of audio")
    
    await pipeline.close()


async def main():
    """Main entry point"""
    await test_text_pipeline()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    asyncio.run(main())

