/**
* Copyright 2025 Google LLC
*
* Licensed under the Apache License, Version 2.0 (the "License");
* you may not use this file except in compliance with the License.
* You may obtain a copy of the License at
*
*     http://www.apache.org/licenses/LICENSE-2.0
*
* Unless required by applicable law or agreed to in writing, software
* distributed under the License is distributed on an "AS IS" BASIS,
* WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
* See the License for the specific language governing permissions and
* limitations under the License.
*/

/**
 * app.js: JS code for the adk-streaming sample app with enhanced status tracking.
 * Version: 2.0 - Fixed initialization for module loading
 */

console.log('🚀 ADK Streaming App v2.0 loaded');

/**
 * Status Management
 */
let currentStatus = 'idle';
let timingData = {
  inputStartTime: null,
  inputSentTime: null,
  responseStartTime: null,
  responseEndTime: null
};

// Status update function
function updateStatus(newStatus) {
  console.log(`[STATUS] Updating to: ${newStatus}`);
  
  // Remove active class from all status indicators
  const indicators = document.querySelectorAll('.status-indicator');
  if (indicators.length === 0) {
    console.warn('[STATUS] No status indicators found in DOM');
    return;
  }
  
  indicators.forEach(el => {
    el.classList.remove('active');
  });
  
  // Add active class to current status
  const statusId = `status${newStatus.charAt(0).toUpperCase() + newStatus.slice(1)}`;
  const statusElement = document.getElementById(statusId);
  
  if (statusElement) {
    statusElement.classList.add('active');
    console.log(`[STATUS] ✓ Activated: ${statusId}`);
  } else {
    console.error(`[STATUS] ✗ Element not found: ${statusId}`);
  }
  
  currentStatus = newStatus;
}

// Update timing display
function updateTimingDisplay() {
  const inputTime = timingData.inputSentTime && timingData.inputStartTime 
    ? (timingData.inputSentTime - timingData.inputStartTime) / 1000 
    : 0;
  
  const processingTime = timingData.responseStartTime && timingData.inputSentTime
    ? (timingData.responseStartTime - timingData.inputSentTime) / 1000
    : 0;
  
  const responseTime = timingData.responseEndTime && timingData.responseStartTime
    ? (timingData.responseEndTime - timingData.responseStartTime) / 1000
    : 0;
  
  const totalTime = timingData.responseEndTime && timingData.inputStartTime
    ? (timingData.responseEndTime - timingData.inputStartTime) / 1000
    : 0;
  
  console.log(`[TIMING] Input: ${inputTime.toFixed(2)}s, Processing: ${processingTime.toFixed(2)}s, Response: ${responseTime.toFixed(2)}s, Total: ${totalTime.toFixed(2)}s`);
  
  const lastInputEl = document.getElementById('lastInputTime');
  const processingEl = document.getElementById('processingTime');
  const responseEl = document.getElementById('responseTime');
  const totalEl = document.getElementById('totalTime');
  
  if (lastInputEl) lastInputEl.textContent = inputTime > 0 ? `${inputTime.toFixed(2)}s` : '-';
  if (processingEl) processingEl.textContent = processingTime > 0 ? `${processingTime.toFixed(2)}s` : '-';
  if (responseEl) responseEl.textContent = responseTime > 0 ? `${responseTime.toFixed(2)}s` : '-';
  if (totalEl) totalEl.textContent = totalTime > 0 ? `${totalTime.toFixed(2)}s` : '-';
}

// Speech recognition for displaying what user is saying
let recognition = null;
let isRecognizing = false;

