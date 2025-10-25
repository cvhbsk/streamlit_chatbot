# 🤖 Streamlit Technical Support Chatbot

## 📝 Project Summary

This project implements a multi-step, **stateful technical support chatbot** using Streamlit. It is designed to efficiently triage hardware issues by guiding the user through a refinement process, automatically diagnosing the root cause using a keyword-based database, suggesting an immediate action, and providing a final form for case escalation to a human agent.

The core goal is to minimize human agent workload by resolving clear issues or collecting complete diagnostic information for complex cases.

---

## ✨ Key Features

* **Stateful Conversation:** Uses Streamlit's `st.session_state` to maintain context across the entire multi-step process.
* **Intelligent Triage Flow:** Adapts the conversation based on the user's initial problem statement.
* **Automatic Diagnosis (Step 3):** Uses a prioritized, keyword-based lookup against a mock `ISSUE_DATABASE` to suggest the most probable cause and action.
* **User Diagnosis Confirmation:** Allows the user to review and adjust the automatically selected root causes via an interactive `st.multiselect`.
* **Case Escalation (Step 4):** A robust form with on-click validation to gather mandatory contact and product details before "submitting" the case.

---

## 🛠️ Setup and Installation

Follow these steps to get a local copy of the project up and running.

### Prerequisites

* Python 3.8+
* `pip` (Python package installer)

### 1. Clone the repository

```bash
git clone <YOUR_REPO_URL>
cd streamlit_project
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

## 🚀 Usage Flow

The application follows a linear, four-step process for problem resolution:

1.  **Initial Input (Step 1):** User describes the hardware issue.
2.  **Refinement/Confirmation (Step 2/2.5):** If the statement is complex, the bot asks follow-up questions. The user confirms the final problem summary.
3.  **Diagnosis Confirmation (Step 3):** The bot displays the most probable **Cause** and pre-selects it in a multiselect. The user can adjust this list of causes before proceeding.
4.  **Case Creation Form (Step 4):** Displays the final suggested action and collects mandatory contact information for case escalation to a human agent.

-----

## ⚙️ Core Logic Details

### State Management

All variables controlling the application flow are stored in `st.session_state`:

| Variable | Purpose |
| :--- | :--- |
| `st.session_state.step` | Controls the current UI state (1, 2, 2.5, 3, 4, 5). |
| `st.session_state.problem_statement`| The continuously refined description of the user's issue. |
| `st.session_state.suggested_cause` | The single primary cause identified by the bot. |

### Diagnosis Logic (`find_best_match_action_by_statement`)

This function uses a **prioritized matching** strategy against the `ISSUE_DATABASE`:

1.  **Critical Check:** It first scans the problem statement for critical hardware failure keywords (e.g., `"no power"`, `"dead"`). If found, it immediately returns the corresponding high-priority diagnosis.
2.  **Score Fallback:** If no critical keywords are found, it uses a score-based match against all other keywords in the database to find the best fit.