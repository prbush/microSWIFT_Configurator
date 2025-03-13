#!/usr/bin/python3
from datetime import datetime
import os
import platform
import struct
import sys

from PyQt6 import QtCore, QtGui, QtWidgets
import serial.tools.list_ports
import re
import subprocess

from PyQt6.QtGui import QTextCharFormat, QColor
from PyQt6.QtWidgets import QGraphicsScene, QGraphicsPixmapItem
from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import pyqtSignal, QThread

FIRMWARE_MAJOR_VERSION = 2
FIRMWARE_MINOR_VERSION = 2


# Add file save button that saves configuration and the output of STM programmer.

class Worker(QThread):
    finished = pyqtSignal()
    stdoutAvailable = pyqtSignal(str)
    stderrAvailable = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)

    def run(self):
        firmwareBurnSuccessful = False
        systemOS = platform.system()

        if systemOS == "Darwin":  # MacOS
            programmerPath = ("/Applications/STMicroelectronics/STM32Cube/STM32CubeProgrammer/"
                              "STM32CubeProgrammer.app/Contents/MacOs/bin/STM32_Programmer_CLI")
        else:  # Windows
            programmerPath = ("C:\\Program Files\\STMicroelectronics\\STM32Cube\\STM32CubeProgrammer\\bin"
                              "\\STM32_Programmer_CLI.exe")

        # Define the command to run STM32CubeProgrammer
        command = [
            programmerPath,
            "--connect", "port=SWD",  # Specify the port (e.g., USB, JTAG)
            "--download", "firmware/microSWIFT_V2.2.elf",  # Firmware file to write to the device
            "0x08000000",  # download address
            "--verify",  # Verify after programming
        ]

        # command = [programmerPath,"--connect"]

        # Burn the firmware first
        try:
            process = subprocess.Popen(command, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            # Do other work while the subprocess is running
            while process.poll() is None:
                # Retrieve output (if needed)
                stdout, stderr = process.communicate()

                if stdout:
                    cleanedText = re.sub(r'\x1b\[[0-9;]*[mG]', '', stdout)
                    self.stdoutAvailable.emit(cleanedText)

            if process.returncode == 0:
                firmwareBurnSuccessful = True
            else:
                self.stderrAvailable.emit(f"\nProgramming Failed with code {process.returncode}")
                firmwareBurnSuccessful = False

        except subprocess.CalledProcessError as e:
            # If there's an error, show the error message
            self.stderrAvailable.emit(f"/nError: {e.stderr}")
            self.stderrAvailable.emit(e.stdout)
            firmwareBurnSuccessful = False
        except Exception as e:
            self.writeError(f"Unexpected error: {str(e)}")
            firmwareBurnSuccessful = False

        if firmwareBurnSuccessful:
            command = [
                programmerPath,
                "--connect", "port=SWD",  # Specify the port (e.g., USB, JTAG)
                "--download", "firmware/config.bin",  # Firmware file to write to the device
                "0x083FFC00",  # download address
                "--verify",  # Verify after programming
                "--start", "0x08000000"  # Start after programming and verification (at address 0x08000000)
            ]

            # Burn the configuration bytes
            try:
                process = subprocess.Popen(command, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

                # Do other work while the subprocess is running
                while process.poll() is None:
                    # Retrieve output (if needed)
                    stdout, stderr = process.communicate()

                    if stdout:
                        cleanedText = re.sub(r'\x1b\[[0-9;]*[mG]', '', stdout)
                        self.stdoutAvailable.emit(cleanedText)

                if process.returncode != 0:
                    self.stderrAvailable.emit(f"\nProgramming Failed with code {process.returncode}")

            except subprocess.CalledProcessError as e:
                # If there's an error, show the error message
                self.stderrAvailable.emit(f"/nError: {e.stderr}")
                self.stderrAvailable.emit(e.stdout)
            except Exception as e:
                self.writeError(f"Unexpected error: {str(e)}")


        self.finished.emit()


class Ui_MainWindow(object):
    device_connected = False
    stlink_port = ""
    configFilePath = "firmware/config.bin"

    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(640, 800)
        self.centralwidget = QtWidgets.QWidget(parent=MainWindow)
        self.centralwidget.setObjectName("centralwidget")
        self.ctFrame = QtWidgets.QFrame(parent=self.centralwidget)
        self.ctFrame.setGeometry(QtCore.QRect(10, 10, 301, 80))
        self.ctFrame.setFrameShape(QtWidgets.QFrame.Shape.StyledPanel)
        self.ctFrame.setFrameShadow(QtWidgets.QFrame.Shadow.Raised)
        self.ctFrame.setObjectName("ctFrame")
        self.layoutWidget = QtWidgets.QWidget(parent=self.ctFrame)
        self.layoutWidget.setGeometry(QtCore.QRect(10, 10, 281, 61))
        self.layoutWidget.setObjectName("layoutWidget")
        self.ctVertLayout = QtWidgets.QVBoxLayout(self.layoutWidget)
        self.ctVertLayout.setContentsMargins(0, 0, 0, 0)
        self.ctVertLayout.setObjectName("ctVertLayout")
        self.ctEnableButton = QtWidgets.QRadioButton(parent=self.layoutWidget)
        font = QtGui.QFont()
        font.setPointSize(12)
        self.ctEnableButton.setFont(font)
        self.ctEnableButton.setObjectName("ctEnableButton")
        self.ctVertLayout.addWidget(self.ctEnableButton)
        self.ctHorizLayout = QtWidgets.QHBoxLayout()
        self.ctHorizLayout.setObjectName("ctHorizLayout")
        self.ctNumSamplesLabel = QtWidgets.QLabel(parent=self.layoutWidget)
        self.ctNumSamplesLabel.setEnabled(False)
        font = QtGui.QFont()
        font.setPointSize(12)
        self.ctNumSamplesLabel.setFont(font)
        self.ctNumSamplesLabel.setObjectName("ctNumSamplesLabel")
        self.ctHorizLayout.addWidget(self.ctNumSamplesLabel)
        self.ctNumSamplesSpinBox = QtWidgets.QSpinBox(parent=self.layoutWidget)
        self.ctNumSamplesSpinBox.setEnabled(False)
        font = QtGui.QFont()
        font.setPointSize(12)
        self.ctNumSamplesSpinBox.setFont(font)
        self.ctNumSamplesSpinBox.setMinimum(1)
        self.ctNumSamplesSpinBox.setMaximum(1000)
        self.ctNumSamplesSpinBox.setProperty("value", 10)
        self.ctNumSamplesSpinBox.setObjectName("ctNumSamplesSpinBox")
        self.ctHorizLayout.addWidget(self.ctNumSamplesSpinBox)
        self.ctVertLayout.addLayout(self.ctHorizLayout)
        self.tempFrame = QtWidgets.QFrame(parent=self.centralwidget)
        self.tempFrame.setGeometry(QtCore.QRect(10, 100, 301, 80))
        self.tempFrame.setFrameShape(QtWidgets.QFrame.Shape.StyledPanel)
        self.tempFrame.setFrameShadow(QtWidgets.QFrame.Shadow.Raised)
        self.tempFrame.setObjectName("tempFrame")
        self.layoutWidget_6 = QtWidgets.QWidget(parent=self.tempFrame)
        self.layoutWidget_6.setGeometry(QtCore.QRect(10, 10, 281, 61))
        self.layoutWidget_6.setObjectName("layoutWidget_6")
        self.tempVertLayout = QtWidgets.QVBoxLayout(self.layoutWidget_6)
        self.tempVertLayout.setContentsMargins(0, 0, 0, 0)
        self.tempVertLayout.setObjectName("tempVertLayout")
        self.tempEnableButton = QtWidgets.QRadioButton(parent=self.layoutWidget_6)
        font = QtGui.QFont()
        font.setPointSize(12)
        self.tempEnableButton.setFont(font)
        self.tempEnableButton.setObjectName("tempEnableButton")
        self.tempVertLayout.addWidget(self.tempEnableButton)
        self.tempHorizLayout = QtWidgets.QHBoxLayout()
        self.tempHorizLayout.setObjectName("tempHorizLayout")
        self.tempNumSamplesLabel = QtWidgets.QLabel(parent=self.layoutWidget_6)
        self.tempNumSamplesLabel.setEnabled(False)
        font = QtGui.QFont()
        font.setPointSize(12)
        self.tempNumSamplesLabel.setFont(font)
        self.tempNumSamplesLabel.setObjectName("tempNumSamplesLabel")
        self.tempHorizLayout.addWidget(self.tempNumSamplesLabel)
        self.tempNumSamplesSpinBox = QtWidgets.QSpinBox(parent=self.layoutWidget_6)
        self.tempNumSamplesSpinBox.setEnabled(False)
        font = QtGui.QFont()
        font.setPointSize(12)
        self.tempNumSamplesSpinBox.setFont(font)
        self.tempNumSamplesSpinBox.setMinimum(1)
        self.tempNumSamplesSpinBox.setMaximum(1000)
        self.tempNumSamplesSpinBox.setProperty("value", 10)
        self.tempNumSamplesSpinBox.setObjectName("tempNumSamplesSpinBox")
        self.tempHorizLayout.addWidget(self.tempNumSamplesSpinBox)
        self.tempVertLayout.addLayout(self.tempHorizLayout)
        self.lightFrame = QtWidgets.QFrame(parent=self.centralwidget)
        self.lightFrame.setGeometry(QtCore.QRect(10, 190, 301, 81))
        self.lightFrame.setFrameShape(QtWidgets.QFrame.Shape.StyledPanel)
        self.lightFrame.setFrameShadow(QtWidgets.QFrame.Shadow.Raised)
        self.lightFrame.setObjectName("lightFrame")
        self.layoutWidget1 = QtWidgets.QWidget(parent=self.lightFrame)
        self.layoutWidget1.setGeometry(QtCore.QRect(10, 11, 286, 61))
        self.layoutWidget1.setObjectName("layoutWidget1")
        self.lightVerticalLayout = QtWidgets.QVBoxLayout(self.layoutWidget1)
        self.lightVerticalLayout.setContentsMargins(0, 0, 0, 0)
        self.lightVerticalLayout.setObjectName("lightVerticalLayout")
        self.lightEnableHorizLayout = QtWidgets.QHBoxLayout()
        self.lightEnableHorizLayout.setObjectName("lightEnableHorizLayout")
        self.lightEnableButton = QtWidgets.QRadioButton(parent=self.layoutWidget1)
        font = QtGui.QFont()
        font.setPointSize(12)
        self.lightEnableButton.setFont(font)
        self.lightEnableButton.setObjectName("lightEnableButton")
        self.lightEnableHorizLayout.addWidget(self.lightEnableButton)
        self.lightMatchGNSSCheckbox = QtWidgets.QCheckBox(parent=self.layoutWidget1)
        self.lightMatchGNSSCheckbox.setEnabled(False)
        font = QtGui.QFont()
        font.setPointSize(12)
        self.lightMatchGNSSCheckbox.setFont(font)
        self.lightMatchGNSSCheckbox.setObjectName("lightMatchGNSSCheckbox")
        self.lightEnableHorizLayout.addWidget(self.lightMatchGNSSCheckbox)
        self.lightVerticalLayout.addLayout(self.lightEnableHorizLayout)
        self.lightSamplesHorizLayout = QtWidgets.QHBoxLayout()
        self.lightSamplesHorizLayout.setObjectName("lightSamplesHorizLayout")
        self.lightNumSamplesLabel = QtWidgets.QLabel(parent=self.layoutWidget1)
        self.lightNumSamplesLabel.setEnabled(False)
        font = QtGui.QFont()
        font.setPointSize(12)
        self.lightNumSamplesLabel.setFont(font)
        self.lightNumSamplesLabel.setObjectName("lightNumSamplesLabel")
        self.lightSamplesHorizLayout.addWidget(self.lightNumSamplesLabel)
        self.lightNumSamplesSpinBox = QtWidgets.QSpinBox(parent=self.layoutWidget1)
        self.lightNumSamplesSpinBox.setEnabled(False)
        font = QtGui.QFont()
        font.setPointSize(12)
        self.lightNumSamplesSpinBox.setFont(font)
        self.lightNumSamplesSpinBox.setMinimum(1)
        self.lightNumSamplesSpinBox.setMaximum(1800)
        self.lightNumSamplesSpinBox.setProperty("value", 512)
        self.lightNumSamplesSpinBox.setObjectName("lightNumSamplesSpinBox")
        self.lightSamplesHorizLayout.addWidget(self.lightNumSamplesSpinBox)
        self.lightVerticalLayout.addLayout(self.lightSamplesHorizLayout)
        self.iridiumFrame = QtWidgets.QFrame(parent=self.centralwidget)
        self.iridiumFrame.setGeometry(QtCore.QRect(10, 370, 301, 80))
        self.iridiumFrame.setFrameShape(QtWidgets.QFrame.Shape.StyledPanel)
        self.iridiumFrame.setFrameShadow(QtWidgets.QFrame.Shadow.Raised)
        self.iridiumFrame.setObjectName("iridiumFrame")
        self.layoutWidget2 = QtWidgets.QWidget(parent=self.iridiumFrame)
        self.layoutWidget2.setGeometry(QtCore.QRect(10, 10, 281, 61))
        self.layoutWidget2.setObjectName("layoutWidget2")
        self.iridiumVertLayout = QtWidgets.QVBoxLayout(self.layoutWidget2)
        self.iridiumVertLayout.setContentsMargins(0, 0, 0, 0)
        self.iridiumVertLayout.setObjectName("iridiumVertLayout")
        self.iridiumTxTimeHorizLayout = QtWidgets.QHBoxLayout()
        self.iridiumTxTimeHorizLayout.setObjectName("iridiumTxTimeHorizLayout")
        self.iridiumTxTimeLabel = QtWidgets.QLabel(parent=self.layoutWidget2)
        font = QtGui.QFont()
        font.setPointSize(12)
        self.iridiumTxTimeLabel.setFont(font)
        self.iridiumTxTimeLabel.setObjectName("iridiumTxTimeLabel")
        self.iridiumTxTimeHorizLayout.addWidget(self.iridiumTxTimeLabel)
        self.iridiumTxTimeSpinBox = QtWidgets.QSpinBox(parent=self.layoutWidget2)
        font = QtGui.QFont()
        font.setPointSize(12)
        self.iridiumTxTimeSpinBox.setFont(font)
        self.iridiumTxTimeSpinBox.setMinimum(2)
        self.iridiumTxTimeSpinBox.setMaximum(60)
        self.iridiumTxTimeSpinBox.setProperty("value", 5)
        self.iridiumTxTimeSpinBox.setObjectName("iridiumTxTimeSpinBox")
        self.iridiumTxTimeHorizLayout.addWidget(self.iridiumTxTimeSpinBox)
        self.iridiumVertLayout.addLayout(self.iridiumTxTimeHorizLayout)
        self.iridiumTypeHorizLayoutr = QtWidgets.QHBoxLayout()
        self.iridiumTypeHorizLayoutr.setObjectName("iridiumTypeHorizLayoutr")
        self.iridiumTypeComboBox = QtWidgets.QComboBox(parent=self.layoutWidget2)
        font = QtGui.QFont()
        font.setPointSize(12)
        self.iridiumTypeComboBox.setFont(font)
        self.iridiumTypeComboBox.setObjectName("iridiumTypeComboBox")
        self.iridiumTypeHorizLayoutr.addWidget(self.iridiumTypeComboBox)
        self.iridiumTypeLabel = QtWidgets.QLabel(parent=self.layoutWidget2)
        font = QtGui.QFont()
        font.setPointSize(12)
        self.iridiumTypeLabel.setFont(font)
        self.iridiumTypeLabel.setObjectName("iridiumTypeLabel")
        self.iridiumTypeHorizLayoutr.addWidget(self.iridiumTypeLabel)
        self.iridiumVertLayout.addLayout(self.iridiumTypeHorizLayoutr)
        self.gnssFrame = QtWidgets.QFrame(parent=self.centralwidget)
        self.gnssFrame.setGeometry(QtCore.QRect(10, 459, 301, 111))
        self.gnssFrame.setFrameShape(QtWidgets.QFrame.Shape.StyledPanel)
        self.gnssFrame.setFrameShadow(QtWidgets.QFrame.Shadow.Raised)
        self.gnssFrame.setObjectName("gnssFrame")
        self.layoutWidget_11 = QtWidgets.QWidget(parent=self.gnssFrame)
        self.layoutWidget_11.setGeometry(QtCore.QRect(10, 10, 281, 90))
        self.layoutWidget_11.setObjectName("layoutWidget_11")
        self.gnssVertLayout = QtWidgets.QVBoxLayout(self.layoutWidget_11)
        self.gnssVertLayout.setContentsMargins(0, 0, 0, 0)
        self.gnssVertLayout.setObjectName("gnssVertLayout")
        self.gnssSamplesHorizLayout = QtWidgets.QHBoxLayout()
        self.gnssSamplesHorizLayout.setObjectName("gnssSamplesHorizLayout")
        self.gnssNumSamplesLabel = QtWidgets.QLabel(parent=self.layoutWidget_11)
        font = QtGui.QFont()
        font.setPointSize(12)
        self.gnssNumSamplesLabel.setFont(font)
        self.gnssNumSamplesLabel.setObjectName("gnssNumSamplesLabel")
        self.gnssSamplesHorizLayout.addWidget(self.gnssNumSamplesLabel)
        self.gnssNumSamplesSpinBox = QtWidgets.QSpinBox(parent=self.layoutWidget_11)
        font = QtGui.QFont()
        font.setPointSize(12)
        self.gnssNumSamplesSpinBox.setFont(font)
        self.gnssNumSamplesSpinBox.setMinimum(1024)
        self.gnssNumSamplesSpinBox.setMaximum(32768)
        self.gnssNumSamplesSpinBox.setProperty("value", 4096)
        self.gnssNumSamplesSpinBox.setObjectName("gnssNumSamplesSpinBox")
        self.gnssSamplesHorizLayout.addWidget(self.gnssNumSamplesSpinBox)
        self.gnssVertLayout.addLayout(self.gnssSamplesHorizLayout)
        self.gnssHighPerformanceModeCheckBox = QtWidgets.QCheckBox(parent=self.layoutWidget_11)
        self.gnssHighPerformanceModeCheckBox.setObjectName("gnssHighPerformanceModeCheckBox")
        self.gnssVertLayout.addWidget(self.gnssHighPerformanceModeCheckBox)
        self.gnssSampleRateHorizLayout = QtWidgets.QHBoxLayout()
        self.gnssSampleRateHorizLayout.setObjectName("gnssSampleRateHorizLayout")
        self.gnssSampleRateComboBox = QtWidgets.QComboBox(parent=self.layoutWidget_11)
        font = QtGui.QFont()
        font.setPointSize(12)
        self.gnssSampleRateComboBox.setFont(font)
        self.gnssSampleRateComboBox.setObjectName("gnssSampleRateComboBox")
        self.gnssSampleRateHorizLayout.addWidget(self.gnssSampleRateComboBox)
        self.gnssSampleRateLabel = QtWidgets.QLabel(parent=self.layoutWidget_11)
        font = QtGui.QFont()
        font.setPointSize(12)
        self.gnssSampleRateLabel.setFont(font)
        self.gnssSampleRateLabel.setObjectName("gnssSampleRateLabel")
        self.gnssSampleRateHorizLayout.addWidget(self.gnssSampleRateLabel)
        self.gnssVertLayout.addLayout(self.gnssSampleRateHorizLayout)
        self.timingFrame = QtWidgets.QFrame(parent=self.centralwidget)
        self.timingFrame.setGeometry(QtCore.QRect(330, 250, 291, 161))
        self.timingFrame.setFrameShape(QtWidgets.QFrame.Shape.StyledPanel)
        self.timingFrame.setFrameShadow(QtWidgets.QFrame.Shadow.Raised)
        self.timingFrame.setObjectName("timingFrame")
        self.verticalLayoutWidget = QtWidgets.QWidget(parent=self.timingFrame)
        self.verticalLayoutWidget.setGeometry(QtCore.QRect(10, 10, 271, 141))
        self.verticalLayoutWidget.setObjectName("verticalLayoutWidget")
        self.timingVertLayout = QtWidgets.QVBoxLayout(self.verticalLayoutWidget)
        self.timingVertLayout.setContentsMargins(0, 0, 0, 0)
        self.timingVertLayout.setObjectName("timingVertLayout")
        self.dutyCycleHorizLayout = QtWidgets.QHBoxLayout()
        self.dutyCycleHorizLayout.setObjectName("dutyCycleHorizLayout")
        self.dutyCycleLabel = QtWidgets.QLabel(parent=self.verticalLayoutWidget)
        font = QtGui.QFont()
        font.setPointSize(12)
        self.dutyCycleLabel.setFont(font)
        self.dutyCycleLabel.setObjectName("dutyCycleLabel")
        self.dutyCycleHorizLayout.addWidget(self.dutyCycleLabel)
        self.dutyCycleSpinBox = QtWidgets.QSpinBox(parent=self.verticalLayoutWidget)
        font = QtGui.QFont()
        font.setPointSize(12)
        self.dutyCycleSpinBox.setFont(font)
        self.dutyCycleSpinBox.setMaximum(1440)
        self.dutyCycleSpinBox.setProperty("value", 30)
        self.dutyCycleSpinBox.setObjectName("dutyCycleSpinBox")
        self.dutyCycleHorizLayout.addWidget(self.dutyCycleSpinBox)
        self.timingVertLayout.addLayout(self.dutyCycleHorizLayout)
        self.gnssBufferTimeHorizLayout = QtWidgets.QHBoxLayout()
        self.gnssBufferTimeHorizLayout.setObjectName("gnssBufferTimeHorizLayout")
        self.gnssMaxAcqusitionTimeLabel = QtWidgets.QLabel(parent=self.verticalLayoutWidget)
        font = QtGui.QFont()
        font.setPointSize(12)
        self.gnssMaxAcqusitionTimeLabel.setFont(font)
        self.gnssMaxAcqusitionTimeLabel.setWhatsThis("")
        self.gnssMaxAcqusitionTimeLabel.setObjectName("gnssMaxAcqusitionTimeLabel")
        self.gnssBufferTimeHorizLayout.addWidget(self.gnssMaxAcqusitionTimeLabel)
        self.gnssMaxAcquisitionTimeSpinBox = QtWidgets.QSpinBox(parent=self.verticalLayoutWidget)
        font = QtGui.QFont()
        font.setPointSize(12)
        self.gnssMaxAcquisitionTimeSpinBox.setFont(font)
        self.gnssMaxAcquisitionTimeSpinBox.setWhatsThis("")
        self.gnssMaxAcquisitionTimeSpinBox.setMaximum(30)
        self.gnssMaxAcquisitionTimeSpinBox.setMinimum(1)
        self.gnssMaxAcquisitionTimeSpinBox.setProperty("value", 5)
        self.gnssMaxAcquisitionTimeSpinBox.setObjectName("gnssMaxAcquisitionTimeSpinBox")
        self.gnssBufferTimeHorizLayout.addWidget(self.gnssMaxAcquisitionTimeSpinBox)
        self.timingVertLayout.addLayout(self.gnssBufferTimeHorizLayout)
        self.trackingNumberHorizLayourt = QtWidgets.QHBoxLayout()
        self.trackingNumberHorizLayourt.setObjectName("trackingNumberHorizLayourt")
        self.trackingNumberLabel = QtWidgets.QLabel(parent=self.verticalLayoutWidget)
        font = QtGui.QFont()
        font.setPointSize(12)
        self.trackingNumberLabel.setFont(font)
        self.trackingNumberLabel.setObjectName("trackingNumberLabel")
        self.trackingNumberHorizLayourt.addWidget(self.trackingNumberLabel)
        self.trackingNumberSpinBox = QtWidgets.QSpinBox(parent=self.verticalLayoutWidget)
        font = QtGui.QFont()
        font.setPointSize(12)
        self.trackingNumberSpinBox.setFont(font)
        self.trackingNumberSpinBox.setMaximum(1000)
        self.trackingNumberSpinBox.setProperty("value", 100)
        self.trackingNumberSpinBox.setObjectName("trackingNumberSpinBox")
        self.trackingNumberHorizLayourt.addWidget(self.trackingNumberSpinBox)
        self.timingVertLayout.addLayout(self.trackingNumberHorizLayourt)
        self.graphicsView = QtWidgets.QGraphicsView(parent=self.centralwidget)
        self.graphicsView.setGeometry(QtCore.QRect(320, 10, 311, 231))
        self.graphicsView.setObjectName("graphicsView")
        self.statusAndProgFrame = QtWidgets.QFrame(parent=self.centralwidget)
        self.statusAndProgFrame.setGeometry(QtCore.QRect(340, 430, 271, 141))
        self.statusAndProgFrame.setFrameShape(QtWidgets.QFrame.Shape.StyledPanel)
        self.statusAndProgFrame.setFrameShadow(QtWidgets.QFrame.Shadow.Raised)
        self.statusAndProgFrame.setObjectName("statusAndProgFrame")
        self.layoutWidget3 = QtWidgets.QWidget(parent=self.statusAndProgFrame)
        self.layoutWidget3.setGeometry(QtCore.QRect(10, 10, 251, 121))
        self.layoutWidget3.setObjectName("layoutWidget3")
        self.statusAndProgVertLayout = QtWidgets.QVBoxLayout(self.layoutWidget3)
        self.statusAndProgVertLayout.setContentsMargins(0, 0, 0, 0)
        self.statusAndProgVertLayout.setObjectName("statusAndProgVertLayout")
        self.devicePortLabel = QtWidgets.QLabel(parent=self.layoutWidget3)
        self.devicePortLabel.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.devicePortLabel.setObjectName("devicePortLabel")
        self.statusAndProgVertLayout.addWidget(self.devicePortLabel)
        self.verifyButton = QtWidgets.QPushButton(parent=self.layoutWidget3)
        font = QtGui.QFont()
        font.setPointSize(12)
        self.verifyButton.setFont(font)
        self.verifyButton.setObjectName("verifyButton")
        self.statusAndProgVertLayout.addWidget(self.verifyButton)
        self.programButton = QtWidgets.QPushButton(parent=self.layoutWidget3)
        font = QtGui.QFont()
        font.setPointSize(12)
        self.programButton.setFont(font)
        self.programButton.setObjectName("programButton")
        self.statusAndProgVertLayout.addWidget(self.programButton)
        self.turbidityFrame = QtWidgets.QFrame(parent=self.centralwidget)
        self.turbidityFrame.setGeometry(QtCore.QRect(10, 280, 301, 81))
        self.turbidityFrame.setFrameShape(QtWidgets.QFrame.Shape.StyledPanel)
        self.turbidityFrame.setFrameShadow(QtWidgets.QFrame.Shadow.Raised)
        self.turbidityFrame.setObjectName("turbidityFrame")
        self.layoutWidget_2 = QtWidgets.QWidget(parent=self.turbidityFrame)
        self.layoutWidget_2.setGeometry(QtCore.QRect(10, 11, 286, 61))
        self.layoutWidget_2.setObjectName("layoutWidget_2")
        self.turbidityVerticalLayout = QtWidgets.QVBoxLayout(self.layoutWidget_2)
        self.turbidityVerticalLayout.setContentsMargins(0, 0, 0, 0)
        self.turbidityVerticalLayout.setObjectName("turbidityVerticalLayout")
        self.turbidityEnableHorizLayout = QtWidgets.QHBoxLayout()
        self.turbidityEnableHorizLayout.setObjectName("turbidityEnableHorizLayout")
        self.turbidityEnableButton = QtWidgets.QRadioButton(parent=self.layoutWidget_2)
        font = QtGui.QFont()
        font.setPointSize(12)
        self.turbidityEnableButton.setFont(font)
        self.turbidityEnableButton.setObjectName("turbidityEnableButton")
        self.turbidityEnableHorizLayout.addWidget(self.turbidityEnableButton)
        self.turbidityMatchGNSSCheckbox = QtWidgets.QCheckBox(parent=self.layoutWidget_2)
        self.turbidityMatchGNSSCheckbox.setEnabled(False)
        font = QtGui.QFont()
        font.setPointSize(12)
        self.turbidityMatchGNSSCheckbox.setFont(font)
        self.turbidityMatchGNSSCheckbox.setObjectName("turbidityMatchGNSSCheckbox")
        self.turbidityEnableHorizLayout.addWidget(self.turbidityMatchGNSSCheckbox)
        self.turbidityVerticalLayout.addLayout(self.turbidityEnableHorizLayout)
        self.turbiditySamplesHorizLayout = QtWidgets.QHBoxLayout()
        self.turbiditySamplesHorizLayout.setObjectName("turbiditySamplesHorizLayout")
        self.turbidityNumSamplesLabel = QtWidgets.QLabel(parent=self.layoutWidget_2)
        self.turbidityNumSamplesLabel.setEnabled(False)
        font = QtGui.QFont()
        font.setPointSize(12)
        self.turbidityNumSamplesLabel.setFont(font)
        self.turbidityNumSamplesLabel.setObjectName("turbidityNumSamplesLabel")
        self.turbiditySamplesHorizLayout.addWidget(self.turbidityNumSamplesLabel)
        self.turbidityNumSamplesSpinBox = QtWidgets.QSpinBox(parent=self.layoutWidget_2)
        self.turbidityNumSamplesSpinBox.setEnabled(False)
        font = QtGui.QFont()
        font.setPointSize(12)
        self.turbidityNumSamplesSpinBox.setFont(font)
        self.turbidityNumSamplesSpinBox.setMinimum(1)
        self.turbidityNumSamplesSpinBox.setMaximum(3600)
        self.turbidityNumSamplesSpinBox.setProperty("value", 1024)
        self.turbidityNumSamplesSpinBox.setObjectName("turbidityNumSamplesSpinBox")
        self.turbiditySamplesHorizLayout.addWidget(self.turbidityNumSamplesSpinBox)
        self.turbidityVerticalLayout.addLayout(self.turbiditySamplesHorizLayout)
        self.statusTextEdit = QtWidgets.QTextEdit(parent=self.centralwidget)
        self.statusTextEdit.setGeometry(QtCore.QRect(10, 580, 621, 211))
        self.statusTextEdit.setObjectName("statusTextEdit")

        # Added functionality
        self.worker = Worker()
        self.thread = QThread()
        self.worker.moveToThread(self.thread)
        self.scene = QGraphicsScene()

        self.disableAllOptionalSensors()
        self.connectUIElements()
        self.fillComboBoxes()
        self.find_usb_port()
        self.displayPicture()

        MainWindow.setCentralWidget(self.centralwidget)

        self.retranslateUi(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "microSWIFT Configurator"))
        self.ctEnableButton.setText(_translate("MainWindow", "Enable CT"))
        self.ctNumSamplesLabel.setText(_translate("MainWindow", "Number of samples to average"))
        self.tempEnableButton.setText(_translate("MainWindow", "Enable Temperature"))
        self.tempNumSamplesLabel.setText(_translate("MainWindow", "Number of samples to average"))
        self.lightEnableButton.setText(_translate("MainWindow", "Enable Light"))
        self.lightMatchGNSSCheckbox.setText(_translate("MainWindow", "Match GNSS period"))
        self.lightNumSamplesLabel.setText(_translate("MainWindow", "Number of samples @ 0.5Hz"))
        self.iridiumTxTimeLabel.setText(_translate("MainWindow", "Iridium transmit time in mins"))
        self.iridiumTypeLabel.setText(_translate("MainWindow", "Iridium Modem Type"))
        self.gnssNumSamplesLabel.setText(_translate("MainWindow", "Number of GNSS samples"))
        self.gnssHighPerformanceModeCheckBox.setText(_translate("MainWindow", "Enable GNSS high performance mode"))
        self.gnssSampleRateLabel.setText(_translate("MainWindow", "GNSS Sampling Rate"))
        self.dutyCycleLabel.setText(_translate("MainWindow", "Total Duty Cycle (mins)"))
        self.gnssMaxAcqusitionTimeLabel.setText(_translate("MainWindow", "GNSS max time to fix (mins)"))
        self.trackingNumberLabel.setText(_translate("MainWindow", "microSWIFT Tracking number"))
        self.verifyButton.setText(_translate("MainWindow", "Verify"))
        self.programButton.setText(_translate("MainWindow", "Program"))
        self.turbidityEnableButton.setText(_translate("MainWindow", "Enable Turbidity"))
        self.turbidityMatchGNSSCheckbox.setText(_translate("MainWindow", "Match GNSS period"))
        self.turbidityNumSamplesLabel.setText(_translate("MainWindow", "Number of samples @ 1Hz"))

    def assembleBinaryConfigFile(self):
        get_int_from_str = lambda s: int(re.search(r'\d+', s).group()) if re.search(r'\d+', s) else None

        with open(self.configFilePath, "wb") as configFile:
            '''
            
            Definition of configuration struct from configuration.h in firmware files

            typedef struct microSWIFT_configuration
            {
              uint32_t tracking_number;
              uint32_t samples_per_window;
              uint32_t duty_cycle;
              uint32_t iridium_max_transmit_time;
              uint32_t gnss_max_acquisition_wait_time;
              uint32_t gnss_sampling_rate;
              uint32_t total_ct_samples;
              uint32_t total_temp_samples;
              uint32_t total_light_samples;
              uint32_t total_turbidity_samples;

              bool iridium_v3f;
              bool gnss_high_performance_mode;
              bool ct_enabled;
              bool temperature_enabled;
              bool light_enabled;
              bool turbidity_enabled;
            } microSWIFT_configuration;
            
            In microSWIFT.ld:
            
              .uservars :
              {
                /* Variables contained in type microSWIFT_configuration contained in configuration.h */
                KEEP(*(.uservars.TRACKING_NUMBER))
                KEEP(*(.uservars.GNSS_SAMPLES_PER_WINDOW))
                KEEP(*(.uservars.DUTY_CYCLE))
                KEEP(*(.uservars.IRIDIUM_MAX_TX_TIME))
                KEEP(*(.uservars.GNSS_MAX_ACQUISITION_TIME))
                KEEP(*(.uservars.GNSS_SAMPLE_RATE))
                KEEP(*(.uservars.TOTAL_CT_SAMPLES))
                KEEP(*(.uservars.TOTAL_TEMP_SAMPLES))
                KEEP(*(.uservars.TOTAL_LIGHT_SAMPLES))
                KEEP(*(.uservars.TOTAL_TURBIDITY_SAMPLES))
                KEEP(*(.uservars.IRIDIUM_V3F))
                KEEP(*(.uservars.GNSS_HIGH_PERF_MODE))
                KEEP(*(.uservars.CT_ENABLED))
                KEEP(*(.uservars.TEMPERATURE_ENABLED))
                KEEP(*(.uservars.LIGHT_ENABLED))
                KEEP(*(.uservars.TURBIDITY_ENABLED))
                /* Compiled in versioning variables */
                KEEP(*(.uservars.VERSION_NUMBER))
                KEEP(*(.uservars.COMPILATION_DATE))
                KEEP(*(.uservars.COMPILATION_TIME))
                *(.uservars*);
              } > USERVARS
              
            Thus, in totality, the config struct is the first element in the .uservars section, followed by:
            VERSION_NUMBER:= typedef struct {uint8_t major_rev :4; uint8_t minor_rev :4;} microSWIFT_firmware_version_t;
                !! Note this is a single byte for both fields !!
            COMPILATION_DATE:= char[11] in the format "MM/DD/YYYY"
            COMPILATION_TIME:= char[9] in the format "HH:MM:SS"
            '''

            current_datetime = datetime.now()

            # Format the date and time strings
            date = current_datetime.strftime("%m/%d/%Y")  # MM/DD/YYYY
            time = current_datetime.strftime("%H:%M:%S")  # HH:MM:SS
            date += "\x00"  # null terminated
            time += "\x00"  # null terminated

            configStruct = struct.pack("<LLLLLLLLLL??????B11s9s",
                                       int(self.trackingNumberSpinBox.value()),
                                       int(self.gnssNumSamplesSpinBox.value()),
                                       int(self.dutyCycleSpinBox.value()),
                                       int(self.iridiumTxTimeSpinBox.value()),
                                       int(self.gnssMaxAcquisitionTimeSpinBox.value()),
                                       get_int_from_str(self.gnssSampleRateComboBox.currentText()),
                                       int(self.ctNumSamplesSpinBox.value()),
                                       int(self.tempNumSamplesSpinBox.value()),
                                       int(self.lightNumSamplesSpinBox.value()),
                                       int(self.turbidityNumSamplesSpinBox.value()),
                                       bool(self.iridiumTypeComboBox.currentText() == "V3F"),
                                       bool(self.gnssHighPerformanceModeCheckBox.isChecked()),
                                       bool(self.ctEnableButton.isChecked()),
                                       bool(self.tempEnableButton.isChecked()),
                                       bool(self.lightEnableButton.isChecked()),
                                       bool(self.turbidityEnableButton.isChecked()),
                                       int(FIRMWARE_MAJOR_VERSION | (FIRMWARE_MINOR_VERSION << 4)),
                                       bytes(date.encode("utf-8")),
                                       bytes(time.encode("utf-8"))
                                       )

            num_bytes = len(configStruct)
            configFile.write(configStruct)

    def fillComboBoxes(self):
        # Iridium type drop box
        self.iridiumTypeComboBox.addItem("V3D")
        self.iridiumTypeComboBox.addItem("V3F")

        # GNSS sampling ratre drop box
        self.gnssSampleRateComboBox.addItem("4 Hz")
        self.gnssSampleRateComboBox.addItem("5 Hz")

    def disableAllOptionalSensors(self):
        self.ctNumSamplesLabel.setDisabled(True)
        self.ctNumSamplesSpinBox.setDisabled(True)

        self.tempNumSamplesLabel.setDisabled(True)
        self.tempNumSamplesSpinBox.setDisabled(True)

        self.lightNumSamplesLabel.setDisabled(True)
        self.lightNumSamplesSpinBox.setDisabled(True)

        self.turbidityNumSamplesLabel.setDisabled(True)
        self.turbidityNumSamplesSpinBox.setDisabled(True)

        self.programButton.setDisabled(True)

    def connectUIElements(self):
        self.worker.stdoutAvailable.connect(self.appendText)
        self.worker.stderrAvailable.connect(self.appendError)
        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.reenableGUI)
        self.worker.finished.connect(self.threadFinished)

        self.ctEnableButton.clicked.connect(self.onCtEnabledClick)
        self.tempEnableButton.clicked.connect(self.onTempEnabledClick)
        self.lightEnableButton.clicked.connect(self.onLightEnabledClick)
        self.turbidityEnableButton.clicked.connect(self.onTurbidityEnabledClick)
        self.lightMatchGNSSCheckbox.clicked.connect(self.onLightMatchGnssClicked)
        self.turbidityMatchGNSSCheckbox.clicked.connect(self.onTurbidityMatchGnssClicked)

        self.verifyButton.clicked.connect(self.verifySettings)
        self.programButton.clicked.connect(self.programDevice)

        self.ctNumSamplesSpinBox.valueChanged.connect(self.resetVerifyButton)
        self.tempNumSamplesSpinBox.valueChanged.connect(self.resetVerifyButton)
        self.lightNumSamplesSpinBox.valueChanged.connect(self.resetVerifyButton)
        self.turbidityNumSamplesSpinBox.valueChanged.connect(self.resetVerifyButton)
        self.iridiumTxTimeSpinBox.valueChanged.connect(self.resetVerifyButton)
        self.gnssNumSamplesSpinBox.valueChanged.connect(self.resetVerifyButton)
        self.gnssNumSamplesSpinBox.valueChanged.connect(self.onLightMatchGnssClicked)
        self.gnssNumSamplesSpinBox.valueChanged.connect(self.onTurbidityMatchGnssClicked)
        self.gnssSampleRateComboBox.currentIndexChanged.connect(self.onLightMatchGnssClicked)
        self.gnssSampleRateComboBox.currentIndexChanged.connect(self.onTurbidityMatchGnssClicked)
        self.dutyCycleSpinBox.valueChanged.connect(self.resetVerifyButton)
        self.gnssMaxAcquisitionTimeSpinBox.valueChanged.connect(self.resetVerifyButton)
        self.trackingNumberSpinBox.valueChanged.connect(self.resetVerifyButton)

        self.iridiumTypeComboBox.currentIndexChanged.connect(self.resetVerifyButton)
        self.gnssSampleRateComboBox.currentIndexChanged.connect(self.resetVerifyButton)

    def onCtEnabledClick(self):
        if self.ctEnableButton.isChecked():
            self.ctNumSamplesLabel.setEnabled(True)
            self.ctNumSamplesSpinBox.setEnabled(True)
        else:
            self.ctNumSamplesLabel.setDisabled(True)
            self.ctNumSamplesSpinBox.setDisabled(True)

        self.resetVerifyButton()

    def onTempEnabledClick(self):
        if self.tempEnableButton.isChecked():
            self.tempNumSamplesLabel.setEnabled(True)
            self.tempNumSamplesSpinBox.setEnabled(True)
        else:
            self.tempNumSamplesLabel.setDisabled(True)
            self.tempNumSamplesSpinBox.setDisabled(True)

        self.resetVerifyButton()

    def onLightEnabledClick(self):
        if self.lightEnableButton.isChecked():
            self.lightNumSamplesLabel.setEnabled(True)
            self.lightNumSamplesSpinBox.setEnabled(True)
            self.lightMatchGNSSCheckbox.setEnabled(True)
        else:
            self.lightNumSamplesLabel.setDisabled(True)
            self.lightNumSamplesSpinBox.setDisabled(True)
            self.lightMatchGNSSCheckbox.setDisabled(True)

        self.resetVerifyButton()

    def onLightMatchGnssClicked(self):
        get_int_from_str = lambda s: int(re.search(r'\d+', s).group()) if re.search(r'\d+', s) else None
        if self.lightMatchGNSSCheckbox.isChecked():
            self.lightNumSamplesSpinBox.setDisabled(True)
            self.lightNumSamplesSpinBox.setValue(int((self.gnssNumSamplesSpinBox.value() /
                                                     get_int_from_str(self.gnssSampleRateComboBox.currentText()) / 2)))

        self.resetVerifyButton()

    def onTurbidityEnabledClick(self):
        if self.turbidityEnableButton.isChecked():
            self.turbidityNumSamplesLabel.setEnabled(True)
            self.turbidityNumSamplesSpinBox.setEnabled(True)
            self.turbidityMatchGNSSCheckbox.setEnabled(True)
        else:
            self.turbidityNumSamplesLabel.setDisabled(True)
            self.turbidityNumSamplesSpinBox.setDisabled(True)
            self.turbidityMatchGNSSCheckbox.setDisabled(True)

        self.resetVerifyButton()

    def onTurbidityMatchGnssClicked(self):
        get_int_from_str = lambda s: int(re.search(r'\d+', s).group()) if re.search(r'\d+', s) else None
        if self.turbidityMatchGNSSCheckbox.isChecked():
            self.turbidityNumSamplesSpinBox.setDisabled(True)
            self.turbidityNumSamplesSpinBox.setValue(int(self.gnssNumSamplesSpinBox.value() /
                                                         get_int_from_str(self.gnssSampleRateComboBox.currentText())))

        self.resetVerifyButton()

    def find_usb_port(self):
        # Vendor ID and Product ID for STLink V3
        VENDOR_ID = 0x0483  # STMicroelectronics
        PRODUCT_ID = 0x374E  # STLink V3

        # List all available serial ports
        ports = serial.tools.list_ports.comports()

        stlink_ports = []

        for port in ports:
            # Check if the port matches the STLink V3 vendor and product IDs
            if port.vid == VENDOR_ID and port.pid == PRODUCT_ID:
                stlink_ports.append(port.device)
                break

        if stlink_ports:
            for device in stlink_ports:
                self.devicePortLabel.setStyleSheet("font-size: 14px; color: green;")
                self.devicePortLabel.setText(f"STLink V3 found on port {device}")
                self.device_connected = True
                self.stlink_port = device
                break
        else:
            self.devicePortLabel.setStyleSheet("font-size: 14px; color: red;")
            self.devicePortLabel.setText("STLink V3 not found on any USB port.")
            self.device_connected = False
            self.stlink_port = ""

        self.devicePortLabel.setWordWrap(True)

    def verifySettings(self):
        # For getting GNSS sample rate from drop down box
        get_int_from_str = lambda s: int(re.search(r'\d+', s).group()) if re.search(r'\d+', s) else None

        settings_invalid = False
        verify_strings = []

        # Pull all the values from the UI
        ct_enabled = self.ctEnableButton.isChecked()
        ct_num_samples = self.ctNumSamplesSpinBox.value()
        temp_enabled = self.tempEnableButton.isChecked()
        temp_num_samples = self.tempNumSamplesSpinBox.value()
        light_enabled = self.lightEnableButton.isChecked()
        light_num_samples = self.lightNumSamplesSpinBox.value()
        turbidity_enabled = self.turbidityEnableButton.isChecked()
        turbidity_num_samples = self.turbidityNumSamplesSpinBox.value()
        iridium_tx_time = self.iridiumTxTimeSpinBox.value()
        num_gnss_samples = self.gnssNumSamplesSpinBox.value()
        gnss_sample_rate = get_int_from_str(self.gnssSampleRateComboBox.currentText())
        duty_cycle = self.dutyCycleSpinBox.value()
        gnss_window_buffer = self.gnssMaxAcquisitionTimeSpinBox.value()

        gnss_duration = (((num_gnss_samples / gnss_sample_rate) / 60) + 1) + gnss_window_buffer

        if (duty_cycle - gnss_duration - iridium_tx_time) < 0:
            verify_strings.append("Duty cycle not long enough to complete GNSS sample window.\n")
            settings_invalid = True

        if ct_enabled and ((((ct_num_samples * 2) + 20) / 60) > 2):
            verify_strings.append("CT sampling window greater than allotted time of 2 mins.\n")
            settings_invalid = True

        if light_enabled:
            if ((duty_cycle - ((light_num_samples / 30) + 1) - iridium_tx_time) < 0):
                verify_strings.append("Duty cycle not long enough to complete Light sample window.\n")
                settings_invalid = True
            if (int((self.gnssNumSamplesSpinBox.value() / get_int_from_str(self.gnssSampleRateComboBox.currentText())
                     / 2)) > 1800):
                verify_strings.append("Max number of light samples is 1800.\n")
                settings_invalid = True

        if turbidity_enabled:
            if ((duty_cycle - ((turbidity_num_samples / 60) + 1) - iridium_tx_time) < 0):
                verify_strings.append("Duty cycle not long enough to complete Turbidity sample window.\n")
                settings_invalid = True
            if (int(self.gnssNumSamplesSpinBox.value() / get_int_from_str(self.gnssSampleRateComboBox.currentText()))
                    > 3600):
                verify_strings.append("Max number of turbidity samples is 3600.\n")
                settings_invalid = True

        if settings_invalid:
            self.programButton.setDisabled(True)
            self.verifyButton.setStyleSheet("""
                background-color: red;
                color: white;
                border-radius: 5px;
                font-size: 16px;
                """)

            write_string = "".join(verify_strings)

            self.writeText(write_string)
        else:
            self.programButton.setEnabled(True)
            self.verifyButton.setStyleSheet("""
                background-color: green;
                color: white;
                border-radius: 5px;
                font-size: 16px;
                """)
            self.writeText("Settings verified. You did a great job.")

    def resetVerifyButton(self):
        self.programButton.setDisabled(True)
        self.verifyButton.setStyleSheet("""
                background-color: gray;
                color: white;
                border-radius: 5px;
                font-size: 16px;
                """)
        self.writeText("Configure as desired and press the Verify button when ready.")

    def writeError(self, err_str):
        self.statusTextEdit.clear()

        char_format = QTextCharFormat()
        char_format.setForeground(QColor('red'))

        self.statusTextEdit.setCurrentCharFormat(char_format)

        self.statusTextEdit.setText(err_str)

    def writeText(self, err_str):
        self.statusTextEdit.clear()

        char_format = QTextCharFormat()
        char_format.setForeground(QColor('white'))

        self.statusTextEdit.setCurrentCharFormat(char_format)

        self.statusTextEdit.setText(err_str)

    def appendText(self, string):
        char_format = QTextCharFormat()
        char_format.setForeground(QColor('white'))

        self.statusTextEdit.setCurrentCharFormat(char_format)

        self.statusTextEdit.append(string)

    def appendError(self, string):
        char_format = QTextCharFormat()
        char_format.setForeground(QColor('red'))

        self.statusTextEdit.setCurrentCharFormat(char_format)

        self.statusTextEdit.append(string)

    def programDevice(self):

        self.find_usb_port()

        if not self.device_connected:
            self.writeError("STLink programmer not detected.")
            return

        self.assembleBinaryConfigFile()

        self.writeText("Running STM32 Programmer CLI, please wait.")

        self.disableGUI()
        # Run the worker thread so the program will be non-blocking
        self.thread.start()

    def disableGUI(self):
        self.ctEnableButton.setDisabled(True)
        self.ctNumSamplesSpinBox.setDisabled(True)
        self.tempEnableButton.setDisabled(True)
        self.tempNumSamplesSpinBox.setDisabled(True)
        self.lightEnableButton.setDisabled(True)
        self.lightMatchGNSSCheckbox.setDisabled(True)
        self.lightNumSamplesSpinBox.setDisabled(True)
        self.turbidityEnableButton.setDisabled(True)
        self.turbidityMatchGNSSCheckbox.setDisabled(True)
        self.turbidityNumSamplesSpinBox.setDisabled(True)
        self.iridiumTxTimeSpinBox.setDisabled(True)
        self.iridiumTypeComboBox.setDisabled(True)
        self.gnssNumSamplesSpinBox.setDisabled(True)
        self.gnssHighPerformanceModeCheckBox.setDisabled(True)
        self.gnssSampleRateComboBox.setDisabled(True)
        self.dutyCycleSpinBox.setDisabled(True)
        self.gnssMaxAcquisitionTimeSpinBox.setDisabled(True)
        self.trackingNumberSpinBox.setDisabled(True)
        self.verifyButton.setDisabled(True)
        self.programButton.setDisabled(True)

    def reenableGUI(self):
        self.ctEnableButton.setEnabled(True)
        if self.ctEnableButton.isChecked():
            self.ctNumSamplesSpinBox.setEnabled(True)

        self.tempEnableButton.setEnabled(True)
        if self.tempEnableButton.isChecked():
            self.tempNumSamplesSpinBox.setEnabled(True)

        self.lightEnableButton.setEnabled(True)
        if self.lightEnableButton.isChecked():
            self.lightMatchGNSSCheckbox.setEnabled(True)
            self.lightNumSamplesSpinBox.setEnabled(True)

        self.turbidityEnableButton.setEnabled(True)
        if self.turbidityEnableButton.isChecked():
            self.turbidityMatchGNSSCheckbox.setEnabled(True)
            self.turbidityNumSamplesSpinBox.setEnabled(True)

        self.iridiumTxTimeSpinBox.setEnabled(True)
        self.iridiumTypeComboBox.setEnabled(True)
        self.gnssNumSamplesSpinBox.setEnabled(True)
        self.gnssHighPerformanceModeCheckBox.setEnabled(True)
        self.gnssSampleRateComboBox.setEnabled(True)
        self.dutyCycleSpinBox.setEnabled(True)
        self.gnssMaxAcquisitionTimeSpinBox.setEnabled(True)
        self.trackingNumberSpinBox.setEnabled(True)
        self.verifyButton.setEnabled(True)
        self.programButton.setEnabled(True)

    def displayPicture(self):

        self.graphicsView.setScene(self.scene)
        pixmap = QPixmap("microSWIFT_pic.png")
        pixmapItem = QGraphicsPixmapItem(pixmap)
        self.scene.addItem(pixmapItem)

    def threadFinished(self):
        self.thread.quit()
        self.thread.wait()
        os.remove(self.configFilePath)


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    MainWindow = QtWidgets.QMainWindow()
    ui = Ui_MainWindow()
    ui.setupUi(MainWindow)
    MainWindow.show()
    sys.exit(app.exec())

