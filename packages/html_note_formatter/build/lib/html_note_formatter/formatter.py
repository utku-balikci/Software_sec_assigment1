import html

def format_note_html(note_id: int, title: str, content: str, author: str) -> str:
    """Format note content into a clean HTML document."""
    escaped_title = html.escape(title)
    escaped_content = html.escape(content).replace("\n", "<br/>")
    escaped_author = html.escape(author)
    
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Note Export: {escaped_title}</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; margin: 40px; background: #fdfdfd; color: #222; }}
        .note-card {{ border: 1px solid #e1e4e8; border-radius: 8px; padding: 24px; max-width: 600px; margin: 0 auto; box-shadow: 0 4px 6px rgba(0,0,0,0.05); background: #ffffff; }}
        .header {{ border-bottom: 1px solid #eaecef; padding-bottom: 12px; margin-bottom: 16px; }}
        .title {{ margin: 0 0 8px 0; color: #0366d6; }}
        .meta {{ font-size: 0.85em; color: #586069; }}
        .body {{ line-height: 1.6; font-size: 1.05em; }}
    </style>
</head>
<body>
    <div class="note-card">
        <div class="header">
            <h1 class="title">{escaped_title}</h1>
            <div class="meta">Note ID: #{note_id} | Author: <strong>{escaped_author}</strong></div>
        </div>
        <div class="body">
            <p>{escaped_content}</p>
        </div>
    </div>
</body>
</html>"""