function initSpeechRecognition() {
  const speechTextEl = document.getElementById('speechText');
  
  if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
    console.warn('[SPEECH] Web Speech API not supported in this browser');
    if (speechTextEl) {
      speechTextEl.textContent = '⚠️ Speech recognition not supported (use Chrome/Edge)';
      speechTextEl.style.color = '#ff9800';
    }
    return;
  }
  
  try {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    recognition = new SpeechRecognition();
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.lang = 'en-US';
    
    console.log('[SPEECH] Speech recognition initialized successfully');
  } catch (error) {
    console.error('[SPEECH] Failed to initialize speech recognition:', error);
    if (speechTextEl) {
      speechTextEl.textContent = '⚠️ Speech recognition initialization failed';
      speechTextEl.style.color = '#f44336';
    }
  }
  
  recognition.onstart = function() {
    console.log('[SPEECH] Recognition started successfully');
    isRecognizing = true;
    const speechDisplay = document.getElementById('speechDisplay');
    const speechText = document.getElementById('speechText');
    speechDisplay.classList.remove('empty');
    speechDisplay.classList.add('listening');
    speechText.textContent = 'Listening...';
  };
  
  recognition.onresult = function(event) {
    let interimTranscript = '';
    let finalTranscript = '';
    
    for (let i = event.resultIndex; i < event.results.length; i++) {
      const transcript = event.results[i][0].transcript;
      const confidence = event.results[i][0].confidence;
      
      if (event.results[i].isFinal) {
        finalTranscript += transcript + ' ';
        console.log(`[SPEECH] Final: "${transcript}" (confidence: ${confidence || 'N/A'})`);
      } else {
        interimTranscript += transcript;
        console.log(`[SPEECH] Interim: "${transcript}"`);
      }
    }
    
    const speechText = document.getElementById('speechText');
    if (finalTranscript || interimTranscript) {
      const combined = (finalTranscript + interimTranscript).trim();
      speechText.textContent = combined;
      console.log(`[SPEECH] Displaying: "${combined}"`);
      updateStatus('listening');
    }
  };
  
  recognition.onerror = function(event) {
    console.error(`[SPEECH] ❌ Error: ${event.error}`, event);
    const speechText = document.getElementById('speechText');
    
    // Handle different error types
    switch(event.error) {
      case 'no-speech':
        console.log('[SPEECH] No speech detected, will retry...');
        speechText.textContent = 'No speech detected... (keep speaking)';
        // Restart after a delay
        if (isRecognizing && is_audio) {
          setTimeout(() => {
            try { 
              recognition.start(); 
              console.log('[SPEECH] Restarted after no-speech');
            } catch(e) {
              console.error('[SPEECH] Failed to restart:', e);
            }
          }, 1000);
        }
        break;
        
      case 'audio-capture':
        console.error('[SPEECH] Audio capture failed - check microphone permissions');
        speechText.textContent = 'Microphone error - check permissions';
        break;
        
      case 'not-allowed':
        console.error('[SPEECH] Permission denied - microphone access needed');
        speechText.textContent = 'Permission denied - allow microphone access';
        break;
        
      case 'network':
        console.error('[SPEECH] Network error - speech recognition needs internet');
        speechText.textContent = 'Network error - check internet connection';
        break;
        
      case 'aborted':
        console.log('[SPEECH] Recognition aborted');
        break;
        
      default:
        console.error(`[SPEECH] Unknown error: ${event.error}`);
        speechText.textContent = `Speech recognition error: ${event.error}`;
    }
  };
  
  recognition.onend = function() {
    console.log('[SPEECH] Recognition ended');
    if (isRecognizing && is_audio) {
      // Auto-restart if in audio mode
      console.log('[SPEECH] Auto-restarting...');
      setTimeout(() => {
        try { 
          recognition.start(); 
          console.log('[SPEECH] Successfully restarted');
        } catch(e) {
          console.error('[SPEECH] Failed to restart:', e.message);
        }
      }, 500);
    } else {
      const speechDisplay = document.getElementById('speechDisplay');
      const speechText = document.getElementById('speechText');
      speechDisplay.classList.remove('listening');
      speechDisplay.classList.add('empty');
      speechText.textContent = 'Start speaking...';
    }
  };
}

