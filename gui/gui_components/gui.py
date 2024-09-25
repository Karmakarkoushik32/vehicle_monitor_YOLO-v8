import sys
import cv2
import numpy as np
from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel, QVBoxLayout, QWidget
from PyQt5.QtGui import QImage, QPixmap, QPainter, QPen
from PyQt5.QtCore import QTimer, Qt, QPoint, QSize

class CameraWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Camera Feed with PyQt5 and OpenCV")
        self.setGeometry(100, 100, 800, 600)

        self.label = QLabel(self)
        self.label.setAlignment(Qt.AlignCenter)

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)

        self.initUI()

        self.cap = cv2.VideoCapture(0)
        if not self.cap.isOpened():
            print("Error: Could not open video stream or file")
            self.close()

        self.q_img = None
        self.drag_start = None
        self.line_start = None
        self.line_end = None

    def initUI(self):
        layout = QVBoxLayout()
        layout.addWidget(self.label)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

        # OpenCV mouse event callbacks
        self.label.mousePressEvent = self.on_mouse_press
        self.label.mouseMoveEvent = self.on_mouse_move
        self.label.mouseReleaseEvent = self.on_mouse_release

    def update_frame(self):
        ret, frame = self.cap.read()
        if not ret:
            return

        # Convert the frame to RGB format
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # Convert the image to QImage
        height, width, channel = frame_rgb.shape
        bytes_per_line = 3 * width
        self.q_img = QImage(frame_rgb.data, width, height, bytes_per_line, QImage.Format_RGB888)
        self.q_img = self.q_img.scaled(self.label.size(), aspectRatioMode =Qt.KeepAspectRatioByExpanding,transformMode = Qt.FastTransformation)

        print(self.q_img.size() ,QSize(width,height), self.label.size())
    
        self.dif = self.label.size() - self.q_img.size()
        self.dif = QPoint(self.dif.width(), self.dif.height())
        # Display the QImage
        self.label.setPixmap(QPixmap.fromImage(self.q_img))

        # Draw the line on the QLabel
        if self.line_start and self.line_end:
            painter = QPainter(self.label.pixmap())
            painter.setPen(QPen(Qt.red, 2, Qt.SolidLine))
            painter.drawLine(self.line_start, self.line_end)
            painter.end()
            self.label.update()

    def on_mouse_press(self, event):
        if event.buttons() == Qt.LeftButton:
            if self.line_start is None:
                self.line_start = event.pos() - (self.dif / 2)
            else:
                self.line_end = event.pos() - (self.dif / 2)
                self.update_frame()

    def on_mouse_move(self, event):
        if event.buttons() == Qt.LeftButton and self.line_start is not None:
            self.line_end = event.pos() - (self.dif / 2)
            self.update_frame()

    def on_mouse_release(self, event):
        if event.button() == Qt.LeftButton and self.line_start is not None:
            self.line_end = event.pos() - (self.dif / 2)
            self.update_frame()
            self.line_start = None
            self.line_end = None

    def closeEvent(self, event):
        self.cap.release()
        super().closeEvent(event)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = CameraWindow()
    window.show()
    window.timer.start(30)  # Update the frame every 30 ms
    sys.exit(app.exec_())
