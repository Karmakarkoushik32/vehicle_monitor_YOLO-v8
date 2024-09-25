import sys
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QComboBox, QTextEdit, QLineEdit, QLabel, QFileDialog
from PyQt5.QtCore import pyqtSignal, QObject

class VideoFileLodingWidget(QWidget):
    videoLoaded = pyqtSignal(str)  
    
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.setWindowTitle('File Option Chooser')

        main_layout = QVBoxLayout(self)

        self.fileOptionCombo = QComboBox(self)
        self.fileOptionCombo.addItem('From File')
        self.fileOptionCombo.addItem('From HTTP Stream')
        self.fileOptionCombo.setCurrentIndex(0)
        self.fileOptionCombo.currentIndexChanged.connect(self.onComboBoxChanged)

        self.urlTextEdit = QTextEdit(self)
        self.urlTextEdit.setPlaceholderText('Enter HTTP URL')
        self.urlTextEdit.hide()

        self.fileLineEdit = QLineEdit(self)
        self.fileLineEdit.setReadOnly(True)
        self.fileLineEdit.setPlaceholderText('Selected file path')

        self.fileChooseButton = QPushButton('Choose File', self)
        self.fileChooseButton.clicked.connect(self.chooseFile)

        button_layout = QHBoxLayout()

        self.cancelButton = QPushButton('Cancel', self)
        self.cancelButton.clicked.connect(self.close)

        self.okButton = QPushButton('OK', self)
        self.okButton.clicked.connect(self.onOKClicked)

        button_layout.addWidget(self.cancelButton)
        button_layout.addWidget(self.okButton)

        main_layout.addWidget(self.fileOptionCombo)
        main_layout.addWidget(self.urlTextEdit)
        main_layout.addWidget(self.fileLineEdit)
        main_layout.addWidget(self.fileChooseButton)
        main_layout.addLayout(button_layout)

        self.setLayout(main_layout)

    def onComboBoxChanged(self, index):
        if index == 0:  # From File
            self.urlTextEdit.hide()
            self.fileLineEdit.show()
            self.fileChooseButton.show()
        elif index == 1:  # From HTTP Stream
            self.fileLineEdit.hide()
            self.fileChooseButton.hide()
            self.urlTextEdit.show()

    def chooseFile(self):
        file_dialog = QFileDialog(self)
        file_dialog.setFileMode(QFileDialog.ExistingFile)
        file_dialog.setNameFilter('Video Files (*.avi *.mp4 *.mkv *.mov *.flv *.wmv)')
        if file_dialog.exec_():
            file_path = file_dialog.selectedFiles()[0]
            self.fileLineEdit.setText(file_path)

    def onOKClicked(self):
        selected_option = self.fileOptionCombo.currentText()
        if selected_option == 'From File':
            file_path = self.fileLineEdit.text()

            if file_path:
                self.videoLoaded.emit(file_path)
                print(f'Handling "From File" option with file: {file_path}')
                # Add your logic for handling 'From File' option with file_path
            else:
                print('No file selected.')
        elif selected_option == 'From HTTP Stream':
            file_path = self.urlTextEdit.toPlainText().strip()
            if file_path:
                self.videoLoaded.emit(file_path)
                print(f'Handling "From HTTP Stream" option with URL: {file_path}')
                # TODO add a message thah
                # Add your logic for handling 'From HTTP Stream' option with url
            else:
                print('No URL entered.')

        self.close()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    widget = VideoFileLodingWidget()
    widget.show()
    sys.exit(app.exec_())
