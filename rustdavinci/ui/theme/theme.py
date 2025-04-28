#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from PyQt6.QtCore import QSettings
from PyQt6.QtWidgets import QApplication, QStyleFactory
from PyQt6.QtGui import QPalette, QColor

from ui.settings.default_settings import default_settings

# Define dark theme colors
DARK_THEME_COLORS = {
    'window': (53, 53, 53),
    'window_text': (255, 255, 255),
    'base': (35, 35, 35),
    'alternate_base': (45, 45, 45),
    'text': (255, 255, 255),
    'button': (53, 53, 53),
    'button_text': (255, 255, 255),
    'bright_text': (255, 255, 0),
    'highlight': (42, 130, 218),
    'highlight_text': (255, 255, 255),
    'link': (42, 130, 218),
    'dark': (35, 35, 35),
    'mid': (65, 65, 65),
    'midlight': (90, 90, 90),
    'light': (110, 110, 110)
}

# Define light theme colors (default Qt colors)
LIGHT_THEME_COLORS = {
    'window': (240, 240, 240),
    'window_text': (0, 0, 0),
    'base': (255, 255, 255),
    'alternate_base': (233, 233, 233),
    'text': (0, 0, 0),
    'button': (240, 240, 240),
    'button_text': (0, 0, 0),
    'bright_text': (0, 0, 255),
    'highlight': (42, 130, 218),
    'highlight_text': (255, 255, 255),
    'link': (0, 0, 255),
    'dark': (160, 160, 160),
    'mid': (160, 160, 160),
    'midlight': (195, 195, 195),
    'light': (230, 230, 230)
}

