# Juthoor 🌳

Juthoor is an interactive, adaptive learning platform built using Python and Streamlit. It leverages knowledge graphs to map out curriculums, provides dynamic skill tree visualizations, and features an adaptive practice engine that tailors the learning experience to the user.

## Features

*   **Interactive App:** Built on Streamlit for a seamless, responsive web experience.
*   **Knowledge Graph & Curriculum:** Uses `networkx` to structure, visualize, and track educational progress through interconnected topics.
*   **Adaptive Learning Engine:** Dynamically adjusts practice difficulty and content based on user performance.
*   **Custom Skill Trees:** Features custom-built UI components (`jt_tree`) to render interactive learning paths.
*   **Gamification & Avatars:** Users can customize their profiles with distinct avatars and unlockable items.
*   **Offline Question Bank:** Robust local storage of practice questions and prompts.

## Project Structure

*   `app.py`: Main entry point for the Streamlit application.
*   `adaptive_engine.py`: Logic for the adaptive learning algorithms.
*   `knowledge_graph.py` & `curriculum.py`: Data models and structures for the learning paths.
*   `tree_view.py` & `tree_component.py`: Logic and integration for the custom skill tree visualizations.
*   `practice.py` & `offline_bank.py`: Practice session logic and local question storage.
*   `avatar.py` & `avatar_items.py`: User profile and gamification elements.
*   `theme.py`, `svgkit.py`, `brand.py`: Styling, branding, and custom visual assets.
*   `components/jt_tree/`: Custom HTML/JS components for rendering the interactive tree.

## Prerequisites

Make sure you have Python 3.8+ installed on your system. 

## Installation

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd Juthoor-main
   ```

2. **Install the required dependencies:**
   The project relies on Streamlit and NetworkX. Install them via the provided requirements file:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

To start the application, run the following command in your terminal:

```bash
streamlit run app.py
```

The app will open automatically in your default web browser (typically at `http://localhost:8501`).

## Dependencies

*   `streamlit >= 1.37`
*   `networkx`
