"""
LiveKit Multi-Agent Loan Recovery System
=========================================
Replicates Google ADK multi-agent architecture using LiveKit's low-latency pipeline.

Features:
- Multi-agent orchestration with silent manager pattern
- CSV data integration for customer management
- Automatic workflow progression
- AssemblyAI STT + Deepgram TTS for optimal performance
- Google Gemini LLM for reasoning

Architecture:
- MultiAgentCoordinator: Silent manager that orchestrates workflow
- Phase-based progression: initial → profile_search → recovery → escalation → complete
- Function tools for each agent action
- Context management across conversation
"""

import logging
import os
from dotenv import load_dotenv
from livekit import agents
from livekit.agents import Agent, AgentSession, RunContext
from livekit.agents.llm import function_tool
from livekit.plugins import google, deepgram, silero, assemblyai
from datetime import datetime
from typing import Dict, List, Optional

# Load environment
load_dotenv(".env")

# Import our tools
from loan_recovery.tools.csv_reader import read_customer_data
from loan_recovery.config import GEMINI_MODEL

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MultiAgentCoordinator(Agent):
    """
    Main coordinator that manages the multi-agent workflow.
    Implements Google ADK's silent manager pattern with LiveKit.
    
    Workflow Phases:
    1. initial → User greeting, system loads
    2. profile_search → Searching for customer in database
    3. profile_found → Customer validated, ready for recovery
    4. recovery → Junior executive handling payment discussion
    5. escalation → Senior manager handling payment modifications
    6. complete → Conversation concluded
    """
    
    def __init__(self):
        super().__init__(
            instructions="""You are the Customer Service Coordinator for a loan recovery system.

IMPORTANT: The USER is an ADMIN, not the customer. The admin instructs you to call customers.

YOUR ROLE:
- Help admin search for customer records in the database
- Wait for admin to say "start the call" before initiating recovery call
- When call starts, you become Alice (Recovery Executive) who talks TO the customer
- The admin will role-play as the customer and respond on their behalf

IMPORTANT GUIDELINES:
- Address the CUSTOMER by name (not the admin)
- Be empathetic and professional
- Keep responses concise (2-3 sentences max for voice clarity)
- Use natural, conversational language

WORKFLOW:
1. Admin provides a customer name
2. Search for the customer account
3. If defaulter found, inform admin and wait for "start the call" instruction
4. When admin says "start the call", you become Alice calling the customer
5. Admin will respond AS the customer
6. Conduct recovery conversation as Alice
7. Handle escalations to senior manager if needed
8. Conclude with clear next steps

Start by asking the admin which customer account they want to look up."""
        )
        
        # Workflow state
        self.current_phase = "initial"  # initial, profile_search, profile_found, awaiting_call_start, recovery, escalation, complete
        self.customer_profile: Optional[Dict] = None
        self.conversation_context: List[Dict] = []
        
        # Recovery agent name
        self.recovery_agent_name = "Alice"
    
    # ====================================================================
    # PHASE 1 & 2: Customer Profile Search
    # ====================================================================
    
    @function_tool
    async def search_customer(self, context: RunContext, customer_name: str) -> str:
        """Search for a customer by name in the loan database.
        
        Args:
            customer_name: Full or partial name of the customer to search for
            
        Returns:
            Customer information if found, or helpful error message
        """
        logger.info(f"[COORDINATOR] Searching for customer: {customer_name}")
        self.current_phase = "profile_search"
        
        # Use CSV reader tool
        result = read_customer_data(customer_name=customer_name)
        
        if result.get("status") == "success" and result.get("customer_found"):
            self.customer_profile = result.get("customer_profile")
            self.current_phase = "profile_found"
            
            # Extract key information
            name = self.customer_profile.get('Name', 'Customer')
            loan_type = self.customer_profile.get('Loan_Type', 'loan')
            loan_amount = self.customer_profile.get('Loan_Amount', '0')
            emi_amount = self.customer_profile.get('EMI_Amount', '0')
            days_overdue = self.customer_profile.get('Days_Overdue', '0')
            status = self.customer_profile.get('Status', 'Unknown')
            
            # Check if defaulter
            if result.get("is_defaulter"):
                logger.info(f"[COORDINATOR] Defaulter found, waiting for call initiation")
                self.current_phase = "awaiting_call_start"
                
                return f"""Found customer: {name}. Status: Defaulter with {loan_type} of ₹{loan_amount}, overdue for {days_overdue} days. 
Ready to call {name}. Just say 'start the call' when you're ready."""
            else:
                return f"""Found customer: {name}. Status: {status}. 
This customer's {loan_type} account appears to be in good standing."""
        
        elif result.get("status") == "not_found":
            # Provide sample names to help
            samples = result.get("available_names_sample", [])
            sample_str = ", ".join(samples[:5]) if samples else "various customers"
            return f"""I couldn't find a customer with that name. Could you check the spelling? 
For example, I have records for: {sample_str}."""
        
        elif result.get("status") == "multiple_matches":
            matches = result.get("matching_customers", [])
            return f"""I found multiple customers with similar names: {', '.join(matches[:3])}. 
Could you provide the full name?"""
        
        else:
            return result.get("message", "Unable to search customer database at this time.")
    
    # ====================================================================
    # PHASE 3: Call Initiation
    # ====================================================================
    
    @function_tool
    async def initiate_recovery_call(self, context: RunContext) -> str:
        """Initiate the recovery call with the customer.
        User should say 'start the call' or 'start call' to trigger this.
        
        Returns:
            Alice's introduction and opening question
        """
        if not self.customer_profile:
            return "Let me first look up your account. What's your name?"
        
        if self.current_phase != "awaiting_call_start":
            return "The call has already been initiated."
        
        logger.info(f"[RECOVERY] Starting call with Alice (Recovery Executive)")
        self.current_phase = "recovery"
        
        # Extract customer info
        name = self.customer_profile.get('Name', 'Customer')
        phone = self.customer_profile.get('Phone', 'your number')
        loan_type = self.customer_profile.get('Loan_Type', 'loan')
        loan_amount = self.customer_profile.get('Loan_Amount', '0')
        days_overdue = self.customer_profile.get('Days_Overdue', '0')
        
        return f"""Connecting you now... 

Hello, am I speaking with {name}? This is {self.recovery_agent_name} calling from the Loan Recovery Department. 
I'm calling regarding your {loan_type} account. I can see the account has been overdue for {days_overdue} days now. 
Can you tell me about your current financial situation? What's preventing you from making the payments?"""
    
    # ====================================================================
    # PHASE 4: Recovery Conversation (Alice - Junior Executive)
    # ====================================================================
    
    @function_tool
    async def handle_payment_discussion(self, context: RunContext, user_response: str) -> str:
        """Handle the payment recovery conversation as a junior executive.
        
        Args:
            user_response: The customer's response or statement
            
        Returns:
            Appropriate recovery executive response
        """
        if not self.customer_profile:
            return "Let me first look up your account. What's your name?"
        
        logger.info(f"[RECOVERY] Handling payment discussion")
        self.conversation_context.append({"role": "user", "content": user_response})
        
        # Extract customer info for context
        name = self.customer_profile.get('Name', 'Customer')
        emi = self.customer_profile.get('EMI_Amount', '15000')
        loan_amount = self.customer_profile.get('Loan_Amount', '0')
        days_overdue = self.customer_profile.get('Days_Overdue', '0')
        
        # Analyze user response (case-insensitive)
        response_lower = user_response.lower()
        
        # Positive acknowledgment
        if any(word in response_lower for word in ["yes", "okay", "sure", "let's discuss", "can talk"]):
            return f"""Thank you {name}. I understand financial situations can be challenging, and I'm here to help. 
Could you share what's been making it difficult to keep up with the ₹{emi} monthly payments?"""
        
        # Financial hardship mentioned
        elif any(word in response_lower for word in ["lost job", "unemployed", "no income", "business loss", "difficult", "crisis"]):
            return f"""I'm really sorry to hear that, {name}. Losing a job is never easy. 
Would you be able to make even a partial payment to show good faith? Any amount would help your account."""
        
        # Request for time
        elif any(word in response_lower for word in ["need time", "give me time", "can't pay now", "next month", "later"]):
            return f"""I understand you need time, {name}. However, the account has been overdue for {days_overdue} days. 
Can you commit to a specific date this month for payment? I want to help you avoid further action."""
        
        # Payment commitment
        elif any(word in response_lower for word in ["will pay", "can pay", "pay by", "commit", "promise"]):
            self.current_phase = "complete"
            return f"""That's wonderful, {name}! Thank you for your commitment. Please ensure the ₹{emi} payment is made by the date you mentioned. 
You'll receive a confirmation SMS shortly. We really appreciate your cooperation!"""
        
        # Request for EMI reduction/modification
        elif any(word in response_lower for word in ["reduce", "lower", "less", "can't afford", "too much", "restructure", "modify", "change plan"]):
            logger.info(f"[RECOVERY] Payment modification requested, escalating to senior manager")
            self.current_phase = "escalation"
            return f"""I understand ₹{emi} is challenging for your current situation, {name}. 
Let me connect you with my senior manager who has the authority to discuss restructuring options. Please hold for a moment..."""
        
        # Asking about amount/details
        elif any(word in response_lower for word in ["how much", "what amount", "total", "emi", "payment"]):
            return f"""Your monthly EMI is ₹{emi}. The total loan amount was ₹{loan_amount}. 
You're currently {days_overdue} days overdue. Can you make this payment soon?"""
        
        # Refusal/resistance
        elif any(word in response_lower for word in ["can't", "won't", "unable", "impossible", "no way"]):
            return f"""I understand this is difficult, but we need to find a solution. The overdue period is significant. 
Would restructuring your EMI amount help? Or can you make a partial payment?"""
        
        # Generic response
        else:
            return f"""I hear you. Let me ask - what would be the most realistic payment option for you right now? 
We want to work with you to resolve this."""
    
    # ====================================================================
    # PHASE 5: Escalation to Senior Manager
    # ====================================================================
    
    @function_tool
    async def escalate_to_senior_manager(self, context: RunContext) -> str:
        """Escalate the conversation to senior manager for payment plan modifications.
        
        Returns:
            Senior manager's introduction and initial assessment
        """
        if not self.customer_profile:
            return "I need to verify your account first. What's your name?"
        
        logger.info(f"[SENIOR MANAGER] Taking over conversation")
        self.current_phase = "escalation"
        
        name = self.customer_profile.get('Name', 'Customer')
        current_emi = self.customer_profile.get('EMI_Amount', '15000')
        loan_type = self.customer_profile.get('Loan_Type', 'loan')
        
        return f"""Hello {name}, I'm the senior recovery manager. I've reviewed your {loan_type} account. 
I see your current EMI is ₹{current_emi}. What monthly amount would be manageable for you?"""
    
    @function_tool
    async def senior_manager_decision(self, context: RunContext, proposed_emi: str, customer_reasoning: str) -> str:
        """Senior manager makes decision on payment plan modification request.
        
        Args:
            proposed_emi: The EMI amount proposed by customer (e.g., "10000")
            customer_reasoning: Customer's explanation for requesting modification
            
        Returns:
            Senior manager's decision (approved, counter-offer, or rejected)
        """
        if not self.customer_profile:
            return "Let me first verify your account details."
        
        logger.info(f"[SENIOR MANAGER] Evaluating proposal: ₹{proposed_emi}")
        
        try:
            # Parse amounts
            proposed_amount = int(proposed_emi.replace(',', '').replace('₹', '').strip())
            current_emi_str = self.customer_profile.get('EMI_Amount', '15000').replace(',', '')
            current_emi = int(current_emi_str)
            loan_amount_str = self.customer_profile.get('Loan_Amount', '800000').replace(',', '')
            loan_amount = int(loan_amount_str)
            
            # Decision logic
            reduction_percent = ((current_emi - proposed_amount) / current_emi) * 100
            
            if proposed_amount < current_emi * 0.5:
                # Too low - reject with counter-offer
                minimum_emi = int(current_emi * 0.6)
                return f"""I understand your situation, {customer_reasoning}. However, ₹{proposed_amount} is too low to sustain the loan. 
The minimum I can approve is ₹{minimum_emi}. This would extend your tenure but keep payments manageable. Can you commit to this?"""
            
            elif proposed_amount >= current_emi * 0.6:
                # Acceptable - approve
                self.current_phase = "complete"
                new_tenure = int(loan_amount / proposed_amount) if proposed_amount > 0 else 0
                return f"""Alright, I can approve ₹{proposed_amount} as your new monthly EMI. 
This extends your loan to approximately {new_tenure} months. This is a one-time concession. Your new EMI starts next month. Confirmed!"""
            
            else:
                # Close but needs negotiation
                counter_offer = int(current_emi * 0.7)
                return f"""₹{proposed_amount} is quite low. Considering your situation, I can offer ₹{counter_offer} per month. 
This is the best we can do. Would this work for you?"""
                
        except (ValueError, TypeError) as e:
            logger.error(f"Error parsing EMI amounts: {e}")
            return "Could you specify the exact monthly EMI amount you can afford? For example, '10000' or '12000'."
    
    # ====================================================================
    # UTILITY TOOLS
    # ====================================================================
    
    @function_tool
    async def get_current_date_and_time(self, context: RunContext) -> str:
        """Get the current date and time.
        
        Returns:
            Formatted current date and time
        """
        return datetime.now().strftime("%B %d, %Y at %I:%M %p")
    
    @function_tool
    async def get_customer_info(self, context: RunContext) -> str:
        """Get the current customer's profile information.
        
        Returns:
            Summary of customer profile or message if no customer loaded
        """
        if not self.customer_profile:
            return "No customer profile currently loaded."
        
        name = self.customer_profile.get('Name', 'N/A')
        loan_type = self.customer_profile.get('Loan_Type', 'N/A')
        status = self.customer_profile.get('Status', 'N/A')
        days_overdue = self.customer_profile.get('Days_Overdue', '0')
        
        return f"Current customer: {name}, {loan_type}, Status: {status}, {days_overdue} days overdue"
    
    # ====================================================================
    # Lifecycle Methods
    # ====================================================================
    
    async def on_enter(self):
        """Called when the agent becomes active."""
        logger.info("[COORDINATOR] Multi-agent loan recovery system started")
        
        # Generate initial greeting
        await self.session.generate_reply(
            instructions="""You're speaking to an ADMIN. Ask: 
'Hello! Which customer would you like me to process?'
Keep it short and professional."""
        )
    
    async def on_exit(self):
        """Called when the agent session ends."""
        logger.info("[COORDINATOR] Multi-agent session ended")
        if self.customer_profile:
            logger.info(f"Session summary - Customer: {self.customer_profile.get('Name')}, Phase: {self.current_phase}")


