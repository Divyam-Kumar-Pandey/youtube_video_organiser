import sqlite3
from typing import Any

import pandas as pd


DB_FILE = "notebooks.db"


def init_db() -> None:
    """Initialize the database table if it doesn't exist."""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS notebooks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            video_url TEXT,
            notes TEXT,
            progress_time_seconds INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.commit()
    conn.close()


def get_all_notebooks() -> pd.DataFrame:
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query(
        "SELECT * FROM notebooks ORDER BY created_at DESC", conn
    )
    conn.close()
    return df


def create_notebook(title: str, url: str) -> int:
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute(
        "INSERT INTO notebooks (title, video_url, notes, progress_time_seconds) VALUES (?, ?, ?, ?)",
        (title, url, "", 0),
    )
    conn.commit()
    notebook_id = c.lastrowid
    conn.close()
    return int(notebook_id)


def update_notes(notebook_id: int, new_notes: str, progress_time_seconds: int = 0) -> None:
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute(
        "UPDATE notebooks SET notes = ?, progress_time_seconds = ? WHERE id = ?",
        (new_notes, progress_time_seconds, notebook_id),
    )
    conn.commit()
    conn.close()


def delete_notebook(notebook_id: int) -> None:
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("DELETE FROM notebooks WHERE id = ?", (notebook_id,))
    conn.commit()
    conn.close()


def get_notebook_by_id(notebook_id: int) -> pd.Series:
    """Return a single notebook row as a pandas Series.

    Raises ValueError if the notebook does not exist.
    """
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query(
        "SELECT * FROM notebooks WHERE id = ?",
        conn,
        params=(notebook_id,),
    )
    conn.close()

    if df.empty:
        raise ValueError(f"Notebook with id {notebook_id} not found")

    # Return first (and only) row as Series
    return df.iloc[0]
