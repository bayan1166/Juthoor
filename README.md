# Juthoor 🌱

Juthoor is an adaptive educational platform built with Streamlit and NetworkX. It features an intelligent adaptive engine, interactive skill trees, and a robust offline learning bank to gamify the educational experience.

## Features
* **Adaptive Learning Engine:** Dynamically adjusts difficulty based on performance metrics.
* **Knowledge Graphs & Skill Trees:** Visualizes progression and prerequisites using NetworkX.
* **LLM Remediation:** AI-driven assistance for debugging and targeted learning support.
* **Avatar System:** Gamified user profiles with unlockable customization items.
* **Offline Bank:** Local caching of practice problems for continuous learning without an active connection.

## Quickstart (WSL / Linux) 🚀

### 1. Clone & Navigate
If you are setting this up for the first time, clone the repository and navigate into the project directory:
```bash
git clone [https://github.com/bayan1166/juthoor.git](https://github.com/bayan1166/juthoor.git)
cd juthoor
```

### 2. Setup Virtual Environment
Create and activate an isolated Python environment:
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies
Install the core application requirements, followed by the optional dependencies for the LLM remediation features:
```bash
pip install --upgrade pip
pip install -r requirements.txt
pip install -r requirements-optional.txt
```

### 4. Run the Application
Start the application using Streamlit:
```bash
streamlit run app.py
```
Open `http://localhost:8501` in your Windows web browser to view the application.

## Project Structure 📁
* `.streamlit/` - Streamlit UI theming and server configuration settings.
* `app.py` - Core Streamlit application entry point and main UI layout.
* `adaptive_engine.py` - Algorithm and logic for the dynamic learning component.
* `knowledge_graph.py` & `tree_view.py` - NetworkX graph traversal and visual rendering logic.
* `llm_remediation.py` - AI integration for automated user guidance and feedback.
* `offline_bank.py` - Caching architecture for offline problem sets.
* `avatar.py` & `avatar_items.py` - Logic and assets for user profile gamification.