// Update connection status display
function updateConnectionStatus(status, text) {
  const connectionStatus = document.getElementById('connectionStatus');
  const connectionText = document.getElementById('connectionText');
  
  if (status === 'connected') {
    connectionStatus.classList.remove('disconnected');
    connectionText.textContent = text || 'Connected';
  } else {
    connectionStatus.classList.add('disconnected');
    connectionText.textContent = text || 'Disconnected';
  }
}

/**
 * WebSocket handling
 */

// Connect the server with a WebSocket connection
const sessionId = Math.random().toString().substring(10);
const ws_url =
  "ws://" + window.location.host + "/ws/" + sessionId;
let websocket = null;
let is_audio = false;

// Get DOM elements
const messageForm = document.getElementById("messageForm");
const messageInput = document.getElementById("message");
const messagesDiv = document.getElementById("messages");
let currentMessageId = null;

// Initialize function - runs immediately since we're a module (deferred by default)
function initialize() {
  console.log('[INIT] Initializing UI...');
  console.log('[INIT] Status indicators found:', document.querySelectorAll('.status-indicator').length);
  console.log('[INIT] Timing elements found:', 
    document.getElementById('lastInputTime') ? '✓' : '✗',
    document.getElementById('processingTime') ? '✓' : '✗',
    document.getElementById('responseTime') ? '✓' : '✗',
    document.getElementById('totalTime') ? '✓' : '✗'
  );
  
  initSpeechRecognition();
  updateStatus('idle'); // Set initial status
  
  console.log('[INIT] Initialization complete');
}

// Run initialization immediately (module scripts are deferred, so DOM is ready)
initialize();

// Debug function - call from browser console: window.testStatus()
window.testStatus = function() {
  console.log('Testing status updates...');
  const statuses = ['idle', 'listening', 'sending', 'processing', 'responding'];
  let index = 0;
  const interval = setInterval(() => {
    if (index >= statuses.length) {
      clearInterval(interval);
      updateStatus('idle');
      console.log('Test complete!');
      return;
    }
    updateStatus(statuses[index]);
    index++;
  }, 1000);
};

