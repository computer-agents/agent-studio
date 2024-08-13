import sys
import json
from typing import get_origin
from enum import Enum
import bisect
import logging

from agent_studio.recorder.utils import Record, Event

from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QPushButton, QFileDialog, QListWidget,
                             QSlider, QLabel, QLineEdit, QComboBox, QFormLayout,
                             QCheckBox, QSpinBox, QDoubleSpinBox, QMenuBar, QMenu, QMessageBox)
from PyQt6.QtMultimedia import QMediaPlayer
from PyQt6.QtMultimediaWidgets import QVideoWidget
from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QAction

# from qfluentwidgets import FluentTranslator

logger = logging.getLogger(__name__)


class VideoPlayer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Video Player")
        self.setGeometry(100, 100, 1000, 600)

        self.record: Record | None = None
        self.current_event: Event | None = None
        self.current_file = None

        self.create_menu_bar()

        # Main layout
        main_layout = QHBoxLayout()

        # Video widget (left side)
        video_layout = QVBoxLayout()
        self.video_widget = QVideoWidget()
        self.media_player = QMediaPlayer()
        self.media_player.setVideoOutput(self.video_widget)
        video_layout.addWidget(self.video_widget)

        self.play_button = QPushButton("Play")
        self.play_button.clicked.connect(self.play_pause)
        video_layout.addWidget(self.play_button)

        self.seek_slider = QSlider(Qt.Orientation.Horizontal)
        self.seek_slider.sliderMoved.connect(self.set_position)
        video_layout.addWidget(self.seek_slider)

        video_container = QWidget()
        video_container.setLayout(video_layout)
        main_layout.addWidget(video_container, 2)

        # Right side layout
        right_layout = QVBoxLayout()

        # List widget (middle-right)
        self.list_widget = QListWidget()
        self.list_widget.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        self.list_widget.itemSelectionChanged.connect(self.update_event_details)
        right_layout.addWidget(self.list_widget)

        # Event details widget (bottom-right)
        self.event_details_widget = QWidget()
        self.event_details_layout = QFormLayout()
        self.event_details_widget.setLayout(self.event_details_layout)
        right_layout.addWidget(self.event_details_widget)

        right_container = QWidget()
        right_container.setLayout(right_layout)
        main_layout.addWidget(right_container, 1)

        # Set the main layout
        central_widget = QWidget()
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)

        # Connect media player signals
        self.media_player.positionChanged.connect(self.position_changed)
        self.media_player.durationChanged.connect(self.duration_changed)

    def create_menu_bar(self):
        menu_bar = QMenuBar(self)
        self.setMenuBar(menu_bar)

        # File menu
        file_menu = QMenu("File", self)
        menu_bar.addMenu(file_menu)

        # Open action
        open_action = QAction("Open", self)
        open_action.triggered.connect(self.open_file)
        file_menu.addAction(open_action)

        # Save action
        save_action = QAction("Save", self)
        save_action.triggered.connect(self.save_file)
        file_menu.addAction(save_action)

        # Save As action
        save_as_action = QAction("Save As", self)
        save_as_action.triggered.connect(self.save_file_as)
        file_menu.addAction(save_as_action)

    def update_event_details(self):
        # Clear previous details
        for i in reversed(range(self.event_details_layout.rowCount())):
            self.event_details_layout.removeRow(i)

        selected_items = self.list_widget.selectedItems()
        if not selected_items or self.record is None:
            self.current_event = None
            return

        selected_index = self.list_widget.row(selected_items[0])
        self.current_event = self.record.events[selected_index]

        # Add static fields
        self.event_details_layout.addRow(
            "Event Type:", QLabel(self.current_event.event_type))

        # Dynamically create UI elements based on event type
        if len(self.list_widget.selectedItems()) == 1:
            self.create_dynamic_ui(self.current_event)

    def create_dynamic_ui(self, event: Event):
        for field_name, field in event.model_fields.items():
            if field_name in ['event_type']:
                continue  # Skip static fields

            field_type = field.annotation
            field_value = getattr(event, field_name)

            label = QLabel(field_name.capitalize() + ":")
            widget = self.create_widget_for_field(field_name, field_type, field_value)

            if widget:
                self.event_details_layout.addRow(label, widget)

    def create_widget_for_field(self, field_name, field_type, field_value):
        if isinstance(field_type, type) and issubclass(field_type, Enum):
            widget = QComboBox()
            widget.addItems([e.name for e in field_type])
            if field_value:
                widget.setCurrentText(field_value.name)
            widget.currentTextChanged.connect(
                lambda text: self.update_field(field_name, field_type[text]))
        elif field_type == bool or get_origin(field_type) == bool:
            widget = QCheckBox()
            if field_value is not None:
                widget.setChecked(field_value)
            widget.stateChanged.connect(
                lambda state: self.update_field(field_name, bool(state)))
        elif field_type == int or get_origin(field_type) == int:
            widget = QSpinBox()
            if field_value is not None:
                widget.setValue(field_value)
            widget.valueChanged.connect(
                lambda value: self.update_field(field_name, value))
        elif field_type == float or get_origin(field_type) == float:
            widget = QDoubleSpinBox()
            widget.setDecimals(9)
            if field_value is not None:
                widget.setValue(field_value)
            widget.valueChanged.connect(
                lambda value: self.update_field(field_name, value))
        elif field_type == str or get_origin(field_type) == str:
            widget = QLineEdit(str(field_value) if field_value is not None else "")
            widget.textChanged.connect(lambda text: self.update_field(field_name, text))
        else:
            # For complex types, use a simple QLineEdit
            widget = QLineEdit(str(field_value) if field_value is not None else "")
            widget.textChanged.connect(lambda text: self.update_field(field_name, text))

        return widget

    def update_field(self, field_name, value):
        if self.current_event is not None:
            setattr(self.current_event, field_name, value)
            self.update_list_item()

    def update_list_item(self):
        selected_items = self.list_widget.selectedItems()
        if len(selected_items) == 1:
            selected_items[0].setText(str(self.current_event))

    def play_pause(self):
        if self.media_player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.media_player.pause()
            self.play_button.setText("Play")
        else:
            self.media_player.play()
            self.play_button.setText("Pause")

    def open_file(self):
        file_name, _ = QFileDialog.getOpenFileName(self, "Open Record Trajectory")
        if file_name:
            self.current_file = file_name
            with open(file_name, 'r') as f:
                self.record = Record.model_validate(json.load(f))
                if self.record.task_type == "vision" and self.record.video is not None:
                    self.media_player.setSource(
                        QUrl.fromLocalFile(self.record.video.path))
                self.list_widget.clear()
                for i, event in enumerate(self.record.events):
                    self.list_widget.addItem(f"{event}")

    ### Menu Bar Slots ###
    def save_file(self):
        if self.current_file:
            self.save_to_file(self.current_file)
        else:
            self.save_file_as()

    def save_file_as(self):
        file_name, _ = QFileDialog.getSaveFileName(self, "Save Record Trajectory")
        if file_name:
            self.current_file = file_name
            self.save_to_file(file_name)

    def save_to_file(self, file_name):
        if self.record is None:
            QMessageBox.critical(self, "Save Failed", "No record to save.")
            return
        try:
            json_str = self.record.model_dump_json(indent=4)
            with open(file_name, 'w') as f:
                f.write(json_str)
            QMessageBox.information(self, "Save Successful", "File saved successfully.")
        except Exception as e:
            QMessageBox.critical(self, "Save Failed",
                                 f"An error occurred while saving: {str(e)}")

    ### Media Player Slots ###

    def handle_item_color(self):
        # find out the current event
        if self.record is not None:
            # position is in milliseconds
            idx = bisect.bisect_left(self.record.events, Event(
                time=self.media_player.position() / 1000.0, event_type=""))
            # change the corresponding item to green
            for i in range(self.list_widget.count()):
                item = self.list_widget.item(i)
                if item is None:
                    logging.error("Item is None")
                    continue
                if i == idx:
                    item.setBackground(Qt.GlobalColor.green)
                else:
                    item.setBackground(Qt.GlobalColor.white)

    def set_position(self, position):
        self.media_player.setPosition(position)

    def position_changed(self, position):
        self.seek_slider.setValue(position)
        self.handle_item_color()

    def duration_changed(self, duration):
        self.seek_slider.setRange(0, duration)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    # if sys.platform == 'win32' and sys.getwindowsversion().build >= 22000:
    #     app.setStyle("fusion")
    # translator = FluentTranslator()
    # app.installTranslator(translator)
    player = VideoPlayer()
    player.show()
    sys.exit(app.exec())
