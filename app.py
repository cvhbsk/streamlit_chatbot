import streamlit as st
import os
from google import genai
from google.genai import types
from pydantic import BaseModel, ValidationError
import json

# --- 1. CONFIGURATION AND MOCK DATA ---

# Gemini API Initialization (Uses st.secrets for key)
try:
    if "GEMINI_API_KEY" in st.secrets:
        client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
    else:
        st.error("Gemini API key not found in `.streamlit/secrets.toml`. Please set it to run the LLM-based scoring.")
        client = None
except Exception as e:
    st.error(f"Error initializing Gemini client: {e}")
    client = None

# Mock Database for Issue Matching (Step 3)
ISSUE_DATABASE = [
    # ------------------------------------------------------------------
    # 1. CRITICAL: NO POWER / HARDWARE FAILURE (High Priority Match)
    # ------------------------------------------------------------------
    {
        "cause": "Power Supply Unit (PSU) or Power Cable Issue",
        "keywords": ["no power", "won't turn on", "dead", "power issue", "no light", "off"],
        "action": "Check the power cable connection to the wall and the device. Try a different power outlet or a different cable (if available). If the issue persists, the internal power supply unit (PSU) or power board has failed and requires professional service."
    },
    
    # ------------------------------------------------------------------
    # 2. PRINTING/SCANNING ERRORS (Generic MFP Issues)
    # ------------------------------------------------------------------
    {
        "cause": "Driver/Software Communication or Paper Jam",
        "keywords": ["print error", "jam", "offline", "communication", "not printing", "scans blank"],
        "action": "Clear any visible or internal paper jams. Reinstall the printer drivers. If connected via Wi-Fi, run the manufacturer's network setup utility to confirm the connection status."
    },
    {
        "cause": "Empty Ink/Toner Cartridge or Low Tank Levels",
        "keywords": ["faded", "blank pages", "no color", "empty ink", "low ink", "toner low"],
        "action": "Replace the indicated ink or toner cartridge, or refill the specific ink tank to the required level. Run a print head cleaning cycle if colors are still inconsistent after replacement/refill."
    },
    {
        "cause": "Clogged Print Head (Inkjet)",
        "keywords": ["streaks", "missing lines", "banding", "poor quality", "clogged"],
        "action": "Run two cycles of 'Print Head Cleaning' from the printer utility software or the printer's maintenance menu. If the problem persists, try a 'Deep Cleaning' cycle."
    },
    {
        "cause": "Fuser Unit Failure (Laser)",
        "keywords": ["smudging", "smears", "wipes off", "not fixing", "powder"],
        "action": "The toner is not being properly fused to the paper. This usually indicates a failure in the fuser unit, which is a key component in laser printers and often requires replacement."
    },

    # ------------------------------------------------------------------
    # 3. CONNECTIVITY ISSUES
    # ------------------------------------------------------------------
    {
        "cause": "Wi-Fi Connection Loss or Incorrect Password",
        "keywords": ["wifi error", "disconnected", "no internet", "network", "can't see"],
        "action": "Restart the router and the printer. Re-enter the Wi-Fi password on the printer's control panel. Ensure the printer is on the same 2.4GHz network as the computer/phone."
    },
    {
        "cause": "USB Port/Cable Malfunction",
        "keywords": ["usb disconnect", "not recognized", "cable fault"],
        "action": "Try connecting the printer to a different USB port on your computer. If the issue continues, replace the USB cable (ensure it is rated USB 2.0 or higher)."
    },

    # ------------------------------------------------------------------
    # 4. OPERATING SYSTEM / SOFTWARE
    # ------------------------------------------------------------------
    {
        "cause": "Operating System Update Incompatibility",
        "keywords": ["after update", "os update", "windows 11", "macos Sonoma"],
        "action": "Check the manufacturer's website for the latest drivers compatible with your recent OS update. Completely remove old drivers before installing the new ones."
    },
]

# Create a master list of all possible causes for the multiselect options list
COMMON_CAUSES = [entry["cause"] for entry in ISSUE_DATABASE]

