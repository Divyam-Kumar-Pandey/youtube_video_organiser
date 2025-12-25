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


def import_notebooks_from_db(external_db_path: str) -> dict[str, Any]:
    """Import/append notebooks from another SQLite database file.

    The current DB is NEVER replaced. Instead, rows from the external DB's
    `notebooks` table are appended to the local table.

    Sanity checks performed:
    - File must be a valid SQLite database.
    - Must contain a `notebooks` table.
    - `notebooks` table must have at least the required columns:
      `title`, `video_url`, `notes`, `progress_time_seconds`.

    The `id` column from the external DB is ignored so that new IDs are
    assigned locally. If a `created_at` column is present, it is preserved.

    Returns a summary dict, e.g. {"imported": 5}.
    Raises ValueError with a user-friendly message if the file is not usable.
    """
    # --- 1. Open external DB and basic validation ---
    try:
        src_conn = sqlite3.connect(external_db_path)
    except sqlite3.Error as exc:
        raise ValueError("The uploaded file is not a valid SQLite database.") from exc

    try:
        src_cursor = src_conn.cursor()

        # Check that `notebooks` table exists
        src_cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='notebooks'"
        )
        if src_cursor.fetchone() is None:
            raise ValueError(
                "The database does not contain a 'notebooks' table and "
                "cannot be used for import."
            )

        # Check required columns using PRAGMA table_info
        src_cursor.execute("PRAGMA table_info(notebooks)")
        columns_info = src_cursor.fetchall()
        column_names = {col[1] for col in columns_info}  # col[1] is the column name

        required_columns = {"title", "video_url", "notes", "progress_time_seconds"}
        missing = required_columns - column_names
        if missing:
            missing_str = ", ".join(sorted(missing))
            raise ValueError(
                "The 'notebooks' table is missing required columns: "
                f"{missing_str}. Cannot import from this database."
            )

        # Decide which columns to select from the source
        select_columns = [
            "title",
            "video_url",
            "notes",
            "progress_time_seconds",
        ]
        has_created_at = "created_at" in column_names
        if has_created_at:
            select_columns.append("created_at")

        select_clause = ", ".join(select_columns)
        src_cursor.execute(f"SELECT {select_clause} FROM notebooks")
        rows = src_cursor.fetchall()
    finally:
        src_conn.close()

    if not rows:
        # Nothing to import – not an error, just a no-op
        return {"imported": 0}

    # --- 2. Insert rows into local DB (append only) ---
    dest_conn = sqlite3.connect(DB_FILE)
    try:
        dest_cursor = dest_conn.cursor()

        if has_created_at:
            dest_cursor.executemany(
                """
                INSERT INTO notebooks (
                    title,
                    video_url,
                    notes,
                    progress_time_seconds,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                rows,
            )
        else:
            # Drop any extra columns from the source rows if present, keep order
            trimmed_rows = [
                (r[0], r[1], r[2], r[3])  # title, video_url, notes, progress_time_seconds
                for r in rows
            ]
            dest_cursor.executemany(
                """
                INSERT INTO notebooks (
                    title,
                    video_url,
                    notes,
                    progress_time_seconds
                )
                VALUES (?, ?, ?, ?)
                """,
                trimmed_rows,
            )

        dest_conn.commit()
    finally:
        dest_conn.close()

    return {"imported": len(rows)}
