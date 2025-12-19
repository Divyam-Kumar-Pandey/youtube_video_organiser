import io
import base64
from datetime import datetime

import streamlit as st
from streamlit_player import st_player, _SUPPORTED_EVENTS
from st_quill_dark_mode import st_quill_dark_mode

from main.db import (
    init_db,
    get_all_notebooks,
    create_notebook,
    update_notes,
    delete_notebook,
    get_notebook_by_id,
)
from main.export import export

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
    current_data = get_notebook_by_id(selected_notebook_id)

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
        # Constrain notes area height using a scrollable container
        with st.container(height=520, border=False):
            # Quill rich-text editor for notes
            notes_input = st_quill_dark_mode(
                value=current_data["notes"] or "",
                html=True,
                placeholder="Write your notes here...",
                key=f"notes_{selected_notebook_id}",  # Unique key forces reset when switching notebooks
            )

            # Fallback in case the component returns None before first interaction
            if notes_input is None:
                notes_input = current_data["notes"] or ""
            
        # Save Button (Manual Trigger)
        if st.button("Save Notes"):
            update_notes(selected_notebook_id, notes_input, playedSeconds)
            st.toast("Notes saved successfully!")
            
        # Auto-save logic: Check if session state differs from DB
        if notes_input != current_data['notes']:
            update_notes(selected_notebook_id, notes_input, playedSeconds)

else:
    st.empty()