# Pydantic Schema for LLM Response (Scoring)
class ScoringResponse(BaseModel):
    """Schema for the model's response on statement scoring."""
    score_status: str  # 'GOOD' or 'LOW'
    follow_up_questions: list[str] # List of 2 to 3 questions if score is LOW

# --- 2. LLM FUNCTIONS ---

def get_scoring_and_suggestions(problem_statement: str):
    """Calls Gemini to score the problem statement and suggest follow-up questions."""
    
    if not client:
        # Mock LLM behavior if client is not available
        st.session_state.chat_history.append({"role": "assistant", "content": "*(LLM Mock: Running in low-detail mode. Assuming statement is **'GOOD'**.)*"})
        return "GOOD", []

    system_prompt = (
        "You are an AI technical support triage system. Your task is to evaluate a user's initial problem statement for a hardware issue. "
        "The problem statement must be complete, specific, and include relevant details like device, error messages, and WHEN the issue started. "
        "Based on this evaluation, you must return a JSON object."
        "\n\nJSON Schema:\n"
        "1. **score_status**: Return 'GOOD' if the statement is detailed, specific, and clear. Return 'LOW' if it is vague, too general, or lacks critical detail (e.g., 'My PC is broken')."
        "2. **follow_up_questions**: If the score_status is 'LOW', provide 2-3 specific questions to help the user elaborate (e.g., 'What is the exact error code?', 'Did you recently install new software?'). If the score_status is 'GOOD', this list should be empty."
    )

    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=f"User's problem statement: '{problem_statement}'",
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                response_mime_type="application/json",
                response_schema=ScoringResponse,
            ),
        )
        
        # Validate and parse the structured JSON response
        data = ScoringResponse.model_validate_json(response.text)
        return data.score_status, data.follow_up_questions

    except Exception as e:
        # Fallback for API/Pydantic errors
        st.session_state.chat_history.append({"role": "assistant", "content": f"*(LLM Error: Failed to process request. Assuming score is **'GOOD'** to proceed.)*"})
        st.exception(e) # Show the error to the coder/user
        return "GOOD", []

# --- UTILITY FUNCTION FOR PROGRESS ---

def handle_diagnosis_confirmation(user_input):
    """Handles Step 3: User confirms/adjusts the automated diagnosis via multiselect."""
    # The multiselect value is already stored in st.session_state.selected_causes 
    # when the user interacts with the widget on the page.
    
    # We just need to check if the user clicked the transition button.
    # The button logic will be tied to st.form_submit_button, not this handler.
    # We will remove this function and integrate the logic directly into the UI block for simplicity.
    pass # No need for a separate handler function here since we use a form submit button.

def run_with_progress(task_description, func, *args, **kwargs):
    """Shows a spinner and processing message while running a function."""
    with st.chat_message("assistant"):
        with st.spinner(f"**Thinking...** {task_description}"):
            # Add a message to the chat history to reflect the processing
            st.session_state.chat_history.append({"role": "assistant", "content": f"*(Processing: {task_description})*"})
            
            # Run the actual function
            result = func(*args, **kwargs)
            
            # Remove the processing message from the history before showing the final result
            st.session_state.chat_history.pop() 
            
            return result

# --- NEW LLM FUNCTION FOR FINAL SUMMARY ---

def generate_human_summary(structured_statement: str) -> str:
    """Uses the LLM to convert the structured statement into a clean, human-readable summary."""
    if not client:
        # Fallback if LLM is disabled
        return f"SUMMARY: {structured_statement.replace('Initial Problem:', '').replace('Additional Details:', ' - ')}"

    system_prompt = (
        "You are an expert technical writer. Your task is to take a structured problem description "
        "(Initial Problem and Additional Details) and synthesize it into a single, clear, coherent, "
        "and human-readable problem statement (a few sentences maximum). Do not add a greeting or closing. "
        "Only output the final summary paragraph."
    )
    
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=structured_statement,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
            ),
        )
        return response.text.strip()
        
    except Exception as e:
        # Fallback if LLM fails here
        st.error(f"Error generating final summary: {e}")
        return f"Could not generate summary. Raw data: {structured_statement}"

