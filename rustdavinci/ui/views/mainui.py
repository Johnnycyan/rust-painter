# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'mainui.ui'
#
# Created by: PyQt6 UI code generator
#
# WARNING! All changes made in this file will be lost!


from PyQt6 import QtCore, QtGui, QtWidgets


class Ui_MainUI(object):
    def setupUi(self, MainUI):
        MainUI.setObjectName("MainUI")
        self.small_width = 240
        self.normal_height = 782
        self.big_width = 950
        MainUI.resize(self.small_width, self.normal_height)
        MainUI.setMinimumSize(QtCore.QSize(self.small_width, self.normal_height))
        MainUI.setMaximumSize(QtCore.QSize(self.small_width, self.normal_height))
        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap(":/icons/RustDaVinci-icon.ico"), QtGui.QIcon.Mode.Normal, QtGui.QIcon.State.Off)
        MainUI.setWindowIcon(icon)
        self.centralwidget = QtWidgets.QWidget(MainUI)
        self.centralwidget.setObjectName("centralwidget")
        
        # Top buttons - keep as they were
        self.load_image_PushButton = QtWidgets.QPushButton(self.centralwidget)
        self.load_image_PushButton.setGeometry(QtCore.QRect(10, 10, 220, 45))
        font = QtGui.QFont()
        font.setPointSize(10)
        font.setBold(True)
        font.setUnderline(False)
        font.setWeight(75)
        font.setStrikeOut(False)
        font.setKerning(True)
        self.load_image_PushButton.setFont(font)
        self.load_image_PushButton.setMouseTracking(False)
        self.load_image_PushButton.setTabletTracking(False)
        self.load_image_PushButton.setFocusPolicy(QtCore.Qt.FocusPolicy.StrongFocus)
        self.load_image_PushButton.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.DefaultContextMenu)
        self.load_image_PushButton.setAcceptDrops(False)
        self.load_image_PushButton.setToolTipDuration(-1)
        self.load_image_PushButton.setLayoutDirection(QtCore.Qt.LayoutDirection.LeftToRight)
        self.load_image_PushButton.setAutoFillBackground(False)
        self.load_image_PushButton.setStyleSheet("")
        self.load_image_PushButton.setInputMethodHints(QtCore.Qt.InputMethodHint.ImhNone)
        icon1 = QtGui.QIcon()
        icon1.addPixmap(QtGui.QPixmap(":/icons/load_image_icon.png"), QtGui.QIcon.Mode.Normal, QtGui.QIcon.State.Off)
        self.load_image_PushButton.setIcon(icon1)
        self.load_image_PushButton.setIconSize(QtCore.QSize(220, 45))
        self.load_image_PushButton.setCheckable(False)
        self.load_image_PushButton.setAutoDefault(False)
        self.load_image_PushButton.setDefault(False)
        self.load_image_PushButton.setFlat(True)
        self.load_image_PushButton.setObjectName("load_image_PushButton")
        
        self.identify_ctrl_PushButton = QtWidgets.QPushButton(self.centralwidget)
        self.identify_ctrl_PushButton.setGeometry(QtCore.QRect(10, 60, 220, 45))
        font = QtGui.QFont()
        font.setPointSize(10)
        font.setBold(True)
        font.setUnderline(False)
        font.setWeight(75)
        font.setStrikeOut(False)
        self.identify_ctrl_PushButton.setFont(font)
        icon2 = QtGui.QIcon()
        icon2.addPixmap(QtGui.QPixmap(":/icons/select_area_icon.png"), QtGui.QIcon.Mode.Normal, QtGui.QIcon.State.Off)
        self.identify_ctrl_PushButton.setIcon(icon2)
        self.identify_ctrl_PushButton.setIconSize(QtCore.QSize(220, 45))
        self.identify_ctrl_PushButton.setFlat(True)
        self.identify_ctrl_PushButton.setObjectName("identify_ctrl_PushButton")
        
        self.paint_image_PushButton = QtWidgets.QPushButton(self.centralwidget)
        self.paint_image_PushButton.setEnabled(False)
        self.paint_image_PushButton.setGeometry(QtCore.QRect(10, 110, 220, 45))
        font = QtGui.QFont()
        font.setPointSize(10)
        font.setBold(True)
        font.setUnderline(False)
        font.setWeight(75)
        self.paint_image_PushButton.setFont(font)
        self.paint_image_PushButton.setInputMethodHints(QtCore.Qt.InputMethodHint.ImhNone)
        icon3 = QtGui.QIcon()
        icon3.addPixmap(QtGui.QPixmap(":/icons/paint_image_icon.png"), QtGui.QIcon.Mode.Normal, QtGui.QIcon.State.Off)
        self.paint_image_PushButton.setIcon(icon3)
        self.paint_image_PushButton.setIconSize(QtCore.QSize(220, 45))
        self.paint_image_PushButton.setFlat(True)
        self.paint_image_PushButton.setObjectName("paint_image_PushButton")
        
        self.settings_PushButton = QtWidgets.QPushButton(self.centralwidget)
        self.settings_PushButton.setGeometry(QtCore.QRect(10, 160, 220, 45))
        font = QtGui.QFont()
        font.setPointSize(10)
        font.setBold(True)
        font.setUnderline(False)
        font.setWeight(75)
        self.settings_PushButton.setFont(font)
        icon4 = QtGui.QIcon()
        icon4.addPixmap(QtGui.QPixmap(":/icons/settings_icon.png"), QtGui.QIcon.Mode.Normal, QtGui.QIcon.State.Off)
        self.settings_PushButton.setIcon(icon4)
        self.settings_PushButton.setIconSize(QtCore.QSize(220, 45))
        self.settings_PushButton.setFlat(True)
        self.settings_PushButton.setObjectName("settings_PushButton")
        
        self.line = QtWidgets.QFrame(self.centralwidget)
        self.line.setGeometry(QtCore.QRect(17, 220, 201, 16))
        self.line.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        self.line.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        self.line.setObjectName("line")
        
        # Keep both paint status frame and log text area visible at the same time
        # The paint status frame (Now showing above the text log area)
        self.paintStatusFrame = QtWidgets.QFrame(self.centralwidget)
        self.paintStatusFrame.setGeometry(QtCore.QRect(10, 240, 221, 101))
        self.paintStatusFrame.setFrameShape(QtWidgets.QFrame.Shape.StyledPanel)
        self.paintStatusFrame.setFrameShadow(QtWidgets.QFrame.Shadow.Raised)
        self.paintStatusFrame.setObjectName("paintStatusFrame")
        
        # Time status labels
        self.timeStatusLabel = QtWidgets.QLabel(self.paintStatusFrame)
        self.timeStatusLabel.setGeometry(QtCore.QRect(5, 5, 211, 20))
        self.timeStatusLabel.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.timeStatusLabel.setObjectName("timeStatusLabel")
        
        # Color progress label
        self.colorProgressLabel = QtWidgets.QLabel(self.paintStatusFrame)
        self.colorProgressLabel.setGeometry(QtCore.QRect(5, 25, 211, 20))
        self.colorProgressLabel.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.colorProgressLabel.setObjectName("colorProgressLabel")
        
        # Current color swatch frame
        self.colorSwatchFrame = QtWidgets.QFrame(self.paintStatusFrame)
        self.colorSwatchFrame.setGeometry(QtCore.QRect(5, 50, 30, 30))
        self.colorSwatchFrame.setFrameShape(QtWidgets.QFrame.Shape.Box)
        self.colorSwatchFrame.setFrameShadow(QtWidgets.QFrame.Shadow.Raised)
        self.colorSwatchFrame.setObjectName("colorSwatchFrame")
        
        # Current color information label
        self.currentColorLabel = QtWidgets.QLabel(self.paintStatusFrame)
        self.currentColorLabel.setGeometry(QtCore.QRect(40, 50, 176, 30))
        self.currentColorLabel.setObjectName("currentColorLabel")
        
        # Increase the height of the log text area from 101 to 120 pixels
        # to make sure the bottom isn't cut off
        self.log_TextEdit = QtWidgets.QTextEdit(self.centralwidget)
        self.log_TextEdit.setGeometry(QtCore.QRect(10, 350, 221, 320))
        self.log_TextEdit.setUndoRedoEnabled(False)
        self.log_TextEdit.setReadOnly(True)
        self.log_TextEdit.setTextInteractionFlags(QtCore.Qt.TextInteractionFlag.NoTextInteraction)
        self.log_TextEdit.setObjectName("log_TextEdit")
        
        # Move the preview button down to accommodate the taller log text area
        self.preview_PushButton = QtWidgets.QPushButton(self.centralwidget)
        self.preview_PushButton.setEnabled(False)
        self.preview_PushButton.setGeometry(QtCore.QRect(10, 680, 221, 41))
        self.preview_PushButton.setObjectName("preview_PushButton")
        
        # Move the progress bar down to accommodate the taller log text area
        self.progress_ProgressBar = QtWidgets.QProgressBar(self.centralwidget)
        self.progress_ProgressBar.setGeometry(QtCore.QRect(10, 730, 221, 21))
        self.progress_ProgressBar.setProperty("value", 0)
        self.progress_ProgressBar.setTextVisible(False)
        self.progress_ProgressBar.setOrientation(QtCore.Qt.Orientation.Horizontal)
        self.progress_ProgressBar.setInvertedAppearance(False)
        self.progress_ProgressBar.setObjectName("progress_ProgressBar")
        
        MainUI.setCentralWidget(self.centralwidget)
        self.statusbar = QtWidgets.QStatusBar(MainUI)
        self.statusbar.setObjectName("statusbar")
        MainUI.setStatusBar(self.statusbar)

        self.retranslateUi(MainUI)
        QtCore.QMetaObject.connectSlotsByName(MainUI)

    def retranslateUi(self, MainUI):
        _translate = QtCore.QCoreApplication.translate
        MainUI.setWindowTitle(_translate("MainUI", "Rust Painter"))
        self.load_image_PushButton.setToolTip(_translate("MainUI", "Load Image from File or URL"))
        self.load_image_PushButton.setText(_translate("MainUI", "         Load Image...        "))
        self.identify_ctrl_PushButton.setToolTip(_translate("MainUI", "Capture the painting control area manually or automatically"))
        self.identify_ctrl_PushButton.setText(_translate("MainUI", " Capture Control Area..."))
        self.paint_image_PushButton.setToolTip(_translate("MainUI", "Paint the Image"))
        self.paint_image_PushButton.setText(_translate("MainUI", "         Paint Image           "))
        self.settings_PushButton.setToolTip(_translate("MainUI", "Show Rust Painter Settings"))
        self.settings_PushButton.setText(_translate("MainUI", "            Settings              "))
        self.preview_PushButton.setToolTip(_translate("MainUI", "Show Original Image and Preview of the Quantized Images"))
        self.preview_PushButton.setText(_translate("MainUI", "Show Image >>"))
        
        # Set default text for the new UI elements
        self.timeStatusLabel.setText(_translate("MainUI", "Time: 00:00:00 | Remaining: 00:00:00"))
        self.colorProgressLabel.setText(_translate("MainUI", "Color: 0/0"))
        self.currentColorLabel.setText(_translate("MainUI", "No color selected"))
import ui.resources.icons_rc