// WebSocket handlers
function connectWebsocket() {
  // Connect websocket
  websocket = new WebSocket(ws_url + "?is_audio=" + is_audio);
  updateConnectionStatus('connecting', 'Connecting...');

  // Handle connection open
  websocket.onopen = function () {
    // Connection opened messages
    console.log("WebSocket connection opened.");
    messagesDiv.innerHTML = '<p>✅ Connection established! ' + (is_audio ? 'Voice mode active 🎤' : 'Text mode active ⌨️') + '</p>';
    
    updateConnectionStatus('connected', 'Connected');
    updateStatus('idle');

    // Enable the Send button
    document.getElementById("sendButton").disabled = false;
    addSubmitHandler();
  };

  // Handle incoming messages
  websocket.onmessage = function (event) {
    // Parse the incoming message
    const message_from_server = JSON.parse(event.data);
    console.log("[AGENT TO CLIENT] ", message_from_server);

    // Check if the turn is complete
    if (
      message_from_server.turn_complete &&
      message_from_server.turn_complete == true
    ) {
      currentMessageId = null;
      timingData.responseEndTime = Date.now();
      updateTimingDisplay();
      updateStatus('idle');
      
      // Clear speech display after response completes
      setTimeout(() => {
        const speechDisplay = document.getElementById('speechDisplay');
        if (!speechDisplay.classList.contains('listening')) {
          document.getElementById('speechText').textContent = 'Start speaking...';
          speechDisplay.classList.add('empty');
        }
      }, 1000);
      
      return;
    }

    // Check for interrupt message
    if (
      message_from_server.interrupted &&
      message_from_server.interrupted === true
    ) {
      // Stop audio playback if it's playing
      if (audioPlayerNode) {
        audioPlayerNode.port.postMessage({ command: "endOfAudio" });
      }
      updateStatus('idle');
      return;
    }

    // If it's audio, play it
    if (message_from_server.mime_type == "audio/pcm" && audioPlayerNode) {
      audioPlayerNode.port.postMessage(base64ToArray(message_from_server.data));
      
      // Mark as responding if first audio chunk
      if (currentStatus === 'processing') {
        timingData.responseStartTime = Date.now();
        updateStatus('responding');
        updateTimingDisplay();
      }
    }

    // If it's a text, print it
    if (message_from_server.mime_type == "text/plain") {
      // add a new message for a new turn
      if (currentMessageId == null) {
        currentMessageId = 'msg-' + Math.random().toString(36).substring(7);
        const message = document.createElement("p");
        message.id = currentMessageId;
        messagesDiv.appendChild(message);
        
        // Mark timing for first response chunk
        if (currentStatus === 'processing') {
          timingData.responseStartTime = Date.now();
          updateStatus('responding');
          updateTimingDisplay();
        }
      }

      // Add message text to the existing message element
      const message = document.getElementById(currentMessageId);
      message.textContent += message_from_server.data;

      // Scroll down to the bottom of the messagesDiv
      messagesDiv.scrollTop = messagesDiv.scrollHeight;
    }
  };

  // Handle connection close
  websocket.onclose = function () {
    console.log("WebSocket connection closed.");
    document.getElementById("sendButton").disabled = true;
    messagesDiv.innerHTML = '<p>❌ Connection closed. Reconnecting in 5 seconds...</p>';
    updateConnectionStatus('disconnected', 'Reconnecting...');
    updateStatus('idle');
    
    setTimeout(function () {
      console.log("Reconnecting...");
      connectWebsocket();
    }, 5000);
  };

  websocket.onerror = function (e) {
    console.log("WebSocket error: ", e);
    updateConnectionStatus('disconnected', 'Connection error');
  };
}

// Connect WebSocket immediately (module scripts are deferred, so DOM is ready)
console.log('[INIT] Connecting WebSocket...');
connectWebsocket();

// Add submit handler to the form
function addSubmitHandler() {
  messageForm.onsubmit = function (e) {
    e.preventDefault();
    const message = messageInput.value;
    if (message) {
      // Track input timing
      timingData.inputStartTime = Date.now();
      
      // Display user message
      const p = document.createElement("p");
      p.textContent = "💬 You: " + message;
      messagesDiv.appendChild(p);
      messagesDiv.scrollTop = messagesDiv.scrollHeight;
      
      // Clear input
      messageInput.value = "";
      
      // Update status
      updateStatus('sending');
      
      // Send message
      sendMessage({
        mime_type: "text/plain",
        data: message,
      });
      
      // Mark as sent
      timingData.inputSentTime = Date.now();
      updateStatus('processing');
      updateTimingDisplay();
      
      console.log("[CLIENT TO AGENT] " + message);
    }
    return false;
  };
}

// Send a message to the server as a JSON string
function sendMessage(message) {
  if (websocket && websocket.readyState == WebSocket.OPEN) {
    const messageJson = JSON.stringify(message);
    websocket.send(messageJson);
  }
}

// Decode Base64 data to Array
function base64ToArray(base64) {
  const binaryString = window.atob(base64);
  const len = binaryString.length;
  const bytes = new Uint8Array(len);
  for (let i = 0; i < len; i++) {
    bytes[i] = binaryString.charCodeAt(i);
  }
  return bytes.buffer;
}

/**
 * Audio handling
 */

let audioPlayerNode;
let audioPlayerContext;
let audioRecorderNode;
let audioRecorderContext;
let micStream;

// Import the audio worklets
import { startAudioPlayerWorklet } from "./audio-player.js";
import { startAudioRecorderWorklet } from "./audio-recorder.js";