# --- REVISED handle_confirmation FUNCTION ---
def handle_confirmation(user_input):
    """Handles Step 2.5: User confirms the problem statement summary."""
    user_response = user_input.lower().strip()
    update_chat("user", user_input)
    
    if user_response in ["yes", "yep", "correct", "yes it is", "yes, correct"]:
        st.session_state.problem_statement_confirmed = True
        
        # 💡 NEW LOGIC: Automatically diagnose using the confirmed problem statement
        action, cause = find_best_match_action_by_statement(st.session_state.problem_statement)
        st.session_state.suggested_action = action
        st.session_state.suggested_cause = cause

        # 💡 NEW: Initialize selected_causes with the single suggested cause
        st.session_state.selected_causes = [cause]
        
        update_chat("assistant", f"Great, confirmed! Based on your detailed statement, I have identified the most probable cause as **{cause}**. \n\nBefore escalating, please try this suggested action:\n\n**Action:** {action}\n\nIf the issue persists, we need to create a formal case. Please fill out the form below.")
        
        st.session_state.step = 4 # Skip old Step 3 and go directly to the Case Form (now Step 4)
        
    elif user_response in ["no", "nope", "incorrect", "no it's not", "no, incorrect"]:
        st.session_state.problem_statement_confirmed = False
        
        # Clear refinement and go back to a manual input to fix the summary
        st.session_state.refinement_history = []
        st.session_state.pending_questions = []
        
        update_chat("assistant", "Apologies for the misunderstanding. Please provide a **new, complete and accurate summary** of your issue, incorporating any details I missed. This will restart the scoring process.")
        st.session_state.step = 1.5
    
    else:
        # Prompt for a clear Yes/No answer
        update_chat("assistant", "Please confirm by simply typing 'Yes' or 'No'.")
        # Step remains 2.5
        
    st.rerun()


# --- REVISED DIAGNOSIS FUNCTION BASED ON TEXT ---

def find_best_match_action_by_statement(problem_statement: str):
    """Performs a simple keyword match against the mock database using the full problem statement."""
    
    statement_lower = problem_statement.lower()
    
    # --- 1. CRITICAL PRIORITY CHECK (NO POWER) ---
    critical_power_keywords = ["no power", "won't turn on", "dead", "power issue"]
    
    is_power_issue = any(kw in statement_lower for kw in critical_power_keywords)
    
    if is_power_issue:
        # Search the database specifically for the Power Supply entry
        for db_entry in ISSUE_DATABASE:
             if db_entry["cause"] == "Power Supply Unit (PSU) or Power Cable Issue":
                 return db_entry["action"], db_entry["cause"]

    # Step 2: Fallback to the best score match for other issues (original logic)
    best_match = None
    best_score = 0
    
    for db_entry in ISSUE_DATABASE:
        score = 0
        for keyword in db_entry["keywords"]:
            if keyword in statement_lower:
                score += 1
        
        if score > best_score:
            best_score = score
            best_match = db_entry

    if best_match:
        return best_match["action"], best_match["cause"]
    else:
        return "No specific match found in the database. Please fill out the form for human review.", "Uncategorized/Complex Issue"


# --- 3. STREAMLIT APP LOGIC ---

# Initialize Session State
if "chat_history" not in st.session_state:
    st.session_state.chat_history = [{"role": "assistant", "content": "Hello! I'm your Technical Support Bot. Please describe the hardware issue you are facing to begin the triage process."}]
if "step" not in st.session_state:
    st.session_state.step = 1 # 1: Initial Input, 2: Scoring, 3: Checklist, 4: Case Form
if "problem_statement" not in st.session_state:
    st.session_state.problem_statement = ""