# Dark theme stylesheet
DARK_THEME_STYLESHEET = """
/* General application styling */
QWidget {
    color: #FFFFFF;
    background-color: #353535;
}

/* Main window background */
QMainWindow, QDialog {
    background-color: #353535;
}

/* Menu styling */
QMenuBar {
    background-color: #353535;
    color: #FFFFFF;
}

QMenuBar::item:selected {
    background-color: #2A82DA;
}

QMenu {
    background-color: #353535;
    color: #FFFFFF;
    border: 1px solid #5E5E5E;
}

QMenu::item:selected {
    background-color: #2A82DA;
}

/* Button styling */
QPushButton {
    background-color: #444444;
    color: #FFFFFF;
    border: 1px solid #5E5E5E;
    border-radius: 3px;
    padding: 5px;
    min-width: 80px;
}

QPushButton:hover {
    background-color: #505050;
    border: 1px solid #6E6E6E;
}

QPushButton:pressed {
    background-color: #2A82DA;
    border: 1px solid #2A82DA;
}

QPushButton:disabled {
    background-color: #353535;
    color: #666666;
    border: 1px solid #444444;
}

/* ComboBox styling */
QComboBox {
    background-color: #444444;
    color: #FFFFFF;
    border: 1px solid #5E5E5E;
    border-radius: 3px;
    padding: 2px 18px 2px 3px;
    min-width: 6em;
}

QComboBox:hover {
    background-color: #505050;
    border: 1px solid #6E6E6E;
}

QComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 20px;
    border-left: 1px solid #5E5E5E;
    border-top-right-radius: 3px;
    border-bottom-right-radius: 3px;
}

QComboBox QAbstractItemView {
    border: 1px solid #5E5E5E;
    background-color: #353535;
    color: #FFFFFF;
    selection-background-color: #2A82DA;
    selection-color: #FFFFFF;
}

/* LineEdit styling */
QLineEdit {
    background-color: #444444;
    color: #FFFFFF;
    border: 1px solid #5E5E5E;
    border-radius: 3px;
    padding: 2px;
}

QLineEdit:focus {
    border: 1px solid #2A82DA;
}

QLineEdit:disabled {
    background-color: #353535;
    color: #666666;
    border: 1px solid #444444;
}

/* TextEdit styling */
QTextEdit {
    background-color: #2B2B2B;
    color: #FFFFFF;
    border: 1px solid #5E5E5E;
}

QTextEdit:focus {
    border: 1px solid #2A82DA;
}

/* CheckBox styling */
QCheckBox {
    color: #FFFFFF;
    spacing: 5px;
}

QCheckBox::indicator {
    width: 13px;
    height: 13px;
    border: 1px solid #5E5E5E;
    background-color: #444444;
}

QCheckBox::indicator:checked {
    background-color: #2A82DA;
}

QCheckBox::indicator:hover {
    border: 1px solid #2A82DA;
}

/* RadioButton styling */
QRadioButton {
    color: #FFFFFF;
    spacing: 5px;
}

QRadioButton::indicator {
    width: 13px;
    height: 13px;
    border: 1px solid #5E5E5E;
    border-radius: 7px;
    background-color: #444444;
}

QRadioButton::indicator:checked {
    background-color: #2A82DA;
    border: 2px solid #444444;
    width: 9px;
    height: 9px;
}

QRadioButton::indicator:hover {
    border: 1px solid #2A82DA;
}

/* GroupBox styling */
QGroupBox {
    border: 1px solid #5E5E5E;
    border-radius: 5px;
    margin-top: 1ex;
    padding-top: 10px;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top center;
    padding: 0 5px;
    color: #FFFFFF;
}

/* TabWidget styling */
QTabWidget::pane {
    border: 1px solid #5E5E5E;
}

QTabBar::tab {
    background-color: #353535;
    color: #FFFFFF;
    border: 1px solid #5E5E5E;
    border-bottom-color: #5E5E5E;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
    padding: 5px 10px;
    min-width: 50px;
}

QTabBar::tab:selected, QTabBar::tab:hover {
    background-color: #444444;
}

QTabBar::tab:selected {
    border-bottom-color: #444444;
}

QTabBar::tab:!selected {
    margin-top: 2px;
}

/* ProgressBar styling */
QProgressBar {
    border: 1px solid #5E5E5E;
    border-radius: 3px;
    background-color: #353535;
    text-align: center;
    color: #FFFFFF;
}

QProgressBar::chunk {
    background-color: #2A82DA;
    width: 10px;
    margin: 0.5px;
}

/* ScrollBar styling */
QScrollBar:vertical {
    border: none;
    background-color: #353535;
    width: 10px;
    margin: 16px 0 16px 0;
}

QScrollBar::handle:vertical {
    background-color: #5E5E5E;
    min-height: 20px;
    border-radius: 4px;
}

QScrollBar::handle:vertical:hover {
    background-color: #6E6E6E;
}

QScrollBar::add-line:vertical {
    border: none;
    background: none;
    height: 10px;
    subcontrol-position: bottom;
    subcontrol-origin: margin;
}

QScrollBar::sub-line:vertical {
    border: none;
    background: none;
    height: 10px;
    subcontrol-position: top;
    subcontrol-origin: margin;
}

QScrollBar:horizontal {
    border: none;
    background-color: #353535;
    height: 10px;
    margin: 0px 16px 0 16px;
}

QScrollBar::handle:horizontal {
    background-color: #5E5E5E;
    min-width: 20px;
    border-radius: 4px;
}

QScrollBar::handle:horizontal:hover {
    background-color: #6E6E6E;
}

QScrollBar::add-line:horizontal {
    border: none;
    background: none;
    width: 10px;
    subcontrol-position: right;
    subcontrol-origin: margin;
}

QScrollBar::sub-line:horizontal {
    border: none;
    background: none;
    width: 10px;
    subcontrol-position: left;
    subcontrol-origin: margin;
}

/* TableView styling */
QTableView {
    gridline-color: #5E5E5E;
    background-color: #2B2B2B;
    color: #FFFFFF;
    border: 1px solid #5E5E5E;
}

QTableView::item:selected {
    background-color: #2A82DA;
    color: #FFFFFF;
}

QHeaderView::section {
    background-color: #444444;
    color: #FFFFFF;
    padding: 4px;
    border: 1px solid #5E5E5E;
}

/* QListView styling */
QListView {
    background-color: #2B2B2B;
    color: #FFFFFF;
    border: 1px solid #5E5E5E;
}

QListView::item:selected {
    background-color: #2A82DA;
    color: #FFFFFF;
}

/* QDialog styling */
QDialog QDialogButtonBox QPushButton {
    min-width: 65px;
}

QLabel {
    color: #FFFFFF;
}

QFrame[frameShape="4"],
QFrame[frameShape="5"] {
    color: #5E5E5E;
}

/* Spinbox styling */
QSpinBox, QDoubleSpinBox {
    background-color: #444444;
    color: #FFFFFF;
    border: 1px solid #5E5E5E;
    border-radius: 3px;
    padding: 2px 18px 2px 3px;
}

QSpinBox::up-button, QDoubleSpinBox::up-button {
    subcontrol-origin: border;
    subcontrol-position: top right;
    border-left: 1px solid #5E5E5E;
    width: 16px;
}

QSpinBox::down-button, QDoubleSpinBox::down-button {
    subcontrol-origin: border;
    subcontrol-position: bottom right;
    border-left: 1px solid #5E5E5E;
    width: 16px;
}

/* QMessageBox styling */
QMessageBox {
    background-color: #353535;
    color: #FFFFFF;
}

QMessageBox QPushButton {
    min-width: 65px;
}

QMessageBox QLabel {
    color: #FFFFFF;
}

/* QToolTip styling */
QToolTip {
    border: 1px solid #5E5E5E;
    background-color: #2B2B2B;
    color: #FFFFFF;
    padding: 1px;
}

/* Status bar styling */
QStatusBar {
    background-color: #444444;
    color: #FFFFFF;
}

QStatusBar::item {
    border: none;
}

/* Frame styling for status displays, color swatches, etc. */
QFrame#colorSwatchFrame {
    border: 2px solid #5E5E5E;
    border-radius: 5px;
}

QFrame#paintStatusFrame {
    background-color: #353535;
    border: 1px solid #5E5E5E;
    border-radius: 3px;
}
"""

