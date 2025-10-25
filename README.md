# 🤖 Streamlit Technical Support Chatbot

## 📝 Project Summary

This project implements a multi-step, **stateful technical support chatbot** using Streamlit and the Gemini API. It is designed to efficiently triage hardware issues by guiding the user through a problem refinement process, automatically diagnosing the root cause, suggesting immediate actions, and providing a final form for case escalation to a human agent only if the suggested actions fail.

The core goal is to minimize human agent workload by resolving clear issues or collecting complete diagnostic information for complex cases.

---

## ✨ Key Features

*   **Stateful Conversation:** Uses Streamlit's `st.session_state` to maintain context across the entire multi-step process.
*   **LLM-Powered Refinement:** Employs the Gemini API to evaluate the clarity of a user's problem statement and generate targeted follow-up questions if it's too vague.
*   **Automatic Diagnosis:** Uses a prioritized, keyword-based lookup against a mock `ISSUE_DATABASE` to suggest the most probable cause.
*   **Interactive Diagnosis Confirmation:** Allows the user to review and adjust the automatically selected root causes via an interactive `st.multiselect` form.
*   **Comprehensive Action Generation:** Dynamically generates a list of suggested actions based on *all* root causes confirmed by the user.
*   **Resolution Checkpoint:** Explicitly asks the user if the suggested actions resolved the issue before proceeding to case creation, preventing unnecessary escalations.
*   **LLM-Powered Case Summary:** Synthesizes the original problem, user refinements, and confirmed causes into a final, concise case summary for human agents.
*   **Validated Escalation Form:** A robust form with on-click validation to gather mandatory contact and product details before "submitting" the case.

---

## 🛠️ Setup and Installation

Follow these steps to get a local copy of the project up and running.

### Prerequisites

* Python 3.8+
* `pip` (Python package installer)

### 1. Clone the repository

```bash
git clone <YOUR_REPO_URL>
cd streamlit_chatbot
````

### 2\. Create and activate a virtual environment

It's highly recommended to use a virtual environment for dependency management.

```bash
python -m venv .venv
source .venv/bin/activate  # On Linux/macOS
.venv\Scripts\activate     # On Windows
```

### 3\. Install dependencies

Install the necessary libraries from your `requirements.txt`:

```bash
pip install -r requirements.txt
```

### 4\. Configure Gemini API Key

This application uses the Gemini API for its core logic. You must set up your API key securely using Streamlit's secrets management.

1.  Create a folder named **`.streamlit`** in your project's root directory if it doesn't already exist.

2.  Inside the **`.streamlit`** folder, create a file named **`secrets.toml`**.

3.  Add the following lines to `secrets.toml`, **replacing the entire placeholder value** with your actual API key:

    ```toml
    # .streamlit/secrets.toml
    GEMINI_API_KEY="UPDATEYOURAPIKEY" # <--- UPDATE THIS VALUE
    ```

### 5\. Run the application

Execute the main application file:

```bash
streamlit run app.py
```

The application will open automatically in your web browser (usually at `http://localhost:8501`).

-----

## 🚀 Application Flow

The application follows a conditional, multi-step process for problem resolution:

1.  **Initial Input (Step 1):** User describes the hardware issue.
    *   **If the statement is clear:** The bot skips to Step 3.
    *   **If the statement is vague:** The bot proceeds to Step 2.
2.  **Refinement & Confirmation (Steps 2 & 2.5):** The bot asks a series of LLM-generated follow-up questions. After gathering details, it presents a synthesized summary for user confirmation ('Yes'/'No').
3.  **Diagnosis Confirmation (Step 3):** The bot displays the most probable **Cause** and pre-selects it in a multiselect form. The user can add or remove causes from this list and confirm their selection.
4.  **Resolution Check (Step 3.5):** The bot presents a final case summary and a comprehensive list of suggested actions based on all confirmed causes. The user is prompted to try these actions and report the outcome.
    *   **If the issue is resolved:** The chat ends successfully (Step 5).
    *   **If the issue persists:** The user is directed to the final escalation step.
5.  **Case Creation Form (Step 4):** A form appears, pre-filled with the final case summary. The user must provide contact and product details to submit the case to a human agent.
6.  **Submission Complete (Step 5):** The bot confirms case creation and the chat is closed.

-----

## ⚙️ Core Logic Details

### State Management

All variables controlling the application flow and conversation history are stored in `st.session_state`:

| Variable | Purpose |
| :--- | :--- |
| `st.session_state.step` | Controls the current UI state (1, 1.5, 2, 2.5, 3, 3.5, 4, 5). |
| `st.session_state.problem_statement`| The continuously refined description of the user's issue. |
| `st.session_state.suggested_cause` | The single primary cause identified by the keyword-based diagnosis. |
| `st.session_state.selected_causes` | A list of all causes confirmed by the user in the Step 3 multiselect form. |
| `st.session_state.suggested_action` | A comprehensive string of all actions corresponding to the `selected_causes`. |

### Diagnosis Logic (`find_best_match_action_by_statement`)

This function uses a **prioritized matching** strategy against the `ISSUE_DATABASE`:

1.  **Critical Check:** It first scans the problem statement for critical hardware failure keywords (e.g., `"no power"`, `"dead"`). If found, it immediately returns the corresponding high-priority diagnosis.
2.  **Score Fallback:** If no critical keywords are found, it uses a score-based match against all other keywords in the database to find the best fit.