# 💡 REVISED: Use a list to hold all refinement attempts
if "refinement_history" not in st.session_state:
    st.session_state.refinement_history = [] 
# 💡 NEW: List of pending questions (from LLM)
if "pending_questions" not in st.session_state: 
    st.session_state.pending_questions = []
if "follow_up_questions" not in st.session_state:
    st.session_state.follow_up_questions = []
if "suggested_action" not in st.session_state:
    st.session_state.suggested_action = ""
if "suggested_cause" not in st.session_state:
    st.session_state.suggested_cause = ""
if "selected_causes" not in st.session_state:
    st.session_state.selected_causes = []
if "problem_statement_confirmed" not in st.session_state:
    st.session_state.problem_statement_confirmed = False # NEW: Flag to track confirmation


def update_chat(role, content):
    """Helper function to add messages to the chat history."""
    st.session_state.chat_history.append({"role": role, "content": content})

def reset_chat():
    """Resets the entire chat state."""
    st.session_state.chat_history = [{"role": "assistant", "content": "Hello! I'm your Technical Support Bot. Please describe the hardware issue you are facing to begin the triage process."}]
    st.session_state.step = 1
    st.session_state.problem_statement = ""
    st.session_state.refinement_history = []
    st.session_state.pending_questions = []
    st.session_state.suggested_action = ""
    st.session_state.suggested_cause = ""
    st.session_state.selected_causes = []
    # st.rerun() <--- Rerun is not needed here because the button's callback handles it.

def handle_initial_input(user_input):
    """Handles Step 1: User provides initial statement and starts the refinement loop if score is LOW."""
    update_chat("user", user_input)
    st.session_state.problem_statement = user_input # Initial statement
    
    # 💡 REVISED: Use progress indicator for the LLM call
    score, questions = run_with_progress("Analyzing your statement and generating follow-up questions...", get_scoring_and_suggestions, user_input)
    
    if score == "LOW":
        st.session_state.pending_questions = questions # Store all questions
        
        # Ask the FIRST question conversationally
        first_q = st.session_state.pending_questions.pop(0) 
        update_chat("assistant", f"Thank you for the initial statement. To provide better support, I need a little more detail. Okay, let's start with a quick question to narrow things down:\n\n**{first_q}**\n\n*(Please provide your answer.)*")
        
        st.session_state.step = 2 # Move to refinement mode
    
# --- REVISED handle_initial_input FUNCTION (Only the 'else' block) ---
# ...
    else:
        # --- LOGIC FOR CLEAR STATEMENT (HIGH SCORE) ---
        
        # 1. Run Automatic Diagnosis
        action, cause = find_best_match_action_by_statement(user_input)
        
        # 2. Save the results
        st.session_state.suggested_action = action
        st.session_state.suggested_cause = cause
        
        # 💡 NEW: Initialize selected_causes with the single suggested cause
        st.session_state.selected_causes = [cause]
        
        # 3. Inform the user
        update_chat("assistant", 
            f"Your initial problem statement is very clear! Based on this, I have identified the most probable cause as **{cause}**. Please review and confirm the diagnosis below before we proceed to the suggested action."
        )
        
        # 4. Skip Steps 2 and 2.5, and go directly to the Diagnosis Confirmation (Step 3)
        st.session_state.step = 3 # <--- MOVED TO NEW STEP 3
        
    st.rerun()

