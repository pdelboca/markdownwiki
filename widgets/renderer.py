import markdown

from PySide6.QtWidgets import QTextBrowser
from PySide6.QtCore import Signal


class MarkdownRenderer(QTextBrowser):
    """Widget to render Markdown content"""

    navigation_requested = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setOpenLinks(False)  # We'll handle link clicking ourselves
        self.setStyleSheet("""
            MarkdownRenderer {
                background-color: #F5F5F5;
                color: #333333;
                padding: 40px;
                font-family: 'Segoe UI', Arial, sans-serif;
                font-size: 20px;
                margin-left: auto;
                margin-right: auto;
                max-width: 800px; /* Limit width for better readability */
            }
            MarkdownRenderer h1 { font-size: 32px; color: #1a1a1a; margin-top: 24px; margin-bottom: 16px; }
            MarkdownRenderer h2 { font-size: 28px; color: #1a1a1a; margin-top: 22px; margin-bottom: 14px; }
            MarkdownRenderer h3 { font-size: 24px; color: #1a1a1a; margin-top: 20px; margin-bottom: 12px; }
            MarkdownRenderer h4 { font-size: 20px; color: #1a1a1a; margin-top: 18px; margin-bottom: 10px; }
            MarkdownRenderer p { line-height: 1.6; margin-bottom: 16px; }
            MarkdownRenderer a { color: #0078d7; text-decoration: none; }
            MarkdownRenderer a:hover { text-decoration: underline; }
            MarkdownRenderer code { background-color: #f0f0f0; padding: 2px 4px; border-radius: 3px; font-family: 'Courier New', monospace; }
            MarkdownRenderer pre { background-color: #f0f0f0; padding: 10px; border-radius: 5px; font-family: 'Courier New', monospace; overflow-x: auto; }
            MarkdownRenderer blockquote { border-left: 4px solid #cccccc; margin-left: 0; padding-left: 16px; color: #555555; }
            MarkdownRenderer img { max-width: 100%; }
            MarkdownRenderer table { border-collapse: collapse; }
            MarkdownRenderer th, td { border: 1px solid #ddd; padding: 8px; }
            MarkdownRenderer tr:nth-child(even) { background-color: #f2f2f2; }
        """)

        # Connect anchor click event
        self.anchorClicked.connect(self.on_link_clicked)

    def on_link_clicked(self, url):
        """Handle link clicking to navigate to other markdown files"""
        path = url.toString()
        if path.startswith('http://') or path.startswith('https://') or path.startswith('file://'):
            # Do nothing, we only handle relative paths.
            return

        # Emit signal to navigate to the document
        self.navigation_requested.emit(path)

    def render_markdown(self, text):
        """Convert markdown to HTML and display it"""
        # Convert markdown to HTML
        html = markdown.markdown(text, extensions=['extra', 'codehilite', 'tables'])
        html = f"""
        <html>
        <body>
          {html}
        </body>
        </html>
        """
        self.setHtml(html)


