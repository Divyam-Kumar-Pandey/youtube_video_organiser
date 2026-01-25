import io
import base64
import json
import os
import tempfile
from urllib.parse import parse_qs, quote, urlparse
from urllib.request import urlopen
from datetime import datetime

import streamlit as st
from streamlit_player import st_player, _SUPPORTED_EVENTS
from st_quill_dark_mode import st_quill_dark_mode

from main.db import (
    DB_FILE,
    init_db,
    get_all_notebooks,
    create_notebook,
    update_title,
    update_notes,
    delete_notebook,
    get_notebook_by_id,
    import_notebooks_from_db,
)
from main.export import export

# --- YouTube helpers ---
def extract_youtube_video_id(url: str) -> str | None:
    if not url:
        return None

    parsed = urlparse(url.strip())
    host = (parsed.netloc or "").lower()
    path = (parsed.path or "").strip("/")

    if host in {"youtu.be", "www.youtu.be"}:
        return path.split("/")[0] if path else None

    if host.endswith("youtube.com"):
        if parsed.path == "/watch":
            query = parse_qs(parsed.query)
            return (query.get("v") or [None])[0]
        if path.startswith("embed/"):
            return path.split("/")[1] if len(path.split("/")) > 1 else None

    return None


def normalize_youtube_url(url: str) -> str | None:
    video_id = extract_youtube_video_id(url)
    if not video_id:
        return None
    return f"https://www.youtube.com/watch?v={video_id}"


def fetch_youtube_title(url: str) -> str | None:
    if not url:
        return None

    oembed_url = f"https://www.youtube.com/oembed?url={quote(url)}&format=json"
    try:
        with urlopen(oembed_url, timeout=5) as response:
            data = json.loads(response.read().decode("utf-8"))
        return data.get("title")
    except Exception:
        return None

# Initialize DB on first run
init_db()

@st.dialog("Confirm Deletion", on_dismiss='rerun')
def verify_deletion(selected_notebook_id):
    st.write(f"Are you sure you want to delete this notebook?")
    confirmation = st.text_input("Type 'DELETE' to confirm:", autocomplete="off")
    if confirmation == "DELETE":
        delete_notebook(selected_notebook_id)
        st.rerun()
    return None


@st.dialog("Rename Notebook", on_dismiss="rerun")
def rename_notebook_dialog(selected_notebook_id: int, current_title: str) -> None:
    """Modal dialog to edit a notebook title."""
    new_title = st.text_input(
        "Notebook title",
        value=current_title,
        key=f"rename_title_{selected_notebook_id}",
    )

    col_save, col_cancel = st.columns(2, gap="large", vertical_alignment="center", width="stretch")
    with col_save:
        if st.button("Save", type="primary", key=f"save_rename_{selected_notebook_id}", use_container_width=True):
            if new_title and new_title.strip() and new_title != current_title:
                update_title(selected_notebook_id, new_title.strip())
                st.rerun()
                st.toast("Title updated.")
    with col_cancel:
        if st.button("Cancel", key=f"cancel_rename_{selected_notebook_id}", use_container_width=True):
            st.rerun()

# --- 2. Streamlit UI Config ---
st.set_page_config(layout="wide", page_icon=":notebook:", page_title="Video Notebook Manager")

# --- 3. Sidebar: Notebook Management ---
with st.sidebar:
    st.title("📚 Library")
    
    # Mode Selection
    mode = st.radio(
        "Menu",
        ["Open Notebook", "Create New", "Import / Export data"],
        label_visibility="collapsed",
    )
    
    st.divider()

    selected_notebook_id = None
    
  
    # Only load and show notebooks list when not in import/export mode
    if mode != "Import / Export data":
        df = get_all_notebooks()
        if not df.empty:
            # Create a dictionary for the selectbox: {Title: ID}
            notebook_options = dict(zip(df['title'], df['id']))
            selected_title = st.selectbox(
                "Select a Notebook:", list(notebook_options.keys())
            )
            selected_notebook_id = notebook_options[selected_title]
        else:
            st.info("No notebooks found. Create one or import from another DB.")

# --- 4. Main Area Logic ---

