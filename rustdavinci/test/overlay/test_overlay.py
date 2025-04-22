#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RustDaVinci Test Overlay
This script creates a transparent overlay that visualizes where the program thinks
all UI elements are located. It's useful for debugging the control positions.
"""

import sys
import os
import time
from PyQt5.QtCore import Qt, QRect, QPoint, QSettings, QTimer
from PyQt5.QtGui import QPainter, QColor, QPen, QFont, QBrush
from PyQt5.QtWidgets import QApplication, QMainWindow, QDesktopWidget, QLabel

# Add the parent directory to the path so we can import from lib
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Import the default settings
from ui.settings.default_settings import default_settings


class OverlayWindow(QMainWindow):
    """
    Creates a transparent overlay window that shows the positions of all UI elements
    that RustDaVinci would interact with.
    """
    def __init__(self):
        super().__init__()
        
        # Load settings
        self.settings = QSettings()
        
        # Initialize UI element coordinates
        self.canvas_x = 0
        self.canvas_y = 0
        self.canvas_w = 0
        self.canvas_h = 0
        
        self.ctrl_update = None
        self.ctrl_size = []
        self.ctrl_brush = []
        self.ctrl_opacity = []
        self.ctrl_color = []
        
        # Element colors
        self.canvas_color = QColor(0, 255, 0, 100)        # Green semi-transparent
        self.update_button_color = QColor(255, 0, 0, 150)  # Red semi-transparent
        self.brush_color = QColor(0, 0, 255, 150)         # Blue semi-transparent
        self.size_color = QColor(255, 165, 0, 150)        # Orange semi-transparent
        self.opacity_color = QColor(255, 0, 255, 150)     # Magenta semi-transparent
        self.color_grid_color = QColor(0, 255, 255, 100)  # Cyan semi-transparent
        
        # UI setup
        self.initUI()
        
        # Load positions from settings
        self.load_positions()
        
        # Setup a timer to reload positions every few seconds
        # This allows changing the settings and seeing the overlay update in real-time
        self.timer = QTimer()
        self.timer.timeout.connect(self.load_positions)
        self.timer.start(2000)  # Update every 2 seconds
        
    def initUI(self):
        """Setup the overlay window UI"""
        # Get screen dimensions
        screen = QDesktopWidget().screenGeometry()
        self.setGeometry(0, 0, screen.width(), screen.height())
        
        # Set window properties
        self.setWindowTitle('RustDaVinci UI Element Overlay')
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        # Add instructions label
        self.instructions = QLabel(self)
        self.instructions.setText("ESC: Close Overlay | R: Reload Positions")
        self.instructions.setStyleSheet("background-color: rgba(0, 0, 0, 150); color: white; padding: 5px;")
        self.instructions.setGeometry(10, 10, 300, 30)
        
        # Show the window
        self.show()
        
    def load_positions(self):
        """Load positions from QSettings"""
        # Canvas area
        self.canvas_x = int(self.settings.value("canvas_x", 0))
        self.canvas_y = int(self.settings.value("canvas_y", 0))
        self.canvas_w = int(self.settings.value("canvas_w", 0))
        self.canvas_h = int(self.settings.value("canvas_h", 0))
        
        # Control area base coordinates
        ctrl_x = int(self.settings.value("ctrl_x", default_settings["ctrl_x"]))
        ctrl_y = int(self.settings.value("ctrl_y", default_settings["ctrl_y"]))
        ctrl_w = int(self.settings.value("ctrl_w", default_settings["ctrl_w"]))
        ctrl_h = int(self.settings.value("ctrl_h", default_settings["ctrl_h"]))
        
        # Reset control positions
        self.ctrl_update = None
        self.ctrl_size = []
        self.ctrl_brush = []
        self.ctrl_opacity = []
        self.ctrl_color = []
        
        # Load pre-calculated positions from settings
        # Update button
        if self.settings.contains("overlay_update_x") and self.settings.contains("overlay_update_y"):
            self.ctrl_update = (
                float(self.settings.value("overlay_update_x")),
                float(self.settings.value("overlay_update_y"))
            )
            
        # Size input
        if self.settings.contains("overlay_size_x") and self.settings.contains("overlay_size_y"):
            self.ctrl_size.append((
                float(self.settings.value("overlay_size_x")),
                float(self.settings.value("overlay_size_y"))
            ))
            
        # Brush types
        brush_count = int(self.settings.value("overlay_brush_count", 0))
        for i in range(brush_count):
            if self.settings.contains(f"overlay_brush_{i}_x") and self.settings.contains(f"overlay_brush_{i}_y"):
                self.ctrl_brush.append((
                    float(self.settings.value(f"overlay_brush_{i}_x")),
                    float(self.settings.value(f"overlay_brush_{i}_y"))
                ))
                
        # Opacity input
        if self.settings.contains("overlay_opacity_x") and self.settings.contains("overlay_opacity_y"):
            self.ctrl_opacity.append((
                float(self.settings.value("overlay_opacity_x")),
                float(self.settings.value("overlay_opacity_y"))
            ))
            
        # Color grid
        color_count = int(self.settings.value("overlay_color_count", 0))
        for i in range(color_count):
            if self.settings.contains(f"overlay_color_{i}_x") and self.settings.contains(f"overlay_color_{i}_y"):
                self.ctrl_color.append((
                    float(self.settings.value(f"overlay_color_{i}_x")),
                    float(self.settings.value(f"overlay_color_{i}_y"))
                ))
                
        # If no positions found in settings but we have valid control area dimensions, 
        # update the control positions using the calculation in the main program
        if not self.ctrl_update or not self.ctrl_size or not self.ctrl_brush or not self.ctrl_opacity or not self.ctrl_color:
            print("Test overlay: No UI element positions found in QSettings.")
            print("Please run the main program first and calculate the positions.")
            print("Try clicking 'Identify Areas' and then 'Automatically' or 'Manually' to set up the control area.")
        
        # Force a repaint to show the updated positions
        self.repaint()
        
    def paintEvent(self, event):
        """Paint the overlay with visual indicators for each UI element"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Draw control area outline
        ctrl_x = int(self.settings.value("ctrl_x", default_settings["ctrl_x"]))
        ctrl_y = int(self.settings.value("ctrl_y", default_settings["ctrl_y"]))
        ctrl_w = int(self.settings.value("ctrl_w", default_settings["ctrl_w"]))
        ctrl_h = int(self.settings.value("ctrl_h", default_settings["ctrl_h"]))
        
        # Set font
        font = QFont()
        font.setPointSize(10)
        painter.setFont(font)
        
        # Draw control area rectangle
        painter.setPen(QPen(QColor(255, 255, 0, 200), 2))
        painter.drawRect(ctrl_x, ctrl_y, ctrl_w, ctrl_h)
        painter.fillRect(ctrl_x, ctrl_y-20, ctrl_w, 20, QColor(255, 255, 0, 150))
        painter.setPen(QPen(Qt.black))
        painter.drawText(ctrl_x+5, ctrl_y-5, "Control Area")
        
        # Draw canvas area rectangle
        if self.canvas_w > 0 and self.canvas_h > 0:
            painter.setPen(QPen(self.canvas_color, 2))
            painter.drawRect(self.canvas_x, self.canvas_y, self.canvas_w, self.canvas_h)
            painter.fillRect(self.canvas_x, self.canvas_y-20, 120, 20, self.canvas_color)
            painter.setPen(QPen(Qt.black))
            painter.drawText(self.canvas_x+5, self.canvas_y-5, "Canvas Area")
        
        # Draw update button indicator
        if self.ctrl_update:
            x, y = self.ctrl_update
            radius = 10
            painter.setBrush(self.update_button_color)
            painter.setPen(QPen(self.update_button_color, 2))
            painter.drawEllipse(QPoint(int(x), int(y)), radius, radius)
            painter.setPen(QPen(Qt.white))
            painter.drawText(int(x-35), int(y+30), "Update Button")
        
        # Draw brush type indicators
        for i, (x, y) in enumerate(self.ctrl_brush):
            radius = 8
            brush_names = ["Paint Brush", "Medium Round", "Light Round", "Heavy Round", "Heavy Square"]
            painter.setBrush(self.brush_color)
            painter.setPen(QPen(self.brush_color, 2))
            painter.drawEllipse(QPoint(int(x), int(y)), radius, radius)
            painter.setPen(QPen(Qt.white))
            if i < len(brush_names):
                painter.drawText(int(x-40), int(y-10), brush_names[i])
        
        # Draw size input field
        for x, y in self.ctrl_size:
            painter.setBrush(self.size_color)
            painter.setPen(QPen(self.size_color, 2))
            painter.drawRect(int(x-25), int(y-10), 50, 20)
            painter.setPen(QPen(Qt.white))
            painter.drawText(int(x-45), int(y-15), "Size Input")
        
        # Draw opacity input field
        for x, y in self.ctrl_opacity:
            painter.setBrush(self.opacity_color)
            painter.setPen(QPen(self.opacity_color, 2))
            painter.drawRect(int(x-25), int(y-10), 50, 20)
            painter.setPen(QPen(Qt.white))
            painter.drawText(int(x-55), int(y-15), "Opacity Input")
        
        # Draw color grid positions
        for i, (x, y) in enumerate(self.ctrl_color):
            # Calculate row and column to label every 4th color
            row = i // 4
            col = i % 4
            
            # Set different colors for different columns to visually distinguish opacity levels
            opacity_colors = [
                QColor(255, 0, 0, 150),  # Red for 100%
                QColor(0, 255, 0, 150),  # Green for 75%
                QColor(0, 0, 255, 150),  # Blue for 50%
                QColor(255, 255, 0, 150) # Yellow for 25%
            ]
            
            radius = 5
            painter.setBrush(opacity_colors[col])
            painter.setPen(QPen(opacity_colors[col], 2))
            painter.drawEllipse(QPoint(int(x), int(y)), radius, radius)
            
            # Show coordinates for first color in each row
            if col == 0:
                painter.setPen(QPen(Qt.white))
                painter.drawText(int(x-15), int(y-5), f"R{row}")
    
    def keyPressEvent(self, event):
        """Handle key press events"""
        # ESC key closes the overlay
        if event.key() == Qt.Key_Escape:
            self.close()
        # R key reloads positions
        elif event.key() == Qt.Key_R:
            self.load_positions()


def main():
    """Main function"""
    app = QApplication(sys.argv)
    overlay = OverlayWindow()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()