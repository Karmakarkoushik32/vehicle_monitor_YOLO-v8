import sys
from PyQt5 import QtWidgets
from PyQt5.QtWidgets import (
    QApplication,
    QTreeWidget,
    QTreeWidgetItem,
    QMainWindow,
    QTableWidgetItem,
    QMessageBox,
)
from PyQt5.QtCore import QTimer, Qt, QPoint, QSize, QCoreApplication
from PyQt5.QtGui import QImage, QPixmap, QPainter, QPen, QPainterPath

# gui components
from gui.gui_components.form_lite import Form
from gui.gui_components.wigdets import *

# for detection
from gui.model.list_devices import list_devices
from gui.model.detection import Detection

# util functions
from gui.utils.utils import formatTime
## for logging
from gui.utils.log import * 

# base paths
from gui import MODELS_PATH, ASSETS_PATH

import cv2
import numpy as np
from uuid import uuid1
import os, math
from datetime import datetime
import csv
from pathlib import Path



class App(QtWidgets.QWidget):
    def __init__(self):
        super(App, self).__init__()

        self.ui = Form()
        self.ui.setupUi(self)
        self.__initLogger()
        self.__initWidgets()
        self.__initModel()
        self.__initEventsAndCallBacks()
        self.__initVariables()


    def __initLogger(self):
        logTextBox = QPlainTextEditLogger(self)
        # You can format what is printed to the text box
        logTextBox.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        logging.getLogger().addHandler(logTextBox)
        # You can control the logging level
        logging.getLogger().setLevel(logging.DEBUG)

        # Add the new logging box widget to the ui.console groupbox
        layout = QtWidgets.QVBoxLayout(self.ui.console)
        self.ui.console.setLayout(layout)
        # Add the new logging box widget to the ui.console group box
        self.ui.console.layout().addWidget(logTextBox.widget) 

    def __initModel(self):
        devices = list_devices()
        
        self.ui.deviceselector.addItems(devices)  
        self.ui.deviceselector.setCurrentIndex(0)
        default_model = 'yolov8n.pt'
        
        try:
            self.detector = Detection(device = self.ui.deviceselector.currentText().split('|')[0], viz_mode = self.ui.vizselectro.currentIndex())
            print(os.path.join(MODELS_PATH, default_model))
            self.detector.loadModel(os.path.join(MODELS_PATH, default_model))
            QMessageBox.information(self, "Information", "Model loaded successfully")
        except Exception as e:
            QMessageBox.critical(self, "Error",e)
            logging.error(e)
            return
        

        self.ui.modelpathlineedit.setText(default_model)
    
    def chooseModel(self):
        modelPath = self.chooseFile()
        if modelPath is None: return

        try:
            self.detector.selectDevice(self.ui.deviceselector.currentText())
            self.detector.loadModel(modelPath)
            QMessageBox.information(self, "Information", "Model loaded successfully")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"An error occurred while exporting the table: {e}")
            logging.error(e)
            return 

        self.ui.modelpathlineedit.setText(modelPath)

    def __toggleModelParamsVisibility(self):
        toggle = False if self.ui.modelchooserbtn.isEnabled() else True
        self.ui.modelchooserbtn.setEnabled(toggle)
        self.ui.deviceselector.setEnabled(toggle)
        self.ui.vizselectro.setEnabled(toggle)

    def onVizModeChange(self):
        mode_index = self.ui.vizselectro.currentIndex()
        mode_name = self.ui.vizselectro.currentText()
        logging.info(f"mode changed to: {mode_name}, index : {mode_index}")
        self.detector.setVizMode(mode_index)

    def onDeviceSelect(self):
        device = self.ui.deviceselector.currentText().split('|')[0]
        logging.info(f"device changed to: {device}")
        self.detector.selectDevice(device)
        self.detector.resetModel()
    
    def chooseFile(self):
        file_dialog = QFileDialog(self)
        file_dialog.setFileMode(QFileDialog.ExistingFile)
        file_dialog.setNameFilter('model Files (*.pt)')
        if file_dialog.exec_():
            file_path = file_dialog.selectedFiles()[0]
            return file_path
        
    def __initWidgets(self):
        self.videoDialog = VideoFileLodingWidget()

    def __initEventsAndCallBacks(self):
        # all button callbacks
        self.ui.playpausebtn.setEnabled(False)
        self.ui.loadvideobtn.clicked.connect(self.loadVideo)
        self.ui.playpausebtn.clicked.connect(self.videoToggler)

        self.ui.toggledrawingbtn.setEnabled(False)
        self.ui.toggledrawingbtn.clicked.connect(self.drawingToggler)

        # OpenCV mouse event callbacks
        self.ui.video_panel.mousePressEvent = self.onMousePress
        self.ui.video_panel.mouseMoveEvent = self.onMouseMove

        # load model
        self.ui.modelchooserbtn.clicked.connect(self.chooseModel)

        # device change callback
        self.ui.deviceselector.currentIndexChanged.connect(self.onDeviceSelect)

        # viz mode callback
        self.ui.vizselectro.currentIndexChanged.connect(self.onVizModeChange)

        # slot callbasks
        self.videoDialog.videoLoaded.connect(self.videoLoadedSlot)

        # export to csv callback
        self.ui.exportreportbtn.clicked.connect(self.exportTable)


    def __initVariables(self):
        self._translate = QCoreApplication.translate
        self.drag_start = None
        self.line_start = None
        self.line_end = None
        self.currect_point = None
        self.line = []
        self.lines = {}
        self.line_id = uuid1()
        self.video_path = None

        # for toggling video play/payse and drawing
        self.is_video_running = False
        self.is_drawing = False

        # for progress update
        self.total_frames = 0
        self.completed_frames = 1
        self.videoDuration = 0

    def initCap(self):
        self.cap = cv2.VideoCapture(self.video_path)
        
        if not self.cap.isOpened():
            logging.error(f'unable to capture video from source : {self.video_path}')
            QMessageBox.critical(
                self,
                "error",  # Title of the message box
                "Could not open video stream or file, try again.",  # Message text
            )
            return

        # enable buttons
        self.ui.playpausebtn.setEnabled(True)
        self.ui.toggledrawingbtn.setEnabled(True)

        # Calculate the duration in seconds
        self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.completed_frames = 1
        fps = self.cap.get(cv2.CAP_PROP_FPS)
        try:
            self.videoDuration = self.total_frames / fps
        except Exception as e:
            logging.info(e)
        logging.info(f'Video loaded Successfilly, Tatal frames: {self.total_frames}, FPS: {fps}, duration: {self.videoDuration}')

        ret, frame = self.cap.read()
        if not ret:
            return
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        self.frame = frame
    
        # Reset progress bar
        self.ui.progressBar.setValue(0)  # Assuming the initial value was 0

        # Reset video current time
        self.ui.videocurrenttime.setText(self._translate("Form", "00:00:00 SEC"))

        # Reset infotable_1 and lines
        self.lines = {}
        self.ui.infotable_1.setRowCount(0)

        # time pulse for update frames
        self.timer = QTimer()
        self.timer.timeout.connect(self.updateFrame) 

        # reset model
        self.detector.resetModel()


        self.__display(self.frame)


    def __display(self, frame):

        height, width, _ = frame.shape
        for _, line in self.lines.items():
            scale_x = width / self.q_img.size().width()
            scale_y = height / self.q_img.size().height()
            points = [(point.x() * scale_x, point.y() * scale_y) for point in line]
            pts = np.array(points, dtype=np.int32).reshape((-1, 1, 2))
            frame = cv2.polylines(frame, [pts], False, (0, 255, 0), 2, lineType=cv2.LINE_AA)

        bytes_per_line = 3 * width
        self.q_img = QImage(
            frame.data, width, height, bytes_per_line, QImage.Format_RGB888
        )
        self.q_img = self.q_img.scaled(
            self.ui.video_panel.size(),
            aspectRatioMode=Qt.KeepAspectRatio,
            transformMode=Qt.FastTransformation,
        )
        
        self.dif = self.ui.video_panel.size() - self.q_img.size()
        self.dif = QPoint(self.dif.width(), self.dif.height())
        q_pixmap = QPixmap.fromImage(self.q_img)

        # Display the QImage
        self.ui.video_panel.setPixmap(q_pixmap)

    def __drawLiveInteractions(self):
        if self.currect_point is None:
            return

        self.painter = QPainter(self.ui.video_panel.pixmap())
        self.painter.setPen(QPen(Qt.red, 2, Qt.SolidLine))
        points = [*self.line, self.currect_point]

        for i in range(len(points) - 1):
            self.painter.drawLine(points[i], points[i + 1])

        self.painter.end()
        self.ui.video_panel.update()

    @property
    def crossingLines(self):
        lines = {}
        height, width, _ = self.frame.shape
        scale_x = width / self.q_img.size().width()
        scale_y = height / self.q_img.size().height()
    
        for uuid_key, points in self.lines.items():
            # points= [point + (self.dif / 2) for point in points]
            
            geometry = [(point.x() * scale_x, point.y() * scale_y) for point in points]
            # Constructing the final dictionary
            lines[uuid_key] = {
                "geometry": geometry,
                "color": (0, 255, 0),  # Default color
                "type": "line"
            }
        return lines
    
    def updateTrackingTable(self, data):
        logging.info(f'Tracking info : {data}')
        data['file'] = self.video_path
        numRows = self.ui.infotable_2.rowCount()
        self.ui.infotable_2.insertRow(numRows)
        for i, key in enumerate(["file", "line_id", "track_id", "crossing_time","vechile","direction"]):
            self.ui.infotable_2.setItem(numRows, i, QTableWidgetItem(str(data[key])))

    def __resetFrameUpdate(self):
        self.detector.resetModel()
        self.timer.stop()
        self.videoToggler()
        self.ui.playpausebtn.setEnabled(False)
        self.ui.toggledrawingbtn.setEnabled(False)
        self.cap.release()


    def exportTable(self):
        # Open a file dialog to choose where to save the CSV file
        options = QFileDialog.Options()
        filePath, _ = QFileDialog.getSaveFileName(self, "Save Table As CSV", "", "CSV Files (*.csv);;All Files (*)", options=options)
        
        if filePath:  # If the user selected a file path
            try:
                # Open the file in write mode
                with open(filePath, mode='w', newline='') as file:
                    writer = csv.writer(file)

                    # Get the number of rows and columns in the table
                    row_count = self.ui.infotable_2.rowCount()
                    column_count = self.ui.infotable_2.columnCount()

                    # Write the headers (column labels)
                    headers = [self.ui.infotable_2.horizontalHeaderItem(i).text() for i in range(column_count)]
                    writer.writerow(headers)

                    # Write each row
                    for row in range(row_count):
                        row_data = []
                        for column in range(column_count):
                            item = self.ui.infotable_2.item(row, column)
                            row_data.append(item.text() if item else "")  # Append item text or empty string if no item
                        writer.writerow(row_data)

                # Optionally, you can show a message box to indicate successful export
                QMessageBox.information(self, "Export Successful", "Table has been exported successfully!")
                logging.info(f'csv exported to : {filePath}')
            except Exception as e:
                QMessageBox.critical(self, "Error", f"An error occurred while exporting the table: {e}")
                logging.error(e)

    def updateFrame(self):
        if self.is_video_running:
            ret, self.frame = self.cap.read()
            if not ret:
                logging.info(f'process completed : {self.video_path}')
                self.__resetFrameUpdate()
                return
            
            # detect
            self.frame = self.detector.detectAndTracePath(self.frame, self.crossingLines, self.ui.videocurrenttime.text() ,self.updateTrackingTable) # WORKING

            # update progress
            frame_completed_ratio = self.completed_frames / self.total_frames
            self.ui.progressBar.setValue(min(math.ceil(frame_completed_ratio * 100), 100))
            self.ui.videocurrenttime.setText(formatTime(self.videoDuration * frame_completed_ratio) + ' SEC')
            self.completed_frames += 1
            # Convert the frame to RGB format
            self.frame = cv2.cvtColor(self.frame, cv2.COLOR_BGR2RGB)

        ## drown image and interactions
        self.__display(self.frame)
        self.__drawLiveInteractions()

    def onMousePress(self, event):
        if not self.is_drawing:
            return

        self.setFocus()
        if event.buttons() == Qt.LeftButton:
            if self.line_start is None:
                self.line_start = event.pos() - (self.dif / 2)
                self.line.append(self.line_start)

            else:
                self.line_end = event.pos() - (self.dif / 2)
                self.line.append(self.line_end)
                self.updateFrame()

        elif event.buttons() == Qt.RightButton:
            self.line_start = None
            self.line_end = None
            self.currect_point = None
            self.updateFrame()

            if len(self.line) > 1:
                # add line to collection
                self.lines[self.line_id] = self.line

                ## update table 1
                numRows = self.ui.infotable_1.rowCount()
                self.ui.infotable_1.insertRow(numRows)
                self.ui.infotable_1.setItem(
                    numRows, 0, QTableWidgetItem(str(self.line_id))
                )
                self.ui.infotable_1.setItem(
                    numRows, 1, QTableWidgetItem(str(self.line))
                )

            ## reset line and id
            self.line = []
            self.line_id = uuid1()

    def onMouseMove(self, event):
        if not self.is_drawing:
            return

        self.setFocus()  # focus to the videoframe
        if self.line_start is not None:
            self.currect_point = event.pos() - (self.dif / 2)
            self.updateFrame()

    def closeEvent(self, event):
        self.cap.release()
        super().closeEvent(event)

    def loadVideo(self):
        self.videoDialog.close()
        self.videoDialog.show()

    def videoToggler(self):
        self.ui.playpausebtn.setText(
            self._translate(
                "Form",
                (
                    "Pause"
                    if self.ui.playpausebtn.text() == self._translate("Form", "Play")
                    else "Play"
                ),
            )
        )
        if self.is_drawing and not self.is_video_running:
            self.drawingToggler()

        self.is_video_running = False if self.is_video_running else True

        if self.is_video_running:
            self.timer.start(30)
            self.__toggleModelParamsVisibility()
        else:
            if not self.is_drawing:
                self.timer.stop()
                self.__toggleModelParamsVisibility()

    def drawingToggler(self):

        self.line = []
        self.ui.toggledrawingbtn.setText(
            self._translate(
                "Form",
                (
                    "Stop Drawing"
                    if self.ui.toggledrawingbtn.text()
                    == self._translate("Form", "Start Drawing")
                    else "Start Drawing"
                ),
            )
        )

        if self.is_video_running:
            self.videoToggler()

        self.is_drawing = False if self.is_drawing else True

        if not self.is_video_running:
            if self.is_drawing:
                self.timer.start(30)
            else:
                self.timer.stop()

    def videoLoadedSlot(self, path):
        # checking for path existance and validity
        if not path:
            return

        self.video_path = path
        logging.info(f'loading video : {self.video_path}')

        self.initCap()


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()
        self.initUI()

    def initUI(self):
        self.setWindowTitle("Vehicle counting system")
        self.setGeometry(100, 100, 900, 600)  # Set initial window size and position

        # Enable mouse tracking
        # Create an instance of your App widget
        self.app = App()

        # Set App widget as the central widget of MainWindow
        self.setCentralWidget(self.app)


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.show()
    # window.app.timer.start(30)
    sys.exit(app.exec_())