def handle_refinement(user_input):
    """Handles Step 2: User refines the statement and determines if more questions are needed."""
    update_chat("user", user_input)
    
    # 1. Store the new answer
    st.session_state.refinement_history.append(user_input)
    
    # 2. Build the FULL statement (initial + all refinements)
    # 💡 REVISED: Create a human-readable summary string for the LLM input and final display
    full_statement_for_llm = (
        f"Initial Problem: {st.session_state.problem_statement}\n"
        f"Additional Details: {', '.join(st.session_state.refinement_history)}"
    )
    
    # 3. Check if we have PENDING questions
    if st.session_state.pending_questions:
        
        # Ask the NEXT question conversationally
        next_q = st.session_state.pending_questions.pop(0)
        q_num = len(st.session_state.refinement_history)
        
        transition = "Thanks for the information. And next, can you tell me:" if q_num == 1 else "I'm still trying to narrow this down. What about this:"
        
        update_chat("assistant", f"{transition}\n\n**{next_q}**\n\n*(Please provide your answer.)*")
        st.rerun() # Stay in Step 2, waiting for next input

    else:
        # 4. If all initial questions are answered, check the score of the FULL statement
        st.session_state.problem_statement = full_statement_for_llm # Save the structured statement for later steps
        
        score, new_questions = run_with_progress("Re-analyzing the full context with your new details...", get_scoring_and_suggestions, full_statement_for_llm)

        if score == "LOW" and new_questions:
            # Score is still low: ask the new batch of questions one-by-one
            st.session_state.pending_questions = new_questions
            next_q = st.session_state.pending_questions.pop(0)
            update_chat("assistant", f"I appreciate the extra detail, but the overall picture still needs clarification. Let's try this critical question:\n\n**{next_q}**\n\n*(Please provide your answer.)*")
            
        else:
            # Score is GOOD or LLM couldn't provide more questions
            # 💡 REVISED: Generate a final, human-readable summary for display in the chat
            
            # Use the LLM (or a template if LLM is down) to make the final statement clean and coherent
            final_summary = generate_human_summary(st.session_state.problem_statement)
            
            # Store this clean summary for the final case creation step
            st.session_state.problem_statement = final_summary
            st.session_state.problem_statement_confirmed = False 
            st.session_state.step = 2.5 
            
            update_chat("assistant", f"Excellent! I've combined all the details. Before we move to the diagnostic phase, could you please confirm I have accurately summarized your issue?\n\n**My Understanding (Summary):**\n\n> {st.session_state.problem_statement}\n\nIs this statement correct? (Please answer 'Yes' or 'No')")
            
        st.rerun()


def handle_checklist_submission(selected_causes):
    """Handles Step 3: User selects causes and gets the suggested action."""
    st.session_state.selected_causes = selected_causes
    
    # Use the selected causes to find a match in the mock DB
    action, cause = find_best_match_action(selected_causes)
    st.session_state.suggested_action = action
    st.session_state.suggested_cause = cause

    # Prepare final chat message and move to Step 4
    update_chat("assistant", f"Based on your selections, the most probable cause is **{cause}**. \n\nBefore escalating, please try this suggested action:\n\n**Action:** {action}\n\nIf the issue persists, we need to create a formal case. Please fill out the form below.")
    st.session_state.step = 4
    st.rerun()

def handle_case_submission(form_data):
    """Handles Step 4: Final case submission."""
    import os # Ensure os is imported at the top of your script for this line
    
    # In a real application, this data would be sent to a CRM/ticketing system via an API call.
    # For this demonstration, we are just generating a mock case ID.
    
    # Generate a mock Case ID
    case_id = f"TKT-{os.urandom(4).hex().upper()}"

    # Prepare final chat message to confirm submission
    confirmation_message = (
        f"**Case Successfully Created!** 🎉\n\n"
        f"- **Case ID:** {case_id}\n"
        f"- **Contact:** {form_data['name']} ({form_data['email']})\n"
        f"- **Issue:** {form_data['problem_statement']}\n"
        f"- **Bot Diagnosis:** {form_data['suggested_cause']}\n\n"
        f"Your case has been submitted to a human agent who will review the suggested action and contact you shortly."
    )
    
    # Update chat history with the confirmation
    st.session_state.chat_history.append({"role": "assistant", "content": confirmation_message})
    
    # Block further chat and offer reset
    st.session_state.step = 5
    st.rerun()


# --- 4. STREAMLIT UI ---

st.set_page_config(page_title="Hardware Support Chatbot", layout="wide")
st.title("🤖 Hardware Support Triage Bot")

