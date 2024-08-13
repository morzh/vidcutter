from PyQt6.QtCore import QEvent, QSize, Qt
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QStyle,
    QToolButton,
    QVBoxLayout,
    QWidget,
    QSizePolicy,
    QSizeGrip,
)


class CustomTitleBar(QWidget):
    def __init__(self, parent, height=32):
        super().__init__(parent)
        self.initial_pos = None
        title_bar_layout = QHBoxLayout(self)
        title_bar_layout.setContentsMargins(0, 0, 0, 0)
        title_bar_layout.setSpacing(2)

        file_operations_layout = QHBoxLayout()
        open_icon = QIcon("open2.svg")
        self.open_button = QToolButton(self)
        self.open_button.setIcon(open_icon)

        save_icon = QIcon("save.svg")
        self.save_button = QToolButton(self)
        self.save_button.setIcon(save_icon)

        file_operations_layout.addWidget(self.open_button)
        file_operations_layout.addWidget(self.save_button)
        file_operations_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)

        self.title = QLabel(f"{self.__class__.__name__}", self)
        self.title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title.setStyleSheet(
            """
        QLabel { text-transform: uppercase; font-size: 10pt; margin-left: 48px; }
        """
        )

        if title := parent.windowTitle():
            self.title.setText(title)

        # Min button
        min_icon = QIcon("min2.svg")
        self.min_button = QToolButton(self)
        self.min_button.setIcon(min_icon)
        self.min_button.clicked.connect(self.window().showMinimized)

        # Max button
        max_icon = QIcon("max2.svg")
        self.max_button = QToolButton(self)
        self.max_button.setIcon(max_icon)
        self.max_button.clicked.connect(self.window().showMaximized)

        # Close button
        close_icon = QIcon("close.svg")
        self.close_button = QToolButton(self)
        self.close_button.setIcon(close_icon)
        self.close_button.clicked.connect(self.window().close)

        # Normal button
        normal_icon = QIcon("normal.svg")
        self.normal_button = QToolButton(self)
        self.normal_button.setIcon(normal_icon)
        self.normal_button.clicked.connect(self.window().showNormal)
        self.normal_button.setVisible(False)

        # Add buttons
        buttons = [
            self.save_button,
            self.open_button,
            self.min_button,
            self.normal_button,
            self.max_button,
            self.close_button,
        ]

        window_buttons_layout = QHBoxLayout()
        window_buttons_layout.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.setFixedHeight(height)
        for button in buttons:
            button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            button.setFixedSize(QSize(int(0.9 * height), int(0.9 * height)))
            button.setIconSize(QSize(int(0.5 * height), int(0.5 * height)))
            button.setStyleSheet(
                """QToolButton {
                    border: none;
                    padding: 2px;
                }
                """
            )
            window_buttons_layout.addWidget(button)
            # window_buttons_layout.addStretch()

        title_bar_layout.addLayout(file_operations_layout)
        title_bar_layout.addWidget(self.title)
        # title_bar_layout.addStretch()
        title_bar_layout.addLayout(window_buttons_layout)

    def window_state_changed(self, state):
        if state == Qt.WindowState.WindowMaximized:
            self.normal_button.setVisible(True)
            self.max_button.setVisible(False)
        else:
            self.normal_button.setVisible(False)
            self.max_button.setVisible(True)

        self.updateGeometry()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.initial_pos = None
        self.setWindowTitle("Custom Title Bar")
        self.setMinimumSize(400, 200)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        central_widget = QWidget()
        central_widget.setObjectName("Container")
        self.title_bar = CustomTitleBar(self, 36)

        work_space_layout = QVBoxLayout()
        work_space_layout.setContentsMargins(11, 11, 11, 11)
        work_space_layout.addWidget(QLabel("Hello, World!", self))

        central_widget_layout = QVBoxLayout()
        central_widget_layout.setContentsMargins(0, 0, 0, 0)
        central_widget_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        central_widget_layout.addWidget(self.title_bar)
        central_widget_layout.addLayout(work_space_layout)

        central_widget.setLayout(central_widget_layout)
        self.setCentralWidget(central_widget)

    def changeEvent(self, event):
        if event.type() == QEvent.Type.WindowStateChange:
            self.title_bar.window_state_changed(self.windowState())
        super().changeEvent(event)
        event.accept()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.initial_pos = event.position().toPoint()
        super().mousePressEvent(event)
        event.accept()

    def mouseMoveEvent(self, event):
        if self.initial_pos is not None:
            delta = event.position().toPoint() - self.initial_pos
            self.window().move(
                self.window().x() + delta.x(),
                self.window().y() + delta.y(),
            )
        super().mouseMoveEvent(event)
        event.accept()

    def mouseReleaseEvent(self, event):
        self.initial_pos = None
        super().mouseReleaseEvent(event)
        event.accept()

    # def resizeEvent(self, a0):
    #     self.title_bar.setFixedWidth(self.window().size().width())


if __name__ == "__main__":
    app = QApplication([])
    window = MainWindow()
    window.show()
    app.exec()