# ====================================================================
# LiveKit Session Setup
# ====================================================================

async def entrypoint(ctx: agents.JobContext):
    """Entry point for the multi-agent loan recovery system."""
    
    logger.info(f"🎯 Starting Multi-Agent Loan Recovery System in room: {ctx.room.name}")
    
    # Configure the voice pipeline with best-in-class components
    session = AgentSession(
        # Speech-to-Text: AssemblyAI (high accuracy, low latency)
        stt=assemblyai.STT(),
        
        # Large Language Model: Google Gemini (reasoning + function calling)
        llm=google.LLM(
            model=GEMINI_MODEL,
            temperature=0.7,
        ),
        
        # Text-to-Speech: Deepgram (low latency, natural voice)
        tts=deepgram.TTS(
            model="aura-asteria-en",
        ),
        
        # Voice Activity Detection: Silero
        vad=silero.VAD.load(),
    )
    
    # Start the session with our multi-agent coordinator
    await session.start(
        room=ctx.room,
        agent=MultiAgentCoordinator()
    )
    
    # Event handlers for monitoring
    @session.on("agent_state_changed")
    def on_state_changed(ev):
        logger.info(f"[STATE] {ev.old_state} → {ev.new_state}")
    
    @session.on("user_started_speaking")
    def on_user_speaking():
        logger.debug("[USER] Started speaking")
    
    @session.on("user_stopped_speaking")
    def on_user_stopped():
        logger.debug("[USER] Stopped speaking")


if __name__ == "__main__":
    # Run the multi-agent system
    agents.cli.run_app(agents.WorkerOptions(entrypoint_fnc=entrypoint))

