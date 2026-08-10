import sys
import ctypes
from datetime import datetime

from PyQt6.QtWidgets import (
    QApplication, QWidget, QGridLayout, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QListWidget, QListWidgetItem, QPushButton, QGroupBox, QTextEdit,
    QRadioButton, QSpinBox, QButtonGroup, QDialog
)
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QKeySequence, QShortcut, QIcon
from storage import load_data, save_data, TaskItem

try:
    myappid = 'ivynode.workspace.v1'
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
except Exception:
    pass


class PlainTextEdit(QTextEdit):
    """QTextEdit variant that forces pasted content to be plain text."""

    def insertFromMimeData(self, source):
        if source.hasText():
            self.insertPlainText(source.text())
        else:
            super().insertFromMimeData(source)


class RetroNodeBox(QGroupBox):
    def __init__(self, title: str):
        super().__init__(title)
        self.box_layout = QVBoxLayout(self)
        self.box_layout.setContentsMargins(10, 14, 10, 10)


class SettingsDialog(QDialog):
    """Personal Settings Dialog with theme toggling."""

    def __init__(self, parent=None, current_theme="dark"):
        super().__init__(parent)
        self.setWindowTitle("Personal Settings")
        self.resize(340, 180)
        self.parent_window = parent
        self.pending_theme = current_theme

        layout = QVBoxLayout(self)

        self.lbl_title = QLabel("Theme Preferences")
        self.lbl_toggle_theme = QLabel()
        self.lbl_toggle_theme.setCursor(Qt.CursorShape.PointingHandCursor)
        self.lbl_toggle_theme.mousePressEvent = lambda event: self.toggle_theme_state()

        self.lbl_hint = QLabel("Press [T] to Toggle | Press [Enter] to Apply & Close")
        self.btn_apply = QPushButton("[ENTER] Apply Changes")
        self.btn_apply.clicked.connect(self.apply_and_close)

        layout.addWidget(self.lbl_title)
        layout.addWidget(self.lbl_toggle_theme)
        layout.addWidget(self.lbl_hint)
        layout.addStretch()
        layout.addWidget(self.btn_apply)

        # Shortcuts
        QShortcut(QKeySequence("T"), self, self.toggle_theme_state)
        QShortcut(QKeySequence("Return"), self, self.apply_and_close)
        QShortcut(QKeySequence("Enter"), self, self.apply_and_close)
        QShortcut(QKeySequence("Escape"), self, self.reject)

        self.update_toggle_text()
        self.apply_dialog_theme(current_theme)

    def toggle_theme_state(self):
        self.pending_theme = "light" if self.pending_theme == "dark" else "dark"
        self.update_toggle_text()
        self.apply_dialog_theme(self.pending_theme)

    def update_toggle_text(self):
        next_mode = "Light" if self.pending_theme == "light" else "Dark"
        self.lbl_toggle_theme.setText(f"[T] Enable {next_mode} Mode")

    def apply_and_close(self):
        self.parent_window.apply_theme(self.pending_theme)
        self.accept()

    def apply_dialog_theme(self, theme_mode):
        colors = {
            "light": {"bg": "#F1EAD8", "text": "#2A332A", "btn_bg": "#588157", "btn_text": "#FFFFFF"},
            "dark": {"bg": "#1e241e", "text": "#d8e2dc", "btn_bg": "#588157", "btn_text": "#ffffff"}
        }[theme_mode]

        self.setStyleSheet(f"background-color: {colors['bg']};")
        self.lbl_title.setStyleSheet(
            f"font-weight: bold; font-size: 14px; color: {colors['text']}; background-color: transparent;")
        self.lbl_toggle_theme.setStyleSheet(
            f"font-weight: bold; font-size: 13px; color: {colors['text']}; background-color: transparent; padding: 4px 0px;")
        self.lbl_hint.setStyleSheet(
            f"color: {colors['text']}; font-size: 11px; font-style: italic; background-color: transparent;")

        self.btn_apply.setStyleSheet(f"""
            QPushButton {{
                background-color: {colors['btn_bg']}; color: {colors['btn_text']}; 
                font-weight: bold; padding: 6px; border-radius: 4px; border: 1px solid #588157;
            }}
            QPushButton:hover {{ background-color: #3a5a40; }}
        """)


