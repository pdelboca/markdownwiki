import re

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QTextEdit


class MarkdownEditor(QTextEdit):
    """Widget for editing Markdown content"""

    navigation_requested = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        font = QFont("Courier New", 16, weight=500)
        self.setAcceptRichText(False)
        self.setFont(font)

    def keyPressEvent(self, event):
        """Override keyPressEvent to handle navigation with Ctrl+Enter"""
        if event.key() == Qt.Key_Return and event.modifiers() == Qt.ControlModifier:
            cursor = self.textCursor()
            block = cursor.block()
            line_text = block.text()

            # Check if the line contains a link
            link_match = re.search(r'\[.*?\]\((.*?)\)', line_text)
            if link_match:
                link_target = link_match.group(1)
                self.navigation_requested.emit(link_target)
                return

        # Default handling for other key events
        super().keyPressEvent(event)

