import sys
import os
import sqlite3
import datetime
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QPushButton, QLineEdit, QLabel,
    QListWidget, QDialog, QDialogButtonBox, QTextEdit, QListWidgetItem
)

class DatabaseManager:
    def __init__(self):
        self.conn = sqlite3.connect("folders.db")
        self.cursor = self.conn.cursor()
        self.cursor.execute("CREATE TABLE IF NOT EXISTS folders (name TEXT UNIQUE)")
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                folder TEXT,
                title TEXT,
                content TEXT,
                created_at TEXT
            )
        """)
        self.conn.commit()

    def add_folder(self, name):
        try:
            self.cursor.execute("INSERT INTO folders (name) VALUES (?)", (name,))
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def get_folders(self):
        self.cursor.execute("SELECT name FROM folders")
        return [row[0] for row in self.cursor.fetchall()]

    def add_note(self, note):
        self.cursor.execute("""
            INSERT INTO notes (folder, title, content, created_at)
            VALUES (?, ?, ?, ?)
        """, (note["folder"], note["title"], note["content"], note["created_at"]))
        self.conn.commit()

    def update_note(self, note_id, title, content):
        self.cursor.execute("""
            UPDATE notes SET title = ?, content = ? WHERE id = ?
        """, (title, content, note_id))
        self.conn.commit()

    def get_notes(self, folder):
        self.cursor.execute("SELECT id, title, content, created_at FROM notes WHERE folder = ?", (folder,))
        return self.cursor.fetchall()

class AddFolderDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Klasör İsmi Girin")
        self.folder_name = None

        layout = QVBoxLayout()
        self.input = QLineEdit()
        layout.addWidget(QLabel("Klasör İsmi:"))
        layout.addWidget(self.input)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accepted)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.setLayout(layout)

    def accepted(self):
        name = self.input.text().strip()
        if name:
            self.folder_name = name
            self.accept()

class AddNoteDialog(QDialog):
    def __init__(self, folder_name):
        super().__init__()
        self.setWindowTitle("Not Ekle")
        self.folder_name = folder_name
        self.note_data = None

        layout = QVBoxLayout()
        self.title_input = QLineEdit()
        self.content_input = QTextEdit()

        layout.addWidget(QLabel("Not Başlığı:"))
        layout.addWidget(self.title_input)
        layout.addWidget(QLabel("Not İçeriği:"))
        layout.addWidget(self.content_input)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accepted)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.setLayout(layout)

    def accepted(self):
        title = self.title_input.text().strip()
        content = self.content_input.toPlainText().strip()
        if title and content:
            self.note_data = {
                "folder": self.folder_name,
                "title": title,
                "content": content,
                "created_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            self.accept()

class NoteEditorWindow(QWidget):
    def __init__(self, db, note_id, title, content, refresh_callback):
        super().__init__()
        self.setWindowTitle("Notu Düzenle")
        self.setGeometry(300, 300, 400, 300)

        self.db = db
        self.note_id = note_id
        self.refresh_callback = refresh_callback

        layout = QVBoxLayout()

        self.title_input = QLineEdit(title)
        self.content_input = QTextEdit(content)

        self.save_button = QPushButton("Kaydet")
        self.save_button.clicked.connect(self.save_note)

        layout.addWidget(QLabel("Başlık:"))
        layout.addWidget(self.title_input)
        layout.addWidget(QLabel("İçerik:"))
        layout.addWidget(self.content_input)
        layout.addWidget(self.save_button)

        self.setLayout(layout)

    def save_note(self):
        title = self.title_input.text().strip()
        content = self.content_input.toPlainText().strip()
        if title and content:
            self.db.update_note(self.note_id, title, content)
            self.refresh_callback()
            self.close()


class FolderWindow(QWidget):
    def __init__(self, folder_name):
        super().__init__()
        self.setWindowTitle(folder_name)
        self.setGeometry(200, 200, 500, 400)
        self.folder_name = folder_name
        self.db = DatabaseManager()

        self.layout = QVBoxLayout()
        self.note_list = QListWidget()
        self.load_notes()
        self.note_list.itemDoubleClicked.connect(self.open_note_editor)

        self.add_note_btn = QPushButton("Not Ekle")
        self.add_note_btn.clicked.connect(self.add_note)

        self.layout.addWidget(QLabel("Notlar:"))
        self.layout.addWidget(self.note_list)
        self.layout.addWidget(self.add_note_btn)
        self.setLayout(self.layout)

    def load_notes(self):
        self.note_list.clear()
        for id, title, content, created_at in self.db.get_notes(self.folder_name):
            item = QListWidgetItem(f"{title} | {created_at}")
            item.setData(1000, id)
            self.note_list.addItem(item)

    def add_note(self):
        dialog = AddNoteDialog(self.folder_name)
        if dialog.exec_() == QDialog.Accepted and dialog.note_data:
            self.db.add_note(dialog.note_data)
            self.load_notes()

    def open_note_editor(self, item):
        note_id = item.data(1000)
        self.db.cursor.execute("SELECT title, content FROM notes WHERE id = ?", (note_id,))
        row = self.db.cursor.fetchone()
        if row:
            title, content = row
            self.editor = NoteEditorWindow(self.db, note_id, title, content, self.load_notes)
            self.editor.show()

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Notepad Giriş Sayfası")
        self.setGeometry(100, 100, 500, 400)

        self.db = DatabaseManager()
        self.layout = QVBoxLayout()

        self.folder_list = QListWidget()
        self.load_folders()
        self.folder_list.itemClicked.connect(self.open_folder)

        self.add_button = QPushButton("Klasör Ekle")
        self.add_button.clicked.connect(self.add_folder)

        self.layout.addWidget(QLabel("Kayıtlı Klasörler:"))
        self.layout.addWidget(self.folder_list)
        self.layout.addWidget(self.add_button)

        self.setLayout(self.layout)

    def load_folders(self):
        self.folder_list.clear()
        for name in self.db.get_folders():
            self.folder_list.addItem(name)

    def add_folder(self):
        dialog = AddFolderDialog()
        if dialog.exec_() == QDialog.Accepted and dialog.folder_name:
            success = self.db.add_folder(dialog.folder_name)
            if success:
                self.load_folders()
                self.open_folder_by_name(dialog.folder_name)

    def open_folder(self, item):
        self.open_folder_by_name(item.text())

    def open_folder_by_name(self, name):
        self.folder_window = FolderWindow(name)
        self.folder_window.show()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())