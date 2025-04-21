#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from PyQt5.QtCore import QSettings, Qt, QRect, QDir
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import QMessageBox, QInputDialog, QFileDialog, QApplication, QLabel

from pynput import keyboard
from PIL import Image

import urllib.request
import pyautogui
import datetime
import numpy
import time
import cv2
import os

from lib.rustPaletteData import rust_palette
from lib.captureArea import capture_area
from lib.color_functions import hex_to_rgb, rgb_to_hex
from ui.dialogs.captureDialog import CaptureAreaDialog
from ui.settings.default_settings import default_settings


class rustDaVinci:
    def __init__(self, parent):
        """RustDaVinci class init"""
        self.parent = parent
        self.settings = QSettings()

        # PIL.Image images original/ quantized
        self.org_img_template = None
        self.org_img = None
        self.quantized_img = None
        self.palette_data = None
        self.updated_palette = None

        # Pixmaps
        self.pixmap_on_display = 0
        self.org_img_pixmap = None
        self.quantized_img_pixmap_normal = None
        self.quantized_img_pixmap_high = None

        # Booleans
        self.org_img_ok = False
        self.use_double_click = False
        self.use_hidden_colors = False

        # Keyboard interrupt variables
        self.pause_key = None
        self.skip_key = None
        self.abort_key = None
        self.paused = False
        self.skip_current_color = False
        self.abort = False

        # Painting control tools
        self.ctrl_update = 0
        self.ctrl_size = []
        self.ctrl_brush = []
        self.ctrl_opacity = []
        self.ctrl_color = []
        self.current_ctrl_size = None
        self.current_ctrl_brush = None
        self.current_ctrl_opacity = None
        self.current_ctrl_color = None

        # Canvas coordinates/ ratio
        self.canvas_x = 0
        self.canvas_y = 0
        self.canvas_w = 0
        self.canvas_h = 0

        # Statistics
        self.img_colors = []
        self.tot_pixels = 0
        self.pixels = 0
        self.lines = 0
        self.estimated_time = 0

        # Delays
        self.click_delay = 0
        self.line_delay = 0
        self.ctrl_area_delay = 0
        self.use_double_click = False

        self.background_color = None
        self.skip_colors = None

        # Hotkey display QLabel
        self.hotkey_label = None

        # Init functions
        if not (
            int(self.settings.value("ctrl_w", default_settings["ctrl_w"])) == 0
            or int(self.settings.value("ctrl_h", default_settings["ctrl_h"]))
        ):
            self.calculate_ctrl_tools_positioning()

    def update(self):
        """Updates pyauogui delays, booleans and paint image button"""
        self.click_delay = float(
            int(self.settings.value("click_delay", default_settings["click_delay"]))
            / 1000
        )
        self.line_delay = float(
            int(self.settings.value("line_delay", default_settings["line_delay"]))
            / 1000
        )
        self.ctrl_area_delay = float(
            int(
                self.settings.value(
                    "ctrl_area_delay", default_settings["ctrl_area_delay"]
                )
            )
            / 1000
        )
        self.use_double_click = bool(
            self.settings.value("double_click", default_settings["double_click"])
        )

        # Update the pyautogui delay
        pyautogui.PAUSE = self.click_delay

        if (
            int(self.settings.value("ctrl_w", default_settings["ctrl_w"])) == 0
            or int(self.settings.value("ctrl_h", default_settings["ctrl_h"])) == 0
        ):
            self.parent.ui.paint_image_PushButton.setEnabled(False)
        elif (
            self.org_img_ok
            and int(self.settings.value("ctrl_w", default_settings["ctrl_w"])) != 0
            and int(self.settings.value("ctrl_h", default_settings["ctrl_h"])) != 0
        ):
            self.parent.ui.paint_image_PushButton.setEnabled(True)

    def load_image_from_file(self):
        """Load image from a file"""
        title = "Select the image to be painted"
        fileformats = "Images (*.png *.jpg *.jpeg *.gif *.bmp)"
        folder_path = self.settings.value("folder_path", QDir.homePath())
        folder_path = os.path.dirname(os.path.abspath(folder_path))
        if not os.path.exists(folder_path):
            folder_path = QDir.homePath()

        path = QFileDialog.getOpenFileName(
            self.parent, title, folder_path, fileformats
        )[0]

        if path.endswith((".png", ".jpg", "jpeg", ".gif", ".bmp")):
            try:
                self.settings.setValue("folder_path", path)
                # Pixmap for original image
                self.org_img_pixmap = QPixmap(path, "1")

                # The original PIL.Image object
                self.org_img_template = Image.open(path).convert("RGBA")
                self.org_img = self.org_img_template

                self.convert_transparency()
                self.create_pixmaps()

                if bool(
                    self.settings.value(
                        "show_preview_load", default_settings["show_preview_load"]
                    )
                ):
                    if (
                        int(self.settings.value("quality", default_settings["quality"]))
                        == 0
                    ):
                        self.pixmap_on_display = 1
                    else:
                        self.pixmap_on_display = 2

                    if self.parent.is_expanded:
                        self.parent.label.hide()
                    self.parent.expand_window()
                else:
                    self.pixmap_on_display = 0

                self.parent.ui.log_TextEdit.clear()
                self.parent.ui.progress_ProgressBar.setValue(0)

            except Exception as e:
                self.org_img = None
                self.org_img_ok = False
                msg = QMessageBox(self.parent)
                msg.setIcon(QMessageBox.Critical)
                msg.setText("ERROR! Could not load the selected image...")
                msg.setInformativeText(str(e))
                msg.exec_()

        self.update()

    def load_image_from_url(self):
        """Load image from url"""
        dialog = QInputDialog(self.parent)
        dialog.setInputMode(QInputDialog.TextInput)
        dialog.setLabelText("Load image from URL:")
        dialog.resize(500, 100)
        ok_clicked = dialog.exec_()
        url = dialog.textValue()

        if ok_clicked and url != "":
            try:
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US; rv:1.9.0.7) Gecko/2009021910 Firefox/3.0.7"
                }
                request = urllib.request.Request(url, None, headers)
                self.org_img_template = Image.open(
                    urllib.request.urlopen(request)
                ).convert("RGBA")

                # Pixmap for original image
                self.org_img_template.save("temp_url_image.png")
                self.org_img_pixmap = QPixmap("temp_url_image.png", "1")
                os.remove("temp_url_image.png")

                # The original PIL.Image object
                self.org_img = self.org_img_template

                self.convert_transparency()
                self.create_pixmaps()

                if bool(
                    self.settings.value(
                        "show_preview_load", default_settings["show_preview_load"]
                    )
                ):
                    if (
                        int(self.settings.value("quality", default_settings["quality"]))
                        == 0
                    ):
                        self.pixmap_on_display = 1
                    else:
                        self.pixmap_on_display = 2

                    if self.parent.is_expanded:
                        self.parent.label.hide()
                    self.parent.expand_window()
                else:
                    self.pixmap_on_display = 0

                self.parent.ui.log_TextEdit.clear()
                self.parent.ui.progress_ProgressBar.setValue(0)

            except Exception as e:
                self.org_img = None
                self.org_img_ok = False
                msg = QMessageBox(self.parent)
                msg.setIcon(QMessageBox.Critical)
                msg.setText("ERROR! Could not load the selected image...")
                msg.setInformativeText(str(e))
                msg.exec_()

        self.update()

    def convert_transparency(self):
        """Paste the org_img on top of an image with background color"""
        try:
            # Get the user's background color preference 
            bg_color_hex = self.settings.value("background_color", default_settings["background_color"])
            bg_color_rgb = hex_to_rgb(bg_color_hex)
            
            # Check if the color exists in our palette - if not, use white (3rd color in our new palette)
            if bg_color_rgb in rust_palette:
                background_color = rust_palette.index(bg_color_rgb)
            else:
                # Use pure white (255,255,255) which is at index 3 in our new palette
                background_color = 3
                
            # Set transparency in image to default background
            self.org_img = self.org_img_template
            temp_org_img = Image.new("RGBA", self.org_img.size, color=rust_palette[background_color])
            temp_org_img.paste(self.org_img, (0, 0), mask=self.org_img)
            self.org_img = temp_org_img
            self.org_img = self.org_img.convert("RGB")
        except Exception as e:
            # Log the error but continue processing
            print(f"Warning: Error handling transparency: {str(e)}")
            self.org_img = self.org_img_template.convert("RGB")

    def create_pixmaps(self):
        """Create quantized pixmaps"""
        try:
            # Make sure we have a properly initialized palette
            background_color = (255, 255, 255)  # Default white
            bg_color_hex = self.settings.value("background_color", default_settings["background_color"])
            bg_color_rgb = hex_to_rgb(bg_color_hex)
            self.update_palette(bg_color_rgb)
            
            # Pixmap for quantized image of quality normal
            temp_normal = self.quantize_to_palette(self.org_img, True, 0)
            
            # Save and load the image to ensure correct processing
            temp_normal.save("temp_normal.png")
            self.quantized_img_pixmap_normal = QPixmap("temp_normal.png")
            os.remove("temp_normal.png")

            # Pixmap for quantized image of quality high (with dithering)
            temp_high = self.quantize_to_palette(self.org_img, True, 1)
            temp_high.save("temp_high.png")
            self.quantized_img_pixmap_high = QPixmap("temp_high.png")
            os.remove("temp_high.png")

            self.org_img_ok = True
        except Exception as e:
            print(f"Error creating pixmaps: {str(e)}")
            self.org_img_ok = False

    def convert_img(self):
        """Convert the image to fit the canvas and quantize the image.
        Updates:    quantized_img,
                    x_correction,
                    y_correction
        Returns:    False, if the image type is invalid.
        """
        org_img_w = self.org_img.size[0]
        org_img_h = self.org_img.size[1]

        wpercent = self.canvas_w / float(org_img_w)
        hpercent = self.canvas_h / float(org_img_h)

        hsize = int((float(org_img_h) * float(wpercent)))
        wsize = int((float(org_img_w) * float(hpercent)))

        x_correction = 0
        y_correction = 0

        if hsize <= self.canvas_h:
            resized_img = self.org_img.resize((self.canvas_w, hsize), Image.ANTIALIAS)
            y_correction = int((self.canvas_h - hsize) / 2)
        elif wsize <= self.canvas_w:
            resized_img = self.org_img.resize((wsize, self.canvas_h), Image.ANTIALIAS)
            x_correction = int((self.canvas_w - wsize) / 2)
        else:
            resized_img = self.org_img.resize(
                (self.canvas_w, self.canvas_h), Image.ANTIALIAS
            )

        self.quantized_img = self.quantize_to_palette(resized_img)
        if not self.quantized_img:
            self.org_img = None
            self.quantized_img = None
            self.org_img_ok = False
            return False

        self.canvas_x += x_correction
        self.canvas_y += y_correction
        self.canvas_w = self.quantized_img.size[0]
        self.canvas_h = self.quantized_img.size[1]
        return True

    def update_palette(self, rgb_background):
        """Update the palette used for image quantization with the new 4x16 color grid"""
        use_brush_opacities = bool(
            self.settings.value("brush_opacities", default_settings["brush_opacities"])
        )

        # Find the background color in the rust_palette list
        background_index = 3  # Default to white (index 3)
        for i, color in enumerate(rust_palette):
            if color == rgb_background:
                background_index = i
                break

        # Calculate the row of this color in our grid
        background_row = background_index // 4

        # Store background color indices for skip_colors list (used only during painting)
        # This doesn't affect the color palette used for image quantization
        self.background_opacities = []
        if self.settings.value("skip_background_color", default_settings["skip_background_color"]):
            self.background_opacities = [
                background_row * 4,     # 100% opacity
                background_row * 4 + 1, # 75% opacity
                background_row * 4 + 2, # 50% opacity
                background_row * 4 + 3, # 25% opacity
            ]

        # Create a new palette image with the right mode
        self.palette_data = Image.new("P", (16, 16))
        self.updated_palette = []
        
        # Build the palette as a list of RGB tuples for our internal use
        palette_colors = []
        
        # Add colors based on whether we're using all opacity versions or just 100% opacity
        if use_brush_opacities:
            # Use all 64 colors from the palette
            for row in range(16):  # 16 rows
                for col in range(4):  # 4 columns per row
                    i = row * 4 + col  # Calculate the index
                    
                    # Always include the actual color for image quantization
                    # (background skipping only affects painting)
                    base_color = rust_palette[row * 4]  # Get base color for this row
                    
                    if col == 0:
                        # 100% opacity - use the original color
                        color = base_color
                    else:
                        # Calculate opacity variation (75%, 50%, 25%)
                        opacity = 1.0 - (col * 0.25)
                        r = max(0, min(255, int(base_color[0] * opacity)))
                        g = max(0, min(255, int(base_color[1] * opacity)))
                        b = max(0, min(255, int(base_color[2] * opacity)))
                        color = (r, g, b)
                    
                    palette_colors.append(color)
        else:
            # Only use the 16 base colors (100% opacity)
            for row in range(16):
                i = row * 4  # First color of each row (100% opacity)
                color = rust_palette[i]
                palette_colors.append(color)

        # Store the final palette for our use
        self.updated_palette = palette_colors.copy()
        
        # Find background color in our updated palette
        if rgb_background in self.updated_palette:
            self.background_color = self.updated_palette.index(rgb_background)
        else:
            self.background_color = None
        
        # Create a flat list of palette values for PIL (R,G,B,R,G,B,...)
        raw_palette = []
        for color in palette_colors:
            raw_palette.append(color[0])  # R
            raw_palette.append(color[1])  # G
            raw_palette.append(color[2])  # B
            
        # Pad the palette to 256 colors as required by PIL
        while len(palette_colors) < 256:
            raw_palette.extend([0, 0, 0])
            palette_colors.append((0, 0, 0))
            
        # Set the palette data
        self.palette_data.putpalette(raw_palette)

    def quantize_to_palette(self, image, pixmap=False, pixmap_q=0):
        """Convert an RGB, RGBA or L mode image to use a given P image's palette.
        Returns:    The quantized image
        """
        try:
            # Get the background color from settings
            bg_color_hex = self.settings.value(
                "background_color", default_settings["background_color"]
            )
            bg_color_rgb = hex_to_rgb(bg_color_hex)
            
            # Prepare the image
            temp_img = image.copy()
            if temp_img.mode == "RGBA":
                # Handle transparency by replacing it with the background color
                bg = Image.new('RGB', temp_img.size, bg_color_rgb)
                bg.paste(temp_img, mask=temp_img.split()[3])  # alpha channel
                temp_img = bg
            
            # Ensure image is in RGB mode for quantization
            if temp_img.mode != "RGB":
                temp_img = temp_img.convert("RGB")
            
            # Make a fresh copy of our rust palette for this quantization
            palette_colors = list(rust_palette[:64])
            
            # Determine if we use dithering
            dither_mode = False
            if not pixmap:
                quality = int(self.settings.value("quality", default_settings["quality"]))
                dither_mode = (quality == 1)  # True for high quality
            else:
                dither_mode = (pixmap_q == 1)  # True for dithered preview
            
            # Use a third-party PIL-compatible quantization library for better results
            # This would be the ideal solution, but since we can't add dependencies,
            # we'll use PIL's built-in quantization
            
            # Create a palette image and put our color data into it
            palette_img = Image.new('P', (1, 1))
            
            # Create the flat palette list (R,G,B,R,G,B,...)
            palette_data = []
            for color in palette_colors:
                palette_data.extend(color)
            
            # Pad to 256 colors
            remaining = 256 - len(palette_colors)
            padding = [0, 0, 0] * remaining
            palette_data.extend(padding)
            
            # Apply the palette
            palette_img.putpalette(palette_data)
            
            # Use PIL's convertible
            dither = Image.FLOYDSTEINBERG if dither_mode else Image.NONE
            
            # Very important: let PIL choose the best color mapping for each pixel
            quantized = temp_img.quantize(
                colors=len(palette_colors), 
                method=2,  # Use median cut method for better color mapping
                kmeans=3,  # Use k-means iterations for refinement
                palette=palette_img,
                dither=dither
            )
            
            # Convert back to RGB for display
            result = quantized.convert('RGB')
            
            # Store the updated palette for painting operations
            self.updated_palette = palette_colors
            if bg_color_rgb in palette_colors:
                self.background_color = palette_colors.index(bg_color_rgb)
            else:
                self.background_color = None
            
            return result
            
        except Exception as e:
            print(f"Error in quantize_to_palette: {str(e)}")
            # If there's an error, return the original image
            if image.mode == "RGBA":
                return image.convert("RGB")
            return image

    def clear_image(self):
        """Clear the image"""
        self.org_img = None
        self.quantized_img = None
        self.org_img_ok = False
        self.update()

    def locate_canvas_area(self):
        """Locate the coordinates/ ratio of the canvas area.
        Updates:    self.canvas_x,
                    self.canvas_y,
                    self.canvas_w,
                    self.canvas_h
        """
        dialog = CaptureAreaDialog(self.parent, 0)
        ans = dialog.exec_()
        if ans == 0:
            return False

        self.parent.hide()
        canvas_area = capture_area()
        self.parent.show()

        if not canvas_area:
            return False
        elif canvas_area[2] == 0 or canvas_area[3] == 0:
            msg = QMessageBox(self.parent)
            msg.setIcon(QMessageBox.Critical)
            msg.setText(
                "Invalid coordinates and ratio. Drag & drop the top left corner of the canvas to the bottom right corner."
            )
            msg.exec_()
            return False

        msg = QMessageBox(self.parent)
        msg.setIcon(QMessageBox.Information)
        msg.setText(
            "Coordinates:\n"
            + "X =\t\t"
            + str(canvas_area[0])
            + "\n"
            + "Y =\t\t"
            + str(canvas_area[1])
            + "\n"
            + "Width =\t"
            + str(canvas_area[2])
            + "\n"
            + "Height =\t"
            + str(canvas_area[3])
        )
        msg.exec_()

        self.canvas_x = canvas_area[0]
        self.canvas_y = canvas_area[1]
        self.canvas_w = canvas_area[2]
        self.canvas_h = canvas_area[3]
        return True

    def locate_control_area_manually(self):
        """"""
        dialog = CaptureAreaDialog(self.parent, 1)
        ans = dialog.exec_()
        if ans == 0:
            return False

        self.parent.hide()
        ctrl_area = capture_area()
        self.parent.show()

        if not ctrl_area:
            self.update()
            return False
        elif ctrl_area[2] == 0 and ctrl_area[3] == 0:
            msg = QMessageBox(self.parent)
            msg.setIcon(QMessageBox.Critical)
            msg.setText(
                "Invalid coordinates and ratio. Drag & drop the top left corner of the canvas to the bottom right corner."
            )
            msg.exec_()
            self.update()
            return False

        btn = QMessageBox.question(
            self.parent,
            None,
            "Coordinates:\n"
            + "X =\t\t"
            + str(ctrl_area[0])
            + "\n"
            + "Y =\t\t"
            + str(ctrl_area[1])
            + "\n"
            + "Width =\t"
            + str(ctrl_area[2])
            + "\n"
            + "Height =\t"
            + str(ctrl_area[3])
            + "\n\n"
            + "Would you like to update the painting controls area coordinates?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes,
        )
        if btn == QMessageBox.Yes:
            self.parent.ui.log_TextEdit.append("Controls area position updated...")
            self.settings.setValue("ctrl_x", str(ctrl_area[0]))
            self.settings.setValue("ctrl_y", str(ctrl_area[1]))
            self.settings.setValue("ctrl_w", str(ctrl_area[2]))
            self.settings.setValue("ctrl_h", str(ctrl_area[3]))

        self.update()

    def locate_control_area_automatically(self):
        """"""
        self.parent.hide()
        ctrl_area = self.locate_control_area_opencv()
        self.parent.show()

        msg = QMessageBox(self.parent)
        if not ctrl_area:
            msg.setIcon(QMessageBox.Critical)
            msg.setText(
                "Couldn't find the painting control area automatically... Please try to manually capture it instead..."
            )
            msg.exec_()
        else:
            btn = QMessageBox.question(
                self.parent,
                None,
                "Coordinates:\n"
                + "X =\t\t"
                + str(ctrl_area[0])
                + "\n"
                + "Y =\t\t"
                + str(ctrl_area[1])
                + "\n"
                + "Width =\t"
                + str(ctrl_area[2])
                + "\n"
                + "Height =\t"
                + str(ctrl_area[3])
                + "\n\n"
                + "Would you like to update the painting controls area coordinates?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes,
            )
            if btn == QMessageBox.Yes:
                self.parent.ui.log_TextEdit.append("Controls area position updated...")
                self.settings.setValue("ctrl_x", str(ctrl_area[0]))
                self.settings.setValue("ctrl_y", str(ctrl_area[1]))
                self.settings.setValue("ctrl_w", str(ctrl_area[2]))
                self.settings.setValue("ctrl_h", str(ctrl_area[3]))

            self.update()

    def locate_control_area_opencv(self):
        """Automatically tries to find the painting control area with opencv.
        Returns:    ctrl_x,
                    ctrl_y,
                    ctrl_w,
                    ctrl_h
                    False, if no control area was found
        """
        screenshot = pyautogui.screenshot()
        screen_w, screen_h = screenshot.size

        image_gray = cv2.cvtColor(numpy.array(screenshot), cv2.COLOR_BGR2GRAY)

        tmpl = cv2.imread("opencv_template/rust_palette_template.png", 0)
        tmpl_w, tmpl_h = tmpl.shape[::-1]

        x_coord, y_coord = 0, 0
        threshold = 0.8

        for loop in range(50):
            matches = cv2.matchTemplate(image_gray, tmpl, cv2.TM_CCOEFF_NORMED)
            loc = numpy.where(matches >= threshold)

            x_list, y_list = [], []
            for point in zip(*loc[::-1]):
                x_list.append(point[0])
                y_list.append(point[1])

            if x_list:
                x_coord = int(sum(x_list) / len(x_list))
                y_coord = int(sum(y_list) / len(y_list))
                return x_coord, y_coord, tmpl_w, tmpl_h

            tmpl_w, tmpl_h = int(tmpl.shape[1] * 1.035), int(tmpl.shape[0] * 1.035)
            tmpl = cv2.resize(tmpl, (int(tmpl_w), int(tmpl_h)))

            if tmpl_w > screen_w or tmpl_h > screen_h or loop == 49:
                return False

    def calculate_ctrl_tools_positioning(self):
        """This function calculates the positioning of the different controls in the painting control area.
        The brush size, type and opacity along with all the different colors.
        Updates:    self.ctrl_update
                    self.ctrl_size
                    self.ctrl_brush
                    self.ctrl_opacity
                    self.ctrl_color
        """
        # Reset
        self.ctrl_update = 0
        self.ctrl_size = []
        self.ctrl_brush = []
        self.ctrl_opacity = []
        self.ctrl_color = []

        ctrl_x = int(self.settings.value("ctrl_x", default_settings["ctrl_x"]))
        ctrl_y = int(self.settings.value("ctrl_y", default_settings["ctrl_y"]))
        ctrl_w = int(self.settings.value("ctrl_w", default_settings["ctrl_w"]))
        ctrl_h = int(self.settings.value("ctrl_h", default_settings["ctrl_h"]))

        # Update button position (at 50% from left, 105.56% from top)
        self.ctrl_update = (ctrl_x + (ctrl_w * 0.5), ctrl_y + (ctrl_h * 1.0556))

        # Size box for text input (at 89.54% from left, 29.96% from top)
        self.ctrl_size.append((ctrl_x + (ctrl_w * 0.8954), ctrl_y + (ctrl_h * 0.2996)))

        # Brush types
        # Paint Brush is 38.17% from the left edge and 9.54% from the top edge
        self.ctrl_brush.append((ctrl_x + (ctrl_w * 0.3817), ctrl_y + (ctrl_h * 0.0954)))
        # Medium Round Brush is 26.42% from the left edge and 24.4% from the top edge
        self.ctrl_brush.append((ctrl_x + (ctrl_w * 0.2642), ctrl_y + (ctrl_h * 0.244)))
        # Light Round Brush is 14.5% from the left edge and 24.4% from the top edge
        self.ctrl_brush.append((ctrl_x + (ctrl_w * 0.145), ctrl_y + (ctrl_h * 0.244)))
        # Heavy Round Brush is 38.17% from the left edge and 24.4% from the top edge
        self.ctrl_brush.append((ctrl_x + (ctrl_w * 0.3817), ctrl_y + (ctrl_h * 0.244)))
        # Heavy Square Brush is 49.72% from the left edge and 24.4% from the top edge
        self.ctrl_brush.append((ctrl_x + (ctrl_w * 0.4972), ctrl_y + (ctrl_h * 0.244)))

        # Opacity box for text input (at 89.54% from left, 39.25% from top)
        self.ctrl_opacity.append(
            (ctrl_x + (ctrl_w * 0.8954), ctrl_y + (ctrl_h * 0.3925))
        )

        # Calculate color grid positions
        # First row and column of colors is 52.03% down from the top edge, 14.68% from the left edge
        first_color_x = ctrl_x + (ctrl_w * 0.1468)
        first_color_y = ctrl_y + (ctrl_h * 0.5203)

        # Each color column is 25% away from the last (with 4 columns)
        column_spacing = ctrl_w * 0.25

        # Each color row is 3% down from the last (with 16 rows)
        row_spacing = ctrl_h * 0.03

        # Populate the color grid (4 columns x 16 rows = 64 colors)
        for row in range(16):
            for column in range(4):
                color_x = first_color_x + (column * column_spacing)
                color_y = first_color_y + (row * row_spacing)
                self.ctrl_color.append((color_x, color_y))

    def calculate_statistics(self):
        """Calculate what colors, how many pixels and lines for the painting
        Updates:    self.img_colors,
                    self.tot_pixels,
                    self.pixels,
                    self.lines
        """
        minimum_line_width = int(
            self.settings.value(
                "minimum_line_width", default_settings["minimum_line_width"]
            )
        )
        self.update_skip_colors()
        pixel_arr = self.quantized_img.load()

        self.img_colors = []
        self.tot_pixels = 0
        self.pixels = 0
        self.lines = 0

        for color in self.quantized_img.getcolors():
            if color[1] not in self.skip_colors:
                self.tot_pixels += color[0]
                self.img_colors.append(color[1])

        for color in self.img_colors:
            is_first_point_of_row = True
            is_last_point_of_row = False
            is_previous_color = False
            is_line = False
            pixels_in_line = 0

            for y in range(self.canvas_h):
                is_first_point_of_row = True
                is_last_point_of_row = False
                is_previous_color = False
                is_line = False
                pixels_in_line = 0

                for x in range(self.canvas_w):
                    if x == (self.canvas_w - 1):
                        is_last_point_of_row = True

                    if is_first_point_of_row:
                        is_first_point_of_row = False
                        if pixel_arr[x, y] == color:
                            is_previous_color = True
                            pixels_in_line = 1
                        continue

                    if pixel_arr[x, y] == color:
                        if is_previous_color:
                            if is_last_point_of_row:
                                if pixels_in_line >= minimum_line_width:
                                    self.lines += 1
                                else:
                                    self.pixels += pixels_in_line + 1
                            else:
                                is_line = True
                                pixels_in_line += 1
                        else:
                            if is_last_point_of_row:
                                self.pixels += 1
                            else:
                                is_previous_color = True
                                pixels_in_line = 1
                    else:
                        if is_previous_color:
                            if is_line:
                                is_line = False

                                if is_last_point_of_row:
                                    if pixels_in_line >= minimum_line_width:
                                        self.lines += 1
                                    else:
                                        self.pixels += pixels_in_line + 1
                                    continue

                                if pixels_in_line >= minimum_line_width:
                                    self.lines += 1
                                else:
                                    self.pixels += pixels_in_line + 1
                                pixels_in_line = 0
                            else:
                                self.pixels += 1
                            is_previous_color = False
                        else:
                            is_line = False
                            pixels_in_line = 0

    def calculate_estimated_time(self):
        """Calculate estimated time for the painting process.
        Updates:    Estimated time for clicking and lines
                    Estimated time for only clicking
        """
        one_click_time = self.click_delay + 0.001
        one_click_time = one_click_time * 2 if self.use_double_click else one_click_time
        one_line_time = (self.line_delay * 5) + 0.0035
        set_paint_controls_time = (
            len(self.img_colors) * ((2 * self.click_delay) + (2 * self.ctrl_area_delay))
        ) + ((2 * self.click_delay) + (2 * self.ctrl_area_delay))
        est_time_lines = int(
            (self.pixels * one_click_time)
            + (self.lines * one_line_time)
            + set_paint_controls_time
        )
        est_time_click = int(
            (self.tot_pixels * one_click_time) + set_paint_controls_time
        )

        if not bool(self.settings.value("draw_lines", default_settings["draw_lines"])):
            self.prefer_lines = False
            self.estimated_time = est_time_click
        elif est_time_lines < est_time_click:
            self.prefer_lines = True
            self.estimated_time = est_time_lines
        else:
            self.prefer_lines = False
            self.estimated_time = est_time_click

    def click_pixel(self, x=0, y=0):
        """Click the pixel"""
        if isinstance(x, tuple):
            pyautogui.click(x[0], x[1])
            if self.use_double_click:
                pyautogui.click(x[0], x[1])
        else:
            pyautogui.click(x, y)
            if self.use_double_click:
                pyautogui.click(x, y)

    def draw_line(self, point_A, point_B):
        """Draws a line between point_A and point_B."""
        pyautogui.PAUSE = self.line_delay
        pyautogui.mouseDown(button="left", x=point_A[0], y=point_A[1])
        pyautogui.keyDown("shift")
        pyautogui.moveTo(point_B[0], point_B[1])
        pyautogui.keyUp("shift")
        pyautogui.mouseUp(button="left")
        pyautogui.PAUSE = self.click_delay

    def key_event(self, key):
        """Key-press thread during painting."""
        try:
            key_str = str(key.char)
        except Exception as _:
            key_str = str(key.name)

        if key_str == self.pause_key:  # Pause
            self.paused = not self.paused
        elif key_str == self.skip_key:  # Skip color
            self.paused = False
            self.skip_current_color = True
        elif key_str == self.abort_key:  # Abort
            self.paused = False
            self.abort = True

    def shutdown(self, listener, start_time, state=0):
        """Shutdown the painting process"""
        self.parent.ui.load_image_PushButton.setEnabled(True)
        self.parent.ui.identify_ctrl_PushButton.setEnabled(True)
        self.parent.ui.paint_image_PushButton.setEnabled(True)
        self.parent.ui.settings_PushButton.setEnabled(True)

        listener.stop()
        elapsed_time = int(time.time() - start_time)
        self.parent.ui.log_TextEdit.append(
            "Elapsed time: " + str(time.strftime("%H:%M:%S", time.gmtime(elapsed_time)))
        )
        QApplication.processEvents()
        self.hotkey_label.hide()

        if state == 0:
            self.parent.ui.progress_ProgressBar.setValue(100)

        if bool(
            self.settings.value("window_topmost", default_settings["window_topmost"])
        ):
            self.parent.setWindowFlags(
                self.parent.windowFlags() & ~Qt.WindowStaysOnTopHint
            )
            self.parent.show()
        self.parent.activateWindow()

    def choose_painting_controls(self, size, brush, color):
        """Choose the paint controls"""
        # Select brush type
        if self.current_ctrl_brush != brush:
            self.current_ctrl_brush = brush
            self.click_pixel(self.ctrl_brush[brush])
            time.sleep(self.ctrl_area_delay)

        # Set brush size (text input box)
        # size 0: small (2), 1: medium (4), 2: large (6), etc.
        # Convert size to appropriate text value
        brush_size = str(2 + (size * 2)) if size >= 0 else "2"  # Default to 2
        if self.current_ctrl_size != size:
            self.current_ctrl_size = size
            # Click the size text box
            self.click_pixel(self.ctrl_size[0])
            time.sleep(self.ctrl_area_delay)
            # Type the brush size
            pyautogui.typewrite(brush_size)
            time.sleep(0.1)
            # Press Enter
            pyautogui.press("enter")
            time.sleep(self.ctrl_area_delay)

        # Set opacity (text input box)
        # Calculate opacity value based on color index
        opacity_value = "100"  # Default opacity: 100%
        if color % 4 == 1:
            opacity_value = "75"
        elif color % 4 == 2:
            opacity_value = "50"
        elif color % 4 == 3:
            opacity_value = "25"

        # Click the opacity text box
        self.click_pixel(self.ctrl_opacity[0])
        time.sleep(self.ctrl_area_delay)
        # Type the opacity value
        pyautogui.typewrite(opacity_value)
        time.sleep(0.1)
        # Press Enter
        pyautogui.press("enter")
        time.sleep(self.ctrl_area_delay)

        # Select the color from the grid
        if self.current_ctrl_color != color:
            self.current_ctrl_color = color
            self.click_pixel(self.ctrl_color[color % 64])
            time.sleep(self.ctrl_area_delay)

    def update_skip_colors(self):
        """Updates the skip colors list"""
        self.skip_colors = []
        temp_skip_colors = self.settings.value(
            "skip_colors", default_settings["skip_colors"], "QStringList"
        )
        if len(temp_skip_colors) != 0:
            for color in temp_skip_colors:
                if hex_to_rgb(color) in self.updated_palette:
                    self.skip_colors.append(
                        self.updated_palette.index(hex_to_rgb(color))
                    )

        # Add background color indices to skip_colors if skip_background_color is enabled
        skip_background_color = bool(
            self.settings.value(
                "skip_background_color", default_settings["skip_background_color"]
            )
        )
        
        if skip_background_color and hasattr(self, 'background_opacities'):
            # Add all background opacities to skip colors
            self.skip_colors.extend(self.background_opacities)

        self.skip_colors = list(map(int, self.skip_colors))

    def start_painting(self):
        """Start the painting"""
        # Update global variables
        self.use_hidden_colors = bool(
            self.settings.value("hidden_colors", default_settings["hidden_colors"])
        )
        self.pause_key = str(
            self.settings.value("pause_key", default_settings["pause_key"])
        ).lower()
        self.skip_key = str(
            self.settings.value("skip_key", default_settings["skip_key"])
        ).lower()
        self.abort_key = str(
            self.settings.value("abort_key", default_settings["abort_key"])
        ).lower()

        # Update local variables
        minimum_line_width = int(
            self.settings.value(
                "minimum_line_width", default_settings["minimum_line_width"]
            )
        )
        ctrl_x = int(self.settings.value("ctrl_x", default_settings["ctrl_x"]))
        ctrl_y = int(self.settings.value("ctrl_h", default_settings["ctrl_y"]))
        ctrl_w = int(self.settings.value("ctrl_w", default_settings["ctrl_w"]))
        ctrl_h = int(self.settings.value("ctrl_h", default_settings["ctrl_h"]))
        brush_type = int(
            self.settings.value("brush_type", default_settings["brush_type"])
        )
        use_brush_opacities = bool(
            self.settings.value("brush_opacities", default_settings["brush_opacities"])
        )
        hide_preview_paint = bool(
            self.settings.value(
                "hide_preview_paint", default_settings["hide_preview_paint"]
            )
        )
        update_canvas_end = bool(
            self.settings.value(
                "update_canvas_end", default_settings["update_canvas_end"]
            )
        )
        window_topmost = bool(
            self.settings.value("window_topmost", default_settings["window_topmost"])
        )
        update_canvas = bool(
            self.settings.value("update_canvas", default_settings["update_canvas"])
        )
        show_info = bool(
            self.settings.value(
                "show_information", default_settings["show_information"]
            )
        )

        self.update()  # Update click, line, ctrl_area delay
        self.update_skip_colors()  # Update self.skip_colors variable
        if not self.locate_canvas_area():
            return  # Locate the canvas
        if not self.convert_img():
            return  # Quantize the image

        # Clear the log
        self.parent.ui.progress_ProgressBar.setValue(0)
        self.parent.ui.log_TextEdit.clear()
        self.parent.ui.log_TextEdit.append("Calculating statistics...")
        QApplication.processEvents()

        self.calculate_ctrl_tools_positioning()  # Calculate the control tools positioning
        self.calculate_statistics()  # Calculate statistics (colors, total pixels, lines)
        self.calculate_estimated_time()  # Calculate the estimated time

        # Opens a information dialog
        question = (
            "Dimensions: \t\t\t\t" + str(self.canvas_w) + " x " + str(self.canvas_h)
        )
        question += "\nNumber of colors:\t\t\t" + str(len(self.img_colors))
        question += "\nTotal Number of pixels to paint: \t" + str(self.tot_pixels)
        question += "\nNumber of pixels to paint:\t\t" + str(self.pixels)
        question += "\nNumber of lines:\t\t\t" + str(self.lines)
        question += "\nEst. painting time:\t\t\t" + str(
            time.strftime("%H:%M:%S", time.gmtime(self.estimated_time))
        )
        question += "\n\nWould you like to start the painting?"
        if show_info:
            btn = QMessageBox.question(
                self.parent,
                None,
                question,
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes,
            )
            if btn == QMessageBox.No:
                return

        # Disable mainwindow buttons while painting
        self.parent.ui.load_image_PushButton.setEnabled(False)
        self.parent.ui.identify_ctrl_PushButton.setEnabled(False)
        self.parent.ui.paint_image_PushButton.setEnabled(False)
        self.parent.ui.settings_PushButton.setEnabled(False)

        # If window_topmost setting is set, activate window always on top functionality
        if window_topmost:
            self.parent.setWindowFlags(
                self.parent.windowFlags() | Qt.WindowStaysOnTopHint
            )
            self.parent.show()

        # If hide_preview_paint and self.parent.is_expanded, close image preview
        if hide_preview_paint and self.parent.is_expanded:
            self.parent.preview_clicked()

        # Add label info about pause, skip and abort keys
        self.hotkey_label = QLabel(self.parent)
        self.hotkey_label.setGeometry(QRect(10, 425, 221, 21))
        self.hotkey_label.setText(
            self.pause_key
            + " = Pause        "
            + self.skip_key
            + " = Skip        "
            + self.abort_key
            + " = Abort"
        )
        self.hotkey_label.show()

        # Paint the background with the default background color
        self.click_pixel(self.ctrl_size[0])  # To set focus on the rust window
        time.sleep(0.5)
        self.click_pixel(self.ctrl_size[0])
        if (
            bool(
                self.settings.value(
                    "paint_background", default_settings["paint_background"]
                )
            )
            and self.background_color is not None
        ):
            self.parent.ui.log_TextEdit.append("Painting background for you...")
            self.choose_painting_controls(5, 3, self.background_color)
            x_start = self.canvas_x + 10
            x_end = self.canvas_x + self.canvas_w - 10
            loops = int((self.canvas_h - 10) / 10)
            for i in range(1, loops + 1):
                self.draw_line(
                    (x_start, self.canvas_y + (10 * i)),
                    (x_end, self.canvas_y + (10 * i)),
                )

        # Print out the start time, estimated time and estimated finish time
        self.parent.ui.log_TextEdit.append(
            "Start time:\t" + str((datetime.datetime.now()).time().strftime("%H:%M:%S"))
        )
        self.parent.ui.log_TextEdit.append(
            "Est. time:\t"
            + str(time.strftime("%H:%M:%S", time.gmtime(self.estimated_time)))
        )
        self.parent.ui.log_TextEdit.append(
            "Est. finished:\t"
            + str(
                (
                    datetime.datetime.now()
                    + datetime.timedelta(seconds=self.estimated_time)
                )
                .time()
                .strftime("%H:%M:%S")
            )
        )
        QApplication.processEvents()

        self.paused = False
        self.abort = False
        pixel_counter = 0
        progress_percent = 0
        previous_progress_percent = None

        start_time = time.time()
        pixel_arr = self.quantized_img.load()

        # Start keyboard listener
        listener = keyboard.Listener(on_press=self.key_event)
        listener.start()

        for counter, color in enumerate(self.img_colors):
            self.skip_current_color = False
            # Print current color to the log
            color_hex = rgb_to_hex(self.updated_palette[color])
            self.parent.ui.log_TextEdit.append(
                "("
                + str((counter + 1))
                + "/"
                + str((len(self.img_colors)))
                + ") Current color: "
                + '<span style=" font-size:8pt; font-weight:600; color:'
                + str(color_hex)
                + ';" >█'
                + str(color_hex)
                + "█</span>"
            )

            QApplication.processEvents()

            # Choose painting controls
            self.choose_painting_controls(0, brush_type, color)

            for y in range(self.canvas_h):
                if self.skip_current_color:
                    break

                # Calculate percentage for progress bar
                progress_percent = int(pixel_counter / int(self.tot_pixels / 100))
                if progress_percent != previous_progress_percent:
                    previous_progress_percent = progress_percent
                    self.parent.ui.progress_ProgressBar.setValue(progress_percent)

                # Reset variables
                is_first_point_of_row = True
                is_last_point_of_row = False
                is_previous_color = False
                is_line = False
                pixels_in_line = 0

                for x in range(self.canvas_w):
                    while self.paused:
                        QApplication.processEvents()
                    if self.skip_current_color:
                        break
                    if self.abort:
                        self.parent.ui.log_TextEdit.append("Aborted...")
                        return self.shutdown(listener, start_time, 1)

                    if x == (self.canvas_w - 1):
                        is_last_point_of_row = True

                    if is_first_point_of_row and self.prefer_lines:
                        is_first_point_of_row = False
                        if pixel_arr[x, y] == color:
                            first_point = (self.canvas_x + x, self.canvas_y + y)
                            is_previous_color = True
                            pixels_in_line = 1
                        continue

                    if pixel_arr[x, y] == color:
                        if not self.prefer_lines:
                            self.click_pixel(self.canvas_x + x, self.canvas_y + y)
                            pixel_counter += 1
                            continue
                        if is_previous_color:
                            if is_last_point_of_row:
                                if pixels_in_line >= minimum_line_width:
                                    self.draw_line(
                                        first_point,
                                        (self.canvas_x + x, self.canvas_y + y),
                                    )
                                    pixel_counter += pixels_in_line
                                else:
                                    for index in range(pixels_in_line):
                                        self.click_pixel(
                                            first_point[0] + index, self.canvas_y + y
                                        )
                                    self.click_pixel(
                                        self.canvas_x + x, self.canvas_y + y
                                    )
                                    pixel_counter += pixels_in_line + 1
                            else:
                                is_line = True
                                pixels_in_line += 1
                        else:
                            if is_last_point_of_row:
                                self.click_pixel(self.canvas_x + x, self.canvas_y + y)
                                pixel_counter += 1
                            else:
                                first_point = (self.canvas_x + x, self.canvas_y + y)
                                is_previous_color = True
                                pixels_in_line = 1
                    else:
                        if not self.prefer_lines:
                            continue
                        if is_previous_color:
                            if is_line:
                                is_line = False

                                if is_last_point_of_row:
                                    if pixels_in_line >= minimum_line_width:
                                        self.draw_line(
                                            first_point,
                                            (
                                                self.canvas_x + (x - 1),
                                                self.canvas_y + y,
                                            ),
                                        )
                                        pixel_counter += pixels_in_line
                                    else:
                                        for index in range(pixels_in_line):
                                            self.click_pixel(
                                                first_point[0] + index,
                                                self.canvas_y + y,
                                            )
                                        pixel_counter += pixels_in_line
                                    continue

                                if pixels_in_line >= minimum_line_width:
                                    self.draw_line(
                                        first_point,
                                        (self.canvas_x + (x - 1), self.canvas_y + y),
                                    )
                                    pixel_counter += pixels_in_line
                                else:
                                    for index in range(pixels_in_line):
                                        self.click_pixel(
                                            first_point[0] + index, self.canvas_y + y
                                        )
                                    pixel_counter += pixels_in_line
                                pixels_in_line = 0

                            else:
                                self.click_pixel(
                                    self.canvas_x + (x - 1), self.canvas_y + y
                                )
                                pixel_counter += 1
                            is_previous_color = False
                        else:
                            is_line = False
                            pixels_in_line = 0

            if update_canvas:
                self.click_pixel(self.ctrl_update)

        if update_canvas_end:
            self.click_pixel(self.ctrl_update)

        return self.shutdown(listener, start_time)