# Light theme stylesheet (minimal - we'll use native styling for light theme)
LIGHT_THEME_STYLESHEET = """
/* Frame styling for color swatches, etc. */
QFrame#colorSwatchFrame {
    border: 2px solid #AAAAAA;
    border-radius: 5px;
}

QFrame#paintStatusFrame {
    background-color: #FFFFFF;
    border: 1px solid #CCCCCC;
    border-radius: 3px;
}
"""

def get_theme_palette(theme="dark"):
    """
    Get the palette for the specified theme.
    
    Args:
        theme (str): The theme to get the palette for ('dark' or 'light')
        
    Returns:
        QPalette: The palette for the theme
    """
    palette = QPalette()
    
    if theme.lower() == "dark":
        colors = DARK_THEME_COLORS
    else:
        colors = LIGHT_THEME_COLORS
    
    color_roles = {
        QPalette.ColorRole.Window: colors['window'],
        QPalette.ColorRole.WindowText: colors['window_text'],
        QPalette.ColorRole.Base: colors['base'],
        QPalette.ColorRole.AlternateBase: colors['alternate_base'],
        QPalette.ColorRole.ToolTipBase: colors['window'],
        QPalette.ColorRole.ToolTipText: colors['window_text'],
        QPalette.ColorRole.PlaceholderText: colors['text'],
        QPalette.ColorRole.Text: colors['text'],
        QPalette.ColorRole.Button: colors['button'],
        QPalette.ColorRole.ButtonText: colors['button_text'],
        QPalette.ColorRole.BrightText: colors['bright_text'],
        QPalette.ColorRole.Highlight: colors['highlight'],
        QPalette.ColorRole.HighlightedText: colors['highlight_text'],
        QPalette.ColorRole.Link: colors['link'],
        QPalette.ColorRole.Dark: colors['dark'],
        QPalette.ColorRole.Mid: colors['mid'],
        QPalette.ColorRole.Midlight: colors['midlight'],
        QPalette.ColorRole.Light: colors['light'],
    }
    
    for role, color in color_roles.items():
        palette.setColor(role, QColor(*color))
    
    return palette

def apply_theme():
    """
    Apply the theme based on settings.
    
    Returns:
        bool: True if dark theme applied, False if light theme
    """
    # Get theme setting
    settings = QSettings()
    theme = settings.value("theme", default_settings["theme"])
    is_dark = theme.lower() == "dark"
    
    # Get the app instance
    app = QApplication.instance()
    if not app:
        return is_dark
    
    # Apply appropriate palette and stylesheet
    if is_dark:
        app.setStyle(QStyleFactory.create("Fusion"))
        app.setPalette(get_theme_palette("dark"))
        app.setStyleSheet(DARK_THEME_STYLESHEET)
    else:
        app.setStyle(QStyleFactory.create("Fusion"))
        app.setPalette(get_theme_palette("light"))
        app.setStyleSheet(LIGHT_THEME_STYLESHEET)
    
    # Note: There's no QMessageBox.setDefaultStyle method
    # We'll just use the app style which will apply to all dialogs
    
    return is_dark

def toggle_theme():
    """
    Toggle between dark and light themes.
    
    Returns:
        str: The name of the new theme
    """
    settings = QSettings()
    current_theme = settings.value("theme", default_settings["theme"])
    
    # Toggle theme
    if current_theme.lower() == "dark":
        new_theme = "light"
    else:
        new_theme = "dark"
    
    # Save the new theme
    settings.setValue("theme", new_theme)
    
    # Apply the new theme
    apply_theme()
    
    return new_theme

def apply_theme_to_dialog(dialog):
    """
    Apply the current theme to a specific dialog.
    This is useful for dynamically created dialogs.
    
    Args:
        dialog: QDialog to apply theme to
    """
    settings = QSettings()
    theme = settings.value("theme", default_settings["theme"])
    is_dark = theme.lower() == "dark"
    
    if is_dark:
        dialog.setStyle(QStyleFactory.create("Fusion"))
        dialog.setPalette(get_theme_palette("dark"))
    else:
        dialog.setStyle(QStyleFactory.create("Fusion"))
        dialog.setPalette(get_theme_palette("light"))