import base64
import io

from docx import Document
from htmldocx import HtmlToDocx
import streamlit as st


def export(notebook_data) -> None:
    """Export the current notebook to a Word (.docx) file.

    Notes are stored as HTML, so we convert the HTML content
    into proper DOCX formatting using htmldocx.
    """
    # Create document in memory
    buffer = io.BytesIO()

    document = Document()
    document.add_heading(notebook_data["title"], level=1)

    # Add video URL as plain text
    video_url = notebook_data["video_url"]
    if video_url:
        document.add_paragraph(f"Video URL: {video_url}")
        document.add_paragraph("")  # blank line

    # Convert HTML notes into DOCX content
    notes_html = notebook_data["notes"] or ""
    if notes_html:
        document.add_paragraph("Notes:")
        parser = HtmlToDocx()
        parser.add_html_to_document(notes_html, document)

    document.save(buffer)
    buffer.seek(0)

    # Convert to Base64 for browser download
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