# Sidebar for controls
with st.sidebar:
    st.header("Chat Controls")
    st.button("Start New Chat", on_click=reset_chat, type="primary")
    st.markdown("---")
    st.markdown(f"**Current Stage:** **Step {st.session_state.step}**")
    if st.session_state.problem_statement:
        st.markdown("**Refined Problem:**")
        st.caption(st.session_state.problem_statement)
    
    # Instruction for API Key
    if not client:
        st.warning("⚠️ LLM is disabled. Set GEMINI_API_KEY in secrets.toml.")


# Chat Display Container
chat_container = st.container(height=400)
with chat_container:
    for message in st.session_state.chat_history:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

st.markdown("---")

# Input Handling (Based on Step)

if st.session_state.step in [1, 1.5, 2]:
    # --- Step 1, 1.5 (Restart), & 2: Initial Input / Refinement ---
    
    if st.session_state.step == 1:
        prompt_placeholder = "Describe your hardware issue (e.g., My printer won't connect after I updated the OS)."
        handler_func = handle_initial_input
    
    elif st.session_state.step == 1.5:
        prompt_placeholder = "Enter your new, complete problem summary."
        handler_func = handle_initial_input # Use initial handler to restart scoring
        st.session_state.step = 1 # Revert to 1 after setting prompt (a quick hack)

    else: # st.session_state.step == 2
        prompt_placeholder = "Enter your answer to the question."
        handler_func = handle_refinement

    user_input = st.chat_input(prompt_placeholder, key="user_input")
    if user_input:
        handler_func(user_input)

elif st.session_state.step == 2.5:
    # --- NEW: Step 2.5: Confirmation ---
    prompt_placeholder = "Is the problem statement correct? Type 'Yes' or 'No'."
    user_input = st.chat_input(prompt_placeholder, key="confirm_input")
    if user_input:
        handle_confirmation(user_input)

# --- Recommended simpler flow without st.form for step 3 ---
# elif st.session_state.step == 3:
#     st.subheader("Step 3: Diagnostic Checklist")
#     st.markdown("Based on your problem, please select all the likely contributing factors from the list below.")
    
#     selected_causes = st.multiselect(
#         "Select the possible causes for your issue:",
#         options=COMMON_CAUSES,
#         default=[]
#     )
    
#     is_disabled = not bool(selected_causes) 
    
#     if st.button("Submit Checklist & Find Action", type="primary", disabled=is_disabled):
#         handle_checklist_submission(selected_causes)

elif st.session_state.step == 3:
    # --- Step 3: Diagnosis Confirmation (User interacts with form) ---
    st.subheader("Step 3: Confirm Diagnosis")
    st.markdown("Based on the chat, we have identified the most probable cause. Please **review and adjust** the selected causes below.")

    # Get all possible options (COMMON_CAUSES was updated with the new database)
    options_list = sorted(list(COMMON_CAUSES)) 

    with st.form("diagnosis_confirmation_form"):
        
        # Multiselect allows user to change the causes, but defaults to the bot's suggestion
        # The key ensures the selection is saved back to session_state.selected_causes
        st.session_state.selected_causes = st.multiselect(
            "Select ALL potential Root Causes (Adjust the pre-selected option as needed):",
            options=options_list,
            default=st.session_state.selected_causes, 
            key="final_cause_selection" 
        )
        
        st.markdown(f"**Bot's Primary Suggestion:** {st.session_state.suggested_cause}")
        st.info("The primary cause is used to determine the first suggested action.")

        # This button is essential to capture the user's action and move to Step 4
        proceed_button = st.form_submit_button(
            "Confirm Diagnosis and View Suggested Action", 
            type="primary",
            # Requires at least one cause to be selected
            disabled=not st.session_state.selected_causes 
        )

    if proceed_button:
        # User has reviewed and confirmed/adjusted the causes.
        
        # Update chat history with the final action before the form disappears
        update_chat("assistant", 
            f"Diagnosis Confirmed! Your primary issue is still focused on **{st.session_state.suggested_cause}**.\n\n"
            f"**Suggested Action:** {st.session_state.suggested_action}\n\n"
            f"If the issue persists after performing the action, please use the form below to submit a case with the confirmed diagnosis."
        )
        st.session_state.step = 4 # Move to the Case Creation Form
        st.rerun()