// Start audio
function startAudio() {
  // Start audio output
  startAudioPlayerWorklet().then(([node, ctx]) => {
    audioPlayerNode = node;
    audioPlayerContext = ctx;
    console.log('Audio output started');
  });
  
  // Start audio input
  startAudioRecorderWorklet(audioRecorderHandler).then(
    ([node, ctx, stream]) => {
      audioRecorderNode = node;
      audioRecorderContext = ctx;
      micStream = stream;
      console.log('Audio input started');
      
      // Start speech recognition for visual feedback
      console.log('[SPEECH] Attempting to start speech recognition...');
      console.log('[SPEECH] Recognition object exists:', !!recognition);
      console.log('[SPEECH] Currently recognizing:', isRecognizing);
      
      if (recognition) {
        if (!isRecognizing) {
          try {
            recognition.start();
            console.log('[SPEECH] ✓ Speech recognition start() called');
          } catch(e) {
            console.error('[SPEECH] ✗ Failed to start:', e.message);
            const speechText = document.getElementById('speechText');
            if (speechText) {
              speechText.textContent = `⚠️ Speech error: ${e.message}`;
              speechText.style.color = '#f44336';
            }
          }
        } else {
          console.log('[SPEECH] Already recognizing, skipping start()');
        }
      } else {
        console.error('[SPEECH] Recognition object is null - not initialized');
        const speechText = document.getElementById('speechText');
        if (speechText) {
          speechText.textContent = '⚠️ Speech recognition not available';
          speechText.style.color = '#ff9800';
        }
      }
      
      // Track that we're starting to listen
      if (!timingData.inputStartTime) {
        timingData.inputStartTime = Date.now();
      }
      updateStatus('listening');
    }
  );
}

// Start the audio only when the user clicked the button
// (due to the gesture requirement for the Web Audio API)
const startAudioButton = document.getElementById("startAudioButton");
startAudioButton.addEventListener("click", () => {
  startAudioButton.textContent = '🎤 Voice Active';
  startAudioButton.disabled = true;
  startAudioButton.style.background = '#ff9800';
  
  startAudio();
  is_audio = true;
  
  // Add visual indicator in messages
  const p = document.createElement("p");
  p.textContent = "🎤 Voice mode activated - Start speaking!";
  p.style.background = '#fff3e0';
  p.style.color = '#e65100';
  p.style.textAlign = 'center';
  p.style.fontWeight = '600';
  messagesDiv.appendChild(p);
  messagesDiv.scrollTop = messagesDiv.scrollHeight;
  
  connectWebsocket(); // reconnect with the audio mode
});

// Audio recorder handler
let lastAudioSendTime = Date.now();
let audioChunkCount = 0;

function audioRecorderHandler(pcmData) {
  // Track audio sending
  if (!timingData.inputSentTime) {
    timingData.inputSentTime = Date.now();
    updateStatus('sending');
  }
  
  // Send the pcm data as base64
  sendMessage({
    mime_type: "audio/pcm",
    data: arrayBufferToBase64(pcmData),
  });
  
  audioChunkCount++;
  const now = Date.now();
  
  // Log every second instead of every chunk
  if (now - lastAudioSendTime > 1000) {
    console.log(`[CLIENT TO AGENT] sent ${audioChunkCount} audio chunks (${(audioChunkCount * pcmData.byteLength / 1024).toFixed(1)} KB)`);
    lastAudioSendTime = now;
    audioChunkCount = 0;
  }
  
  // Update status to processing if we've been sending for a bit
  if (now - timingData.inputSentTime > 2000 && currentStatus === 'sending') {
    updateStatus('processing');
    updateTimingDisplay();
  }
}

// Encode an array buffer with Base64
function arrayBufferToBase64(buffer) {
  let binary = "";
  const bytes = new Uint8Array(buffer);
  const len = bytes.byteLength;
  for (let i = 0; i < len; i++) {
    binary += String.fromCharCode(bytes[i]);
  }
  return window.btoa(binary);
}
