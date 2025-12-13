import streamlit as st
import sqlite3
import pandas as pd
from streamlit_player import st_player, _SUPPORTED_EVENTS
from datetime import datetime
from docx import Document
import io, base64

# --- 1. Database Setup (SQLite) ---
DB_FILE = "notebooks.db"

def init_db():
    """Initialize the database table if it doesn't exist."""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS notebooks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            video_url TEXT,
            notes TEXT,
            progress_time_seconds INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def get_all_notebooks():
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query("SELECT * FROM notebooks ORDER BY created_at DESC", conn)
    conn.close()
    return df

def create_notebook(title, url):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT INTO notebooks (title, video_url, notes, progress_time_seconds) VALUES (?, ?, ?, ?)", 
              (title, url, "", 0))
    conn.commit()
    notebook_id = c.lastrowid
    conn.close()
    return notebook_id

def update_notes(notebook_id, new_notes, progress_time_seconds=0):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("UPDATE notebooks SET notes = ?, progress_time_seconds = ? WHERE id = ?", (new_notes, progress_time_seconds, notebook_id))
    conn.commit()
    conn.close()

def delete_notebook(notebook_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("DELETE FROM notebooks WHERE id = ?", (notebook_id,))
    conn.commit()
    conn.close()

# Initialize DB on first run
init_db()

@st.dialog("Confirm Deletion", on_dismiss='rerun')
def verify_deletion(selected_notebook_id):
    st.write(f"Are you sure you want to delete this notebook?")
    confirmation = st.text_input("Type 'DELETE' to confirm:")
    if confirmation == "DELETE":
        delete_notebook(selected_notebook_id)
        st.rerun()
    return None

def export(notebook_data):
    # Create document in memory
    buffer = io.BytesIO()

    document = Document()
    document.add_heading(notebook_data['title'], level=1)

    text = f"Video URL: {notebook_data['video_url']}\n\nNotes:\n{notebook_data['notes']}"
    document.add_paragraph(text)

    document.save(buffer)
    buffer.seek(0)

    # Convert to Base64
    b64 = base64.b64encode(buffer.read()).decode()

    file_name = f"{notebook_data['title'].replace(' ', '_')}.docx"

    # Auto-trigger download via JS
    download_html = f"""
        <html>
            <body>
                <a id="download_link"
                   href="data:application/vnd.openxmlformats-officedocument.wordprocessingml.document;base64,{b64}"
                   download="{file_name}">
                </a>

                <script>
                    document.getElementById('download_link').click();
                </script>
            </body>
        </html>
    """

    st.components.v1.html(download_html, height=0, width=0)
# --- 2. Streamlit UI Config ---
st.set_page_config(layout="wide", page_title="Video Notebook Manager")

# --- 3. Sidebar: Notebook Management ---
with st.sidebar:
    st.title("📚 Library")
    
    # Mode Selection
    mode = st.radio("Menu", ["Open Notebook", "Create New"], label_visibility="collapsed")
    
    st.divider()

    selected_notebook_id = None
    
  
    df = get_all_notebooks()
    if not df.empty:
        # Create a dictionary for the selectbox: {Title: ID}
        notebook_options = dict(zip(df['title'], df['id']))
        selected_title = st.selectbox("Select a Notebook:", list(notebook_options.keys()))
        selected_notebook_id = notebook_options[selected_title]
    else:
        st.info("No notebooks found. Create one!")

# --- 4. Main Area Logic ---

if mode == "Create New":
    st.header("✨ Create New Notebook")
    with st.form("new_notebook"):
        new_title = st.text_input("Notebook Title", placeholder="e.g., Python Course - Lecture 1")
        new_url = st.text_input("YouTube URL", placeholder="https://youtube.com/...")
        submitted = st.form_submit_button("Create Notebook")
        
        if submitted and new_title and new_url:
            create_notebook(new_title, new_url)
            st.success(f"Created '{new_title}'!")
            st.rerun()

elif mode == "Open Notebook" and selected_notebook_id:
    # Fetch current notebook data
    conn = sqlite3.connect(DB_FILE)
    # We fetch specifically by ID to ensure we get the right one
    current_data = pd.read_sql_query(f"SELECT * FROM notebooks WHERE id = {selected_notebook_id}", conn).iloc[0]
    conn.close()

    # Header with Delete Button
    c1, c2, c3 = st.columns([6, 1, 1], vertical_alignment="bottom")
    c1.title(f"📖 {current_data['title']}")
    if c2.button("Export Word (.docx)", type="secondary"):
        export(current_data)
    if c3.button("Delete Notebook", type="primary"):
        verify_deletion(selected_notebook_id)
            
    # Layout: Video (Left) vs Notes (Right)
    col_video, col_notes = st.columns([2, 1])

    with col_video:
        progressTimeSeconds = int(current_data['progress_time_seconds'])

        options = {
            "events": ["onProgress"],
            "progress_interval": 500,
            "height": 600,
            "playback_rate": 1.5,
            "config": {
                "youtube": {
                    "playerVars": {
                        "start": progressTimeSeconds
                    }
                }
            }
        }
        
        event = st_player(current_data['video_url'], **options, key="youtube_player",)
        playedSeconds = 0
        if event :
            (name, data) = event
            playedSeconds = (data or {}).get("playedSeconds", 0)

    with col_notes:
        st.subheader("Notes")
        # The trick: 'on_change' auto-saves when you click away or press Ctrl+Enter
        notes_input = st.text_area(
            "(Auto-saves on click away or Ctrl+Enter)",
            value=current_data['notes'],
            height=480,
            key=f"notes_{selected_notebook_id}" # Unique key forces reset when switching notebooks
        )
        
        # Save Button (Manual Trigger)
        if st.button("Save Notes"):
            update_notes(selected_notebook_id, notes_input, playedSeconds)
            st.toast("Notes saved successfully!")
            
        # Auto-save logic: Check if session state differs from DB
        if notes_input != current_data['notes']:
            update_notes(selected_notebook_id, notes_input, playedSeconds)

else:
    st.empty()