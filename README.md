**Video Notes App**

A small Streamlit app to create and manage video-linked notebooks. Use it to attach notes to YouTube videos, play videos in the app, and save playback progress alongside your notes.

**Features**
- **Create Notebook**: Add a notebook with a title and a YouTube URL.
- **Play Video**: Watch videos inside the app using `streamlit-player`.
- **Take Notes**: Rich text area for notes saved to the local SQLite DB.
- **Progress Save**: Saves playback progress (seconds) alongside notes.
- **Delete**: Remove notebooks you no longer need.

**Requirements**
- **Python**: 3.10 or newer recommended.
- **Main packages**: `streamlit`, `streamlit-player`, `pandas` (install steps below).
- **Database**: Uses SQLite (`notebooks.db`) — no separate DB server required.

**Installation**
1. Clone the repository (if not already):

```bash
git clone <your-repo-url>
cd video-notes-app
```

2. Create and activate a virtual environment (recommended):

```bash
python3 -m venv .venv
source .venv/bin/activate
```

3. Dependencies are handled by the project's `uv` build system. Use your normal `uv` workflow to build or install dependencies before running the app.

**Run the app**

Start the Streamlit app with:

```bash
streamlit run app.py
```

Then open `http://localhost:8501` (or follow the URL printed by Streamlit) in your browser.

**Usage**
- Open the sidebar to create a new notebook or select an existing one.
- When creating, provide a title and a YouTube URL.
- The video appears on the left; notes are on the right.
- Notes are auto-saved when changed and you can also click the `💾 Save Notes` button.
- Playback progress (seconds) is stored in the DB and used as the player's start time.

**Data / Database**
- The app uses a local SQLite file named `notebooks.db` in the project root.
- The database is created automatically on first run by `app.py`.
- To reset all data, stop the app and delete `notebooks.db`.

**Troubleshooting**
- If the video doesn't play, verify the URL is a public YouTube link.
- If `streamlit-player` events (progress/time) don't update, try a different browser or update the `streamlit-player` package.
- If Streamlit reports missing packages, ensure your virtualenv is activated and packages installed.

**Development notes**
- Main app file: `app.py`.
- DB file: `notebooks.db` (auto-created).
- The UI uses `streamlit_player` to capture playback `onProgress` events.