if mode == "Create New":
    st.header("✨ Create New Notebook")

    if "new_title_auto" not in st.session_state:
        st.session_state["new_title_auto"] = ""

    def update_title_from_url() -> None:
        raw_url = st.session_state.get("new_video_url", "").strip()
        normalized_url = normalize_youtube_url(raw_url)
        if not normalized_url:
            return

        title = fetch_youtube_title(normalized_url)
        if not title:
            return

        current_title = st.session_state.get("new_title", "")
        last_auto = st.session_state.get("new_title_auto", "")
        if not current_title or current_title == last_auto:
            st.session_state["new_title"] = title
            st.session_state["new_title_auto"] = title

    new_url = st.text_input(
        "YouTube URL",
        placeholder="https://youtube.com/...",
        key="new_video_url",
        on_change=update_title_from_url,
    )

    with st.form("new_notebook", clear_on_submit=True):
        new_title = st.text_input(
            "Notebook Title",
            placeholder="e.g., Python Course - Lecture 1",
            key="new_title",
        )
        submitted = st.form_submit_button("Create Notebook")

        if submitted:
            normalized_url = normalize_youtube_url(new_url)
            if not normalized_url:
                st.error("Please enter a valid YouTube URL.")
            elif not new_title or not new_title.strip():
                st.error("Please enter a notebook title.")
            else:
                create_notebook(new_title.strip(), normalized_url)
                st.success(f"Created '{new_title.strip()}'!")
                st.session_state["new_title_auto"] = ""
                st.rerun()

elif mode == "Import / Export data":
    st.header("📥 Import / Export data")

    import_tab, export_tab = st.tabs(["Import from DB", "Export data"])

    # --- Import Tab ---
    with import_tab:
        st.subheader("Import notebooks from SQLite DB")
        st.write(
            "Upload a SQLite database file created by this app. "
            "Its `notebooks` table will be **appended** to your current library; "
            "your existing data will not be replaced."
        )

        uploaded_file = st.file_uploader(
            "SQLite database file",
            type=["db", "sqlite", "sqlite3"],
            help="Select a .db / .sqlite file that was exported or copied from another instance of this app.",
        )

        if uploaded_file is not None:
            st.caption(
                f"Selected file: `{uploaded_file.name}` "
                f"({uploaded_file.size / 1024:.1f} KB)"
            )

            if st.button("Start Import", type="primary"):
                # Persist the uploaded file to a temporary path for sqlite3 to read
                tmp_path = None
                try:
                    with tempfile.NamedTemporaryFile(
                        delete=False, suffix=".db"
                    ) as tmp_file:
                        tmp_file.write(uploaded_file.getbuffer())
                        tmp_path = tmp_file.name

                    try:
                        result = import_notebooks_from_db(tmp_path)
                    except ValueError as exc:
                        st.error(str(exc))
                    except Exception:
                        st.error(
                            "An unexpected error occurred while importing the database."
                        )
                    else:
                        imported = int(result.get("imported", 0))
                        if imported > 0:
                            st.success(f"Successfully imported {imported} notebooks.")
                            st.toast("Import completed successfully.")
                        else:
                            st.info(
                                "The database was valid but did not contain any notebooks "
                                "to import."
                            )
                finally:
                    if tmp_path and os.path.exists(tmp_path):
                        try:
                            os.remove(tmp_path)
                        except OSError:
                            # Not fatal – just log silently
                            pass

    # --- Export Tab ---
    with export_tab:
        st.subheader("Export current data")
        st.write(
            "Download a copy of your current SQLite database file. "
            "You can later import this file into another instance of the app."
        )

        if not os.path.exists(DB_FILE):
            st.warning(
                "The database file could not be found. "
                "Try creating a notebook first and then refresh the page."
            )
        else:
            try:
                with open(DB_FILE, "rb") as f:
                    db_bytes = f.read()
            except OSError:
                st.error("Could not read the database file for export.")
            else:
                st.download_button(
                    "Download database file",
                    data=db_bytes,
                    file_name=DB_FILE,
                    mime="application/octet-stream",
                )

elif mode == "Open Notebook" and selected_notebook_id:
    # Fetch current notebook data
    current_data = get_notebook_by_id(selected_notebook_id)

    # Header with large title, inline edit trigger, export and delete buttons
    header_left, header_export, header_delete = st.columns(
        [8, 1, 1], vertical_alignment="bottom"
    )

    with header_left:
        title_col, icon_col = st.columns([12, 1], vertical_alignment="bottom")

        with title_col: 
            # Use native title styling for the notebook name
            st.title(f"📖 {current_data['title']}", anchor=False, width="content")

        # Small pencil icon that opens the rename dialog
        pencil_clicked = icon_col.button(
            "✏️",
            key=f"pencil_btn_{selected_notebook_id}",
            help="Rename this notebook",
        )

        if pencil_clicked:
            rename_notebook_dialog(selected_notebook_id, current_data["title"])

    if header_export.button("Export notes", type="secondary"):
        export(current_data)
    if header_delete.button("Delete Notebook", type="primary"):
        verify_deletion(selected_notebook_id)
            
    # Layout: Video (Left) vs Notes (Right)
    col_video, col_notes = st.columns([2, 1])

    with col_video:
        progressTimeSeconds = int(current_data['progress_time_seconds'])
        video_url = normalize_youtube_url(current_data["video_url"]) or current_data["video_url"]

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
        
        event = st_player(video_url, **options, key="youtube_player",)
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