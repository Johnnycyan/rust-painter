#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from PyQt6 import QtCore
from PyQt6 import QtWidgets

import sys

from ui.views.main import MainWindow
from ui.theme.theme import apply_theme


def run():

    # Set some application settings for QSettings
    QtCore.QCoreApplication.setOrganizationName("Rust Painter")
    QtCore.QCoreApplication.setApplicationName("Rust Painter")

    # Setup the application and start
    app = QtWidgets.QApplication(sys.argv)
    
    # Apply theme based on settings (dark by default)
    apply_theme()

    main = MainWindow()
    main.show()
    sys.exit(app.exec())  # Note: exec_() changed to exec() in PyQt6


if __name__ == "__main__":
    run()