class TaskInspectorDialog(QDialog):
    """Sub-task and Detailed Task Inspector Pop-up."""

    def __init__(self, parent, task_title, task_data):
        super().__init__(parent)
        self.setWindowTitle(f"Task Inspector - {task_title}")
        self.resize(420, 380)
        self.parent_window = parent
        self.task_title = task_title
        self.task_data = task_data

        layout = QVBoxLayout(self)

        self.lbl_header = QLabel(f"Task: <b>{task_title}</b>")
        layout.addWidget(self.lbl_header)

        # Status & Toggle Action Buttons
        status_layout = QHBoxLayout()
        self.lbl_status = QLabel(f"Status: {'[Completed]' if task_data.get('completed') else '[In Progress]'}")
        self.btn_toggle_done = QPushButton(
            "[T] Mark Completed" if not task_data.get('completed') else "[T] Mark In Progress")
        self.btn_toggle_done.clicked.connect(self.toggle_task_status)
        status_layout.addWidget(self.lbl_status)
        status_layout.addStretch()
        status_layout.addWidget(self.btn_toggle_done)
        layout.addLayout(status_layout)

        # Sub-tasks List
        layout.addWidget(QLabel("Sub-tasks & Descriptions:"))
        self.subtask_list = QListWidget()
        self.reload_subtasks_list()
        layout.addWidget(self.subtask_list)

        # Sub-task Title & Description Input
        sub_input_layout = QVBoxLayout()
        self.subtask_title_input = QLineEdit()
        self.subtask_title_input.setPlaceholderText("[A] Focus Title | Enter Sub-task Title...")
        self.subtask_title_input.returnPressed.connect(self.add_subtask)

        self.subtask_desc_input = QLineEdit()
        self.subtask_desc_input.setPlaceholderText("Sub-task Description & press Enter to Save...")
        self.subtask_desc_input.returnPressed.connect(self.add_subtask)

        sub_input_layout.addWidget(self.subtask_title_input)
        sub_input_layout.addWidget(self.subtask_desc_input)
        layout.addLayout(sub_input_layout)

        # Bottom Actions
        actions_layout = QHBoxLayout()
        self.btn_delete_task = QPushButton("[D] Delete Task")
        self.btn_delete_task.setStyleSheet(
            "background-color: #a34848; color: white; font-weight: bold; border-radius: 4px; padding: 4px;")
        self.btn_delete_task.clicked.connect(self.delete_task)

        self.btn_close = QPushButton("[C] Close")
        self.btn_close.clicked.connect(self.accept)

        actions_layout.addWidget(self.btn_delete_task)
        actions_layout.addStretch()
        actions_layout.addWidget(self.btn_close)
        layout.addLayout(actions_layout)

        # Keybindings
        QShortcut(QKeySequence("D"), self, self.delete_task)
        QShortcut(QKeySequence("T"), self, self.toggle_task_status)
        QShortcut(QKeySequence("A"), self, self.focus_subtask_input)
        QShortcut(QKeySequence("C"), self, self.accept)
        QShortcut(QKeySequence("Escape"), self, self.unfocus_or_close)

        self.apply_theme(parent.current_theme)

    def reload_subtasks_list(self):
        self.subtask_list.clear()
        for sub in self.task_data.get("subtasks", []):
            if isinstance(sub, dict):
                title, desc = sub.get("title", ""), sub.get("desc", "")
                display = f"• {title}" + (f" - {desc}" if desc else "")
            else:
                display = f"• {sub}"
            self.subtask_list.addItem(display)

    def focus_subtask_input(self):
        if not self.subtask_title_input.hasFocus() and not self.subtask_desc_input.hasFocus():
            self.subtask_title_input.setFocus()

    def unfocus_or_close(self):
        if self.subtask_title_input.hasFocus() or self.subtask_desc_input.hasFocus():
            self.setFocus()
        else:
            self.reject()

    def add_subtask(self):
        title = self.subtask_title_input.text().strip()
        desc = self.subtask_desc_input.text().strip()
        if title:
            self.task_data.setdefault("subtasks", []).append({"title": title, "desc": desc})
            self.reload_subtasks_list()
            self.subtask_title_input.clear()
            self.subtask_desc_input.clear()
            self.subtask_title_input.setFocus()
            self.parent_window.update_active_task_display()
            self.parent_window.reload_task_manager_list()

    def toggle_task_status(self):
        is_completed = not self.task_data.get("completed", False)
        self.task_data["completed"] = is_completed
        self.lbl_status.setText(f"Status: {'[Completed]' if is_completed else '[In Progress]'}")
        self.btn_toggle_done.setText("[T] Mark In Progress" if is_completed else "[T] Mark Completed")
        self.parent_window.reload_task_manager_list()

    def delete_task(self):
        self.parent_window.remove_task(self.task_title)
        self.accept()

    def apply_theme(self, theme_mode):
        c = {
            "light": {"bg": "#F1EAD8", "text": "#2A332A", "input": "#FAF6ED", "sel_bg": "#588157"},
            "dark": {"bg": "#1e241e", "text": "#d8e2dc", "input": "#2a332a", "sel_bg": "#3a5a40"}
        }[theme_mode]

        self.setStyleSheet(f"background-color: {c['bg']}; color: {c['text']};")
        self.subtask_list.setStyleSheet(f"""
            QListWidget {{ background-color: {c['input']}; color: {c['text']}; border: 1px solid #588157; }}
            QListWidget::item:selected {{ background-color: {c['sel_bg']}; color: #ffffff; font-weight: bold; }}
        """)

        input_style = f"background-color: {c['input']}; color: {c['text']}; border: 1px solid #588157; padding: 3px;"
        self.subtask_title_input.setStyleSheet(input_style)
        self.subtask_desc_input.setStyleSheet(input_style)

        btn_style = "background-color: #588157; color: white; font-weight: bold; padding: 4px;"
        self.btn_toggle_done.setStyleSheet(btn_style)
        self.btn_close.setStyleSheet(btn_style)


class IvyNodeWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("IvyNode Workspace")
        self.resize(1100, 750)
        self.setMinimumSize(950, 620)
        self.setWindowIcon(QIcon("leaf.png"))

        self.state = load_data()
        self.active_tasks = []
        self.max_active_tasks = 3

        self.task_details = {}
        self.show_task_subtasks = False

        self.timer_running = False
        self.timer_mode = "countdown"
        self.time_seconds = 1500

        self.journal_entries = []
        self.current_journal_idx = None
        self.max_journal_logs = 30
        self.max_word_count = 500
        self.current_theme = "dark"

        self.init_ui()
        self.setup_shortcuts()
        self.apply_theme("dark")

    def init_ui(self):
        grid = QGridLayout(self)
        grid.setSpacing(10)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 3)
        grid.setColumnStretch(2, 2)

        # 1. LEFT COLUMN: Weather, Profile & MENU
        left_layout = QVBoxLayout()
        left_layout.setSpacing(8)

        self.weather_box = RetroNodeBox("Date, Time & Weather")
        self.lbl_live_clock = QLabel("Time: --:--:--")
        self.lbl_live_clock.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_live_clock.setStyleSheet("font-weight: bold; font-size: 13px;")
        self.lbl_weather = QLabel("⛅ Manila, PH: 28°C Partly Cloudy")
        self.lbl_weather.setAlignment(Qt.AlignmentFlag.AlignCenter)

        weather_l = QVBoxLayout()
        weather_l.addWidget(self.lbl_live_clock)
        weather_l.addWidget(self.lbl_weather)
        self.weather_box.box_layout.addLayout(weather_l)

        self.profile_box = RetroNodeBox("User Profile")
        self.lbl_user = QLabel("User: Default User")
        self.profile_box.box_layout.addWidget(self.lbl_user)

        self.sidebar_box = RetroNodeBox("MENU")
        shortcuts_info = [
            "<b>[A]</b> Focus Task Input", "<b>[Z]</b> Task Manager Focus",
            "<b>[V]</b> View Task / Sub-tasks", "<b>[H]</b> Show/Hide Sub-tasks",
            "<b>[S]</b> Open Settings", "<b>[Space]</b> Timer", "<b>[Esc]</b> Unfocus"
        ]
        for info in shortcuts_info:
            self.sidebar_box.box_layout.addWidget(QLabel(info))
        self.sidebar_box.box_layout.addStretch()

        left_layout.addWidget(self.weather_box)
        left_layout.addWidget(self.profile_box)
        left_layout.addWidget(self.sidebar_box)
        grid.addLayout(left_layout, 0, 0, 2, 1)

        # 2. CENTER COLUMN: Active Task & Task Manager
        center_layout = QVBoxLayout()
        center_layout.setSpacing(8)

        self.system_box = RetroNodeBox("Active Task")
        self.active_task_label = QLabel("No active task set")
        self.active_task_label.setWordWrap(True)
        self.system_box.box_layout.addWidget(self.active_task_label)

        self.task_box = RetroNodeBox("Task Manager")
        self.task_input = QLineEdit()
        self.task_input.setPlaceholderText("Type task & press Enter...")
        self.task_input.returnPressed.connect(self.add_task)

        self.task_list = QListWidget()
        self.task_list.itemClicked.connect(self.toggle_active_task)
        self.task_list.itemDoubleClicked.connect(self.open_task_inspector)

        self.task_box.box_layout.addWidget(self.task_input)
        self.task_box.box_layout.addWidget(self.task_list)

        center_layout.addWidget(self.system_box)
        center_layout.addWidget(self.task_box)
        grid.addLayout(center_layout, 0, 1, 2, 1)

        # 3. RIGHT COLUMN: Focus Timer & Focus Journal
        right_layout = QVBoxLayout()
        right_layout.setSpacing(8)

        self.timer_box = RetroNodeBox("Focus Timer")
        mode_layout = QHBoxLayout()
        self.radio_countdown = QRadioButton("Countdown")
        self.radio_stopwatch = QRadioButton("Stopwatch")
        self.radio_countdown.setChecked(True)

        self.mode_group = QButtonGroup(self)
        self.mode_group.addButton(self.radio_countdown)
        self.mode_group.addButton(self.radio_stopwatch)
        self.radio_countdown.toggled.connect(self.on_mode_change)

        mode_layout.addWidget(self.radio_countdown)
        mode_layout.addWidget(self.radio_stopwatch)
        self.timer_box.box_layout.addLayout(mode_layout)

        self.timer_display = QLabel("25:00")
        self.timer_display.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.timer_box.box_layout.addWidget(self.timer_display)

        self.duration_container = QWidget()
        duration_layout = QHBoxLayout(self.duration_container)
        duration_layout.setContentsMargins(0, 0, 0, 0)

        self.spin_mins = QSpinBox()
        self.spin_mins.setRange(1, 180)
        self.spin_mins.setValue(25)
        self.spin_mins.setSuffix(" m")

        self.btn_set_custom = QPushButton("Set")
        self.btn_set_custom.clicked.connect(self.set_custom_time)

        duration_layout.addWidget(QLabel("Duration:"))
        duration_layout.addWidget(self.spin_mins)
        duration_layout.addWidget(self.btn_set_custom)
        self.timer_box.box_layout.addWidget(self.duration_container)

        btn_layout = QHBoxLayout()
        self.timer_btn = QPushButton("Start / Pause")
        self.timer_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.timer_btn.clicked.connect(self.toggle_timer)

        self.reset_btn = QPushButton("Reset")
        self.reset_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.reset_btn.clicked.connect(self.reset_timer)

        btn_layout.addWidget(self.timer_btn)
        btn_layout.addWidget(self.reset_btn)
        self.timer_box.box_layout.addLayout(btn_layout)

        # Journal Box
        self.journal_box = RetroNodeBox("Focus Journal")
        self.journal_list = QListWidget()
        self.journal_list.setFixedHeight(85)
        self.journal_list.itemClicked.connect(self.load_selected_journal_entry)

        self.journal_input = PlainTextEdit()
        self.journal_input.setPlaceholderText("Write daily reflections or study notes here (Max 500 words)...")
        self.journal_input.textChanged.connect(self.on_journal_text_changed)

        self.word_count_label = QLabel("0 / 500 words")
        self.word_count_label.setAlignment(Qt.AlignmentFlag.AlignRight)

        journal_btn_layout = QHBoxLayout()
        self.btn_new_journal = QPushButton("New")
        self.btn_save_journal = QPushButton("Save")
        self.btn_edit_journal = QPushButton("Edit")
        self.btn_delete_journal = QPushButton("Delete")

        self.btn_new_journal.clicked.connect(self.prepare_new_journal_entry)
        self.btn_save_journal.clicked.connect(self.save_journal)
        self.btn_edit_journal.clicked.connect(self.edit_journal)
        self.btn_delete_journal.clicked.connect(self.delete_journal)

        for btn in (self.btn_save_journal, self.btn_edit_journal, self.btn_delete_journal):
            btn.setEnabled(False)

        journal_btn_layout.addWidget(self.btn_new_journal)
        journal_btn_layout.addWidget(self.btn_save_journal)
        journal_btn_layout.addWidget(self.btn_edit_journal)
        journal_btn_layout.addWidget(self.btn_delete_journal)

        self.lbl_recent = QLabel("Recent Log Entries:")
        self.journal_box.box_layout.addWidget(self.lbl_recent)
        self.journal_box.box_layout.addWidget(self.journal_list)
        self.journal_box.box_layout.addWidget(self.journal_input)
        self.journal_box.box_layout.addWidget(self.word_count_label)
        self.journal_box.box_layout.addLayout(journal_btn_layout)

        right_layout.addWidget(self.timer_box)
        right_layout.addWidget(self.journal_box)
        grid.addLayout(right_layout, 0, 2, 2, 1)

        self.qtimer = QTimer(self)
        self.qtimer.timeout.connect(self.update_timer)
        self.qtimer.start(1000)

        self.load_tasks_into_ui()

    def apply_theme(self, theme_mode: str):
        self.current_theme = theme_mode
        themes = {
            "light": {
                "bg_app": "#F1EAD8", "box_bg": "#E6DEC9", "card_bg": "#FAF6ED", "card_text": "#2A332A",
                "title_bg": "#F1EAD8", "border": "#588157", "text_main": "#2A332A", "text_accent": "#3A5A40",
                "input_bg": "#FAF6ED", "btn_bg": "#588157", "btn_text": "#FFFFFF", "btn_dis_bg": "#D2C9B3",
                "btn_dis_text": "#8A9A86", "radio_dot": "#3A5A40", "sel_bg": "#588157", "sel_text": "#FFFFFF",
                "hover_bg": "#D8E2DC"
            },
            "dark": {
                "bg_app": "#1e241e", "box_bg": "#2a332a", "card_bg": "#232a23", "card_text": "#a3b18a",
                "title_bg": "#1e241e", "border": "#588157", "text_main": "#d8e2dc", "text_accent": "#a3b18a",
                "input_bg": "#2a332a", "btn_bg": "#588157", "btn_text": "#ffffff", "btn_dis_bg": "#1e241e",
                "btn_dis_text": "#588157", "radio_dot": "#a3b18a", "sel_bg": "#3A5A40", "sel_text": "#FFFFFF",
                "hover_bg": "#384438"
            }
        }
        t = themes[theme_mode]

        self.setStyleSheet(f"background-color: {t['bg_app']};")

        box_style = f"""
            QGroupBox {{
                font-weight: bold; font-size: 14px; color: {t['text_accent']};
                border: 2px solid {t['border']}; border-radius: 6px;
                margin-top: 12px; background-color: {t['box_bg']};
            }}
            QGroupBox::title {{
                subcontrol-origin: margin; subcontrol-position: top left;
                left: 12px; padding: 0 6px; background-color: {t['title_bg']};
            }}
            QLabel {{ color: {t['text_main']}; font-size: 13px; background-color: transparent; }}
            QRadioButton {{
                color: {t['text_main']}; font-size: 13px; font-weight: bold; spacing: 6px; background-color: transparent;
            }}
            QRadioButton::indicator {{
                width: 12px; height: 12px; border-radius: 7px; border: 1px solid {t['border']}; background-color: transparent;
            }}
            QRadioButton::indicator:checked {{ background-color: {t['radio_dot']}; border: 1px solid {t['border']}; }}
        """

        for box in (self.profile_box, self.sidebar_box, self.system_box, self.task_box, self.timer_box,
                    self.weather_box, self.journal_box):
            box.setStyleSheet(box_style)

        self.active_task_label.setStyleSheet(f"""
            color: {t['card_text']}; font-weight: bold; font-size: 13px;
            background-color: {t['card_bg']}; padding: 8px; border-radius: 4px; border: 1px solid {t['border']};
        """)

        self.timer_display.setStyleSheet(f"""
            font-size: 28px; font-weight: bold; color: {t['text_accent']};
            background-color: {t['card_bg']}; border: 1px solid {t['border']};
            border-radius: 4px; padding: 6px; margin: 4px 0px;
        """)

        self.lbl_recent.setStyleSheet(
            f"color: {t['text_main']}; font-size: 13px; font-weight: bold; background-color: transparent;")
        self.word_count_label.setStyleSheet(
            f"color: {t['text_accent']}; font-size: 11px; margin-top: 2px; background-color: transparent;")

        input_style = f"""
            QLineEdit, QTextEdit, QSpinBox {{
                background-color: {t['input_bg']}; color: {t['text_main']}; 
                border: 1px solid {t['border']}; border-radius: 4px; padding: 4px;
            }}
            QTextEdit:disabled {{ background-color: {t['box_bg']}; color: {t['text_accent']}; }}
        """

        list_style = f"""
            QListWidget {{
                background-color: {t['input_bg']}; color: {t['text_main']}; 
                border: 1px solid {t['border']}; border-radius: 4px; padding: 4px;
            }}
            QListWidget::item {{ padding: 4px; border-radius: 3px; }}
            QListWidget::item:hover {{ background-color: {t['hover_bg']}; }}
            QListWidget::item:selected {{ background-color: {t['sel_bg']}; color: {t['sel_text']}; font-weight: bold; }}
        """

        self.task_input.setStyleSheet(input_style)
        self.task_list.setStyleSheet(list_style)
        self.journal_input.setStyleSheet(input_style)
        self.journal_list.setStyleSheet(list_style)
        self.spin_mins.setStyleSheet(input_style)

        button_style = f"""
            QPushButton {{
                background-color: {t['btn_bg']}; color: {t['btn_text']}; font-weight: bold; padding: 5px; border-radius: 4px;
            }}
            QPushButton:hover {{ background-color: #3a5a40; }}
            QPushButton:disabled {{ background-color: {t['btn_dis_bg']}; color: {t['btn_dis_text']}; border: 1px solid {t['border']}; }}
        """
        for btn in (self.btn_set_custom, self.timer_btn, self.reset_btn, self.btn_new_journal, self.btn_save_journal,
                    self.btn_edit_journal):
            btn.setStyleSheet(button_style)

        self.btn_delete_journal.setStyleSheet(f"""
            QPushButton {{ background-color: #a34848; color: #ffffff; font-weight: bold; padding: 5px; border-radius: 4px; }}
            QPushButton:hover {{ background-color: #823535; }}
            QPushButton:disabled {{ background-color: {t['btn_dis_bg']}; color: {t['btn_dis_text']}; border: 1px solid {t['border']}; }}
        """)

    def open_settings(self):
        SettingsDialog(self, current_theme=self.current_theme).exec()

    def get_clean_title(self, text):
        return text.split("\n")[0].replace(" [ACTIVE]", "").replace(" [DONE]", "").strip()

    def toggle_active_task(self, item):
        title = self.get_clean_title(item.text())
        if title in self.active_tasks:
            self.active_tasks.remove(title)
        else:
            if len(self.active_tasks) >= self.max_active_tasks:
                self.show_active_task_warning()
                return
            self.active_tasks.append(title)
        self.update_active_task_display()

    def show_active_task_warning(self):
        warning_msg = f"<span style='color: #d9534f; font-style: italic;'>You can only work in {self.max_active_tasks} active tasks.</span>"
        lines = [f"• <b>{task}</b>" for task in self.active_tasks]
        self.active_task_label.setText("<br>".join(lines) + f"<br>{warning_msg}" if lines else warning_msg)

    def update_active_task_display(self):
        if not self.active_tasks:
            self.active_task_label.setText("No active task set")
        else:
            lines = []
            for task_title in self.active_tasks:
                lines.append(f"• <b>{task_title}</b>")
                data = self.task_details.get(task_title, {})
                for sub in data.get("subtasks", []):
                    if isinstance(sub, dict):
                        desc_str = f": <i>{sub.get('desc', '')}</i>" if sub.get('desc') else ""
                        lines.append(f"   └ <b>{sub.get('title', '')}</b>{desc_str}")
                    else:
                        lines.append(f"   └ {sub}")
            self.active_task_label.setText("<br>".join(lines))

        self.reload_task_manager_list()

    def reload_task_manager_list(self):
        for i in range(self.task_list.count()):
            item = self.task_list.item(i)
            self.refresh_item_label(item, self.get_clean_title(item.text()))

    def refresh_item_label(self, item, raw_title):
        data = self.task_details.get(raw_title, {})
        display = raw_title
        if data.get("completed"):
            display += " [DONE]"
        if raw_title in self.active_tasks:
            display += " [ACTIVE]"

        if self.show_task_subtasks:
            for sub in data.get("subtasks", []):
                if isinstance(sub, dict):
                    desc_str = f": {sub.get('desc', '')}" if sub.get('desc') else ""
                    display += f"\n   └ {sub.get('title', '')}{desc_str}"
                else:
                    display += f"\n   └ {sub}"

        item.setText(display)

    def toggle_task_manager_subtasks(self):
        if not self.task_input.hasFocus() and not self.journal_input.hasFocus():
            self.show_task_subtasks = not self.show_task_subtasks
            self.reload_task_manager_list()

    def focus_task_list(self):
        self.task_list.setFocus()
        if self.task_list.count() > 0 and not self.task_list.selectedItems():
            self.task_list.setCurrentRow(0)

    def open_task_inspector(self):
        selected_items = self.task_list.selectedItems()
        if selected_items:
            raw_title = self.get_clean_title(selected_items[0].text())
            task_data = self.task_details.setdefault(raw_title, {"completed": False, "subtasks": []})
            TaskInspectorDialog(self, raw_title, task_data).exec()

    def remove_task(self, task_title):
        if task_title in self.active_tasks:
            self.active_tasks.remove(task_title)
            self.update_active_task_display()

        self.task_details.pop(task_title, None)

        for i in range(self.task_list.count()):
            item = self.task_list.item(i)
            if self.get_clean_title(item.text()) == task_title:
                self.task_list.takeItem(i)
                break

    def on_mode_change(self):
        self.timer_running = False
        if self.radio_countdown.isChecked():
            self.timer_mode = "countdown"
            self.time_seconds = self.spin_mins.value() * 60
            self.duration_container.setVisible(True)
        else:
            self.timer_mode = "stopwatch"
            self.time_seconds = 0
            self.duration_container.setVisible(False)
        self.render_timer_display()

    def set_custom_time(self):
        self.timer_running = False
        self.time_seconds = self.spin_mins.value() * 60
        self.render_timer_display()

    def toggle_timer(self):
        self.timer_running = not self.timer_running

    def reset_timer(self):
        self.timer_running = False
        self.time_seconds = self.spin_mins.value() * 60 if self.timer_mode == "countdown" else 0
        self.render_timer_display()

    def update_timer(self):
        self.lbl_live_clock.setText("Time: " + datetime.now().strftime("%I:%M:%S %p"))
        if not self.timer_running:
            return

        if self.timer_mode == "countdown":
            if self.time_seconds > 0:
                self.time_seconds -= 1
            else:
                self.timer_running = False
        else:
            self.time_seconds += 1

        self.render_timer_display()

    def render_timer_display(self):
        mins, secs = divmod(self.time_seconds, 60)
        self.timer_display.setText(f"{mins:02d}:{secs:02d}")

    def get_first_line_preview(self, text: str, max_chars: int = 22) -> str:
        first_line = text.strip().split('\n')[0] if text else ""
        return (first_line[:max_chars].strip() + "...") if len(first_line) > max_chars else first_line

    def on_journal_text_changed(self):
        text = self.journal_input.toPlainText()
        words = text.split()
        word_count = len(words)

        if word_count > self.max_word_count:
            truncated_text = " ".join(words[:self.max_word_count])
            self.journal_input.blockSignals(True)
            self.journal_input.setPlainText(truncated_text)
            self.journal_input.moveCursor(self.journal_input.textCursor().MoveOperation.End)
            self.journal_input.blockSignals(False)
            word_count = self.max_word_count

        self.word_count_label.setText(f"{word_count} / {self.max_word_count} words")
        if self.journal_input.isEnabled():
            self.btn_save_journal.setEnabled(bool(text.strip()))

    def prepare_new_journal_entry(self):
        self.current_journal_idx = None
        self.journal_list.clearSelection()
        self.journal_input.setEnabled(True)
        self.journal_input.clear()
        self.journal_input.setFocus()
        self.btn_save_journal.setEnabled(False)
        self.btn_edit_journal.setEnabled(False)
        self.btn_delete_journal.setEnabled(False)

    def save_journal(self):
        text = self.journal_input.toPlainText().strip()
        if not text:
            return

        now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
        preview = self.get_first_line_preview(text)

        if self.current_journal_idx is not None:
            idx = self.current_journal_idx
            self.journal_entries[idx]["text"] = text
            self.journal_entries[idx]["edited"] = now_str
            self.journal_list.item(idx).setText(f"{self.journal_entries[idx]['created']} - \"{preview}\"")
        else:
            entry = {"created": now_str, "edited": now_str, "text": text}
            if len(self.journal_entries) >= self.max_journal_logs:
                self.journal_entries.pop(0)
                self.journal_list.takeItem(0)

            self.journal_entries.append(entry)
            item = QListWidgetItem(f"{now_str} - \"{preview}\"")
            self.journal_list.addItem(item)
            self.current_journal_idx = len(self.journal_entries) - 1
            self.journal_list.setCurrentItem(item)

        self.journal_input.setEnabled(False)
        self.btn_save_journal.setEnabled(False)
        self.btn_edit_journal.setEnabled(True)
        self.btn_delete_journal.setEnabled(True)

    def edit_journal(self):
        if self.current_journal_idx is not None:
            self.journal_input.setEnabled(True)
            self.journal_input.setFocus()
            self.btn_save_journal.setEnabled(True)
            self.btn_edit_journal.setEnabled(False)

    def delete_journal(self):
        if self.current_journal_idx is not None:
            idx = self.current_journal_idx
            self.journal_entries.pop(idx)
            self.journal_list.takeItem(idx)

            self.current_journal_idx = None
            self.journal_input.clear()
            self.journal_input.setEnabled(False)
            self.btn_save_journal.setEnabled(False)
            self.btn_edit_journal.setEnabled(False)
            self.btn_delete_journal.setEnabled(False)

    def load_selected_journal_entry(self, item):
        idx = self.journal_list.row(item)
        if 0 <= idx < len(self.journal_entries):
            self.current_journal_idx = idx
            self.journal_input.setPlainText(self.journal_entries[idx]["text"])
            self.journal_input.setEnabled(False)
            self.btn_save_journal.setEnabled(False)
            self.btn_edit_journal.setEnabled(True)
            self.btn_delete_journal.setEnabled(True)

    def setup_shortcuts(self):
        shortcuts = [
            ("A", self.focus_task_input),
            ("Z", self.focus_task_list),
            ("V", self.trigger_view_keybind),
            ("H", self.toggle_task_manager_subtasks),
            ("S", self.trigger_settings_keybind),
            ("Space", self.handle_spacebar),
            ("Escape", self.setFocus)
        ]
        for key, func in shortcuts:
            QShortcut(QKeySequence(key), self).activated.connect(func)

    def trigger_view_keybind(self):
        if not self.task_input.hasFocus() and not self.journal_input.hasFocus():
            self.open_task_inspector()

    def trigger_settings_keybind(self):
        if not self.task_input.hasFocus() and not self.journal_input.hasFocus():
            self.open_settings()

    def focus_task_input(self):
        self.task_input.setFocus()
        self.task_input.selectAll()

    def handle_spacebar(self):
        if not self.task_input.hasFocus() and not self.journal_input.hasFocus():
            self.toggle_timer()

    def load_tasks_into_ui(self):
        self.task_list.clear()
        for task in self.state.tasks:
            self.task_list.addItem(task.title)
            self.task_details[task.title] = {"completed": False, "subtasks": []}

    def add_task(self):
        text = self.task_input.text().strip()
        if text:
            new_task = TaskItem(id=len(self.state.tasks) + 1, title=text)
            self.state.tasks.append(new_task)
            save_data(self.state)
            self.task_list.addItem(text)
            self.task_details[text] = {"completed": False, "subtasks": []}
            self.task_input.clear()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = IvyNodeWindow()
    window.show()
    sys.exit(app.exec())