elif st.session_state.step == 4:
    # --- Step 4: Case Creation Form ---
    st.subheader("Step 4: Create a Support Case")
    st.markdown("The suggested action has been provided. If the issue persists, please submit the following form to create a formal case with our support team.")

    # 💡 NEW: Placeholder for validation message
    validation_placeholder = st.empty()

    # 💡 NEW: Define the list of causes to display as 'selected'
    # The list contains only the cause identified by the bot.
    # We use a set for the options to ensure the bot's suggested cause is definitely included.
    
    bot_suggested_cause = st.session_state.suggested_cause
    
    # Ensure the full list of options includes the bot's suggestion
    # (Assuming COMMON_CAUSES is a list/set of all possible causes)
    all_available_causes = set(COMMON_CAUSES) 
    all_available_causes.add(bot_suggested_cause)
    
    # Convert the set back to a list for the multiselect options
    options_list = sorted(list(all_available_causes)) 
    
    # The default value is a list containing only the suggested cause
    default_selection = [bot_suggested_cause]

    with st.form("case_creation_form"):
        col1, col2 = st.columns(2)
        
        # Contact Information - HIGHLIGHTED REQUIRED FIELDS
        # Note: Added 'key' and Markdown for visual emphasis
        name = col1.text_input("**Full Name** (Required)", key="case_name")
        email = col2.text_input("**Email Address** (Required)", key="case_email")
        phone = col1.text_input("Phone Number (Optional)")
        product_model = col2.text_input("**Product Model / Device Name** (Required)", key="case_model")
        
        st.markdown("---")
        
        # Issue Summary (Pre-filled)
        st.caption("Final Problem Statement (Refined by the chat):")
        final_statement = st.text_area(
            "Final Problem Statement",
            value=st.session_state.problem_statement,
            height=150,
            disabled=True
        )

        st.caption("Selected Causes:")
        st.multiselect(
            "Selected Causes",
            options=COMMON_CAUSES,
            default=st.session_state.selected_causes,
            disabled=True
        )
        
        st.info(f"**Bot Identified Cause:** {st.session_state.suggested_cause}")

        # Submission Button - ALWAYS ENABLED (disabled=False or omitted)
        submit_case = st.form_submit_button(
            "Submit Case to Human Agent", 
            type="primary", 
            disabled=False # Button is always enabled now
        )

    # 💡 REVISED: Validation logic runs ONLY after the button is clicked
    if submit_case:
        
        required_inputs = {
            "Full Name": name,
            "Email Address": email,
            "Product Model / Device Name": product_model,
        }
        missing_fields = []
        
        for label, value in required_inputs.items():
            # Check if the value is empty or contains only whitespace
            if not value or not value.strip():
                missing_fields.append(label)

        if missing_fields:
            # If fields are missing, display the error message in the placeholder
            error_message = f"**⚠️ Please fill in all required fields to submit the case.** Missing: {', '.join(missing_fields)}"
            validation_placeholder.error(error_message)
            # The form submission itself stops here because we don't call handle_case_submission
        else:
            # If the form is valid, clear any previous error and submit the case
            validation_placeholder.empty()
            form_data = {
                'name': name,
                'email': email,
                'phone': phone,
                'product_model': product_model,
                'problem_statement': final_statement,
                'selected_causes': st.session_state.selected_causes,
                'suggested_cause': st.session_state.suggested_cause
            }
            # This will update the chat history and rerender the final step (Step 5)
            handle_case_submission(form_data)

elif st.session_state.step == 5:
    # --- Step 5: Finished/Reset ---
    st.info("The case has been finalized. Please start a new chat if you have another issue.")
    st.chat_input("Chat is finished. Click 'Start New Chat' in the sidebar.", disabled=True)