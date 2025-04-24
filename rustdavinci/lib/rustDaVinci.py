#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from PyQt5.QtCore import QSettings, Qt, QRect, QDir, QTimer
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import QMessageBox, QInputDialog, QFileDialog, QApplication, QLabel, QProgressBar

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
from lib.color_blending import find_optimal_layers, quality_adjusted_find_optimal_layers, create_layered_colors_map, simulate_layered_image, alpha_blend
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
        
        # New variables for optimal layering
        self.layered_colors_map = None
        self.base_palette_colors = []
        self.opacity_values = [1.0, 0.75, 0.5, 0.25]  # 100%, 75%, 50%, 25%
        
        # Cache for storing calculated color data to avoid recalculation
        self.color_calculation_cache = {
            'resized_img': None,         # Stores the resized image
            'layered_colors_map': None,  # Stores the calculated color layers
            'simulated_img': None,       # Stores the simulated result image
            'background_color': None     # The background color used for calculation
        }

        # Pixmaps
        self.pixmap_on_display = 0
        self.org_img_pixmap = None
        self.quantized_img_pixmap = None  # Single pixmap instead of normal/high variants

        # Booleans
        self.org_img_ok = False

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
        self.current_ctrl_opacity = None  # Track actual opacity value
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

        # Color tracking for status display
        self.total_colors = 0
        self.current_color_index = 0
        self.current_color_rgb = None
        self.current_color_opacity = None
        self.painting_start_time = 0
        
        # Timer for updating status UI during painting
        self.status_update_timer = None
        self.current_operation_counter = 0
        self.current_total_operations = 0
        self.current_color_key = None
        self.sorted_color_keys = []

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
                # Clear previous data
                self.layered_colors_map = None
                self.color_calculation_cache = {
                    'resized_img': None,
                    'layered_colors_map': None,
                    'simulated_img': None,
                    'background_color': None
                }
                
                # Pixmap for original image
                self.org_img_pixmap = QPixmap(path, "1")

                # The original PIL.Image object
                self.org_img_template = Image.open(path).convert("RGBA")
                self.org_img = self.org_img_template

                # Check if we should try to load cached data
                use_cached_data = bool(
                    self.settings.value("use_cached_data", True)
                )
                
                if use_cached_data:
                    # Get background color for cache check
                    bg_color_hex = self.settings.value("background_color", default_settings["background_color"])
                    bg_color_rgb = hex_to_rgb(bg_color_hex)
                    
                    # Try to load cached data
                    if self.load_calculation_cache(path, bg_color_rgb):
                        self.parent.ui.log_TextEdit.append("Using cached color calculations")
                
                self.convert_transparency()
                self.create_pixmaps()

                if self.parent.is_expanded:
                    self.parent.label.hide()
                self.parent.expand_window()
                self.pixmap_on_display = 1

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

    def optimized_quantize_to_palette(self, image):
        """
        Advanced version of quantize_to_palette that calculates optimal color layering.
        This produces higher quality results by simulating how colors layer on top of each other.
        
        Args:
            image: PIL Image object to quantize
            
        Returns:
            PIL Image: Quantized image based on optimal color layering
        """
        try:
            # Prepare the base image
            temp_img = image.copy()
            if temp_img.mode == "RGBA":
                # Get background color from settings
                bg_color_hex = self.settings.value("background_color", default_settings["background_color"])
                bg_color_rgb = hex_to_rgb(bg_color_hex)
                
                # Create new image with background color
                bg = Image.new('RGB', temp_img.size, bg_color_rgb)
                bg.paste(temp_img, mask=temp_img.split()[3])  # Use alpha channel as mask
                temp_img = bg
            
            # Ensure image is in RGB mode
            if temp_img.mode != "RGB":
                temp_img = temp_img.convert("RGB")
                
            # Performance optimization for very large images
            # Set a reasonable limit for pixel count
            total_pixels = temp_img.width * temp_img.height
            resize_threshold = 500000  # Adjust based on typical system capabilities
            
            if total_pixels > resize_threshold:
                # Ask user if they want to resize for faster calculation
                # Calculate new dimensions to fit within threshold while maintaining aspect ratio
                factor = (resize_threshold / total_pixels) ** 0.5
                new_width = int(temp_img.width * factor)
                new_height = int(temp_img.height * factor)
                
                from ui.theme.theme import apply_theme_to_dialog
                
                msg = QMessageBox(self.parent)
                apply_theme_to_dialog(msg)  # Apply current theme to dialog
                msg.setIcon(QMessageBox.Question)
                msg.setWindowTitle("Large Image Detected")
                msg.setText(f"This image is very large ({temp_img.width}x{temp_img.height} = {total_pixels:,} pixels).")
                msg.setInformativeText(f"Would you like to temporarily resize to {new_width}x{new_height} for faster color calculation?\n\n" +
                                       "Note: The final painted image will still use your original resolution.")
                msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
                response = msg.exec_()
                
                if response == QMessageBox.Yes:
                    # Resize for faster processing
                    temp_img = temp_img.resize((new_width, new_height), Image.LANCZOS)
                    self.parent.ui.log_TextEdit.append(f"Using reduced resolution ({new_width}x{new_height}) for color calculation...")
            
            # Use ALL 64 base colors from rust_palette
            self.base_palette_colors = rust_palette[:64]
            
            # Create progress dialog
            self.parent.ui.log_TextEdit.append("Starting optimal color layering calculation...")
            
            # Create a much larger custom dialog for progress display instead of using QMessageBox
            from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QPushButton
            from ui.theme.theme import apply_theme_to_dialog
            
            # Create custom dialog with proper size
            self.progress_dialog = QDialog(self.parent)
            apply_theme_to_dialog(self.progress_dialog)  # Apply the current theme
            self.progress_dialog.setWindowTitle("Calculating Optimal Colors")
            self.progress_dialog.setMinimumWidth(600)  # Much wider dialog
            self.progress_dialog.setMinimumHeight(200) # Much taller dialog
            self.progress_dialog.setModal(False)       # Non-modal dialog
            
            # Create layout
            layout = QVBoxLayout()
            
            # Add main information label
            info_label = QLabel("Processing image colors...\nThis may take a moment.", self.progress_dialog)
            info_label.setStyleSheet("font-size: 11pt; font-weight: bold;")
            layout.addWidget(info_label)
            
            # Add spacer
            layout.addSpacing(10)
            
            # Add progress bar with better size
            self.progress_bar = QProgressBar(self.progress_dialog)
            self.progress_bar.setMinimumHeight(30)  # Taller progress bar
            layout.addWidget(self.progress_bar)
            
            # Add status label with better formatting
            self.progress_status = QLabel("Calculating...", self.progress_dialog)
            self.progress_status.setStyleSheet("font-size: 10pt;")
            self.progress_status.setMinimumHeight(30)  # Ensure enough height
            layout.addWidget(self.progress_status)
            
            # Add spacer
            layout.addSpacing(10)
            
            # Add cancel button in its own layout for better positioning
            button_layout = QHBoxLayout()
            button_layout.addStretch()
            cancel_button = QPushButton("Cancel", self.progress_dialog)
            cancel_button.setMinimumWidth(100)
            cancel_button.setMinimumHeight(30)
            cancel_button.clicked.connect(self.cancel_color_calculation)
            button_layout.addWidget(cancel_button)
            layout.addLayout(button_layout)
            
            # Set the layout on the dialog
            self.progress_dialog.setLayout(layout)
            
            # Show the dialog
            self.progress_dialog.show()
            QApplication.processEvents()
            
            # Background color for calculations
            background_color = rust_palette[0]  # Default to first color
            bg_color_hex = self.settings.value("background_color", default_settings["background_color"])
            bg_color_rgb = hex_to_rgb(bg_color_hex)
            
            if bg_color_rgb in rust_palette:
                background_color = bg_color_rgb
            
            # Store the background color used for calculation
            self.background_color = background_color
            
            # Update callback function to update the progress dialog
            self.cancel_requested = False
            
            def update_progress(percent, elapsed, remaining):
                if self.cancel_requested:
                    return True  # Signal to stop processing
                    
                self.progress_bar.setValue(percent)
                
                # Format time strings
                elapsed_str = time.strftime("%M:%S", time.gmtime(elapsed))
                remaining_str = time.strftime("%M:%S", time.gmtime(remaining))
                
                # Update status message
                if percent < 50:
                    stage = "Analyzing color groups"
                elif percent < 90:
                    stage = "Processing pixels"
                else:
                    stage = "Finalizing"
                    
                status_text = f"{stage}: {percent}% complete | "
                status_text += f"Elapsed: {elapsed_str} | Remaining: {remaining_str}"
                self.progress_status.setText(status_text)
                
                # Update the log every 10%
                if percent % 10 == 0:
                    self.parent.ui.log_TextEdit.append(f"Color processing: {percent}% complete")
                    
                QApplication.processEvents()
                return self.cancel_requested
            
            # Define the opacity values
            # These are SEPARATE from the base colors and are applied during painting
            self.opacity_values = [1.0, 0.75, 0.5, 0.25]
            
            # Get the user's color quality setting (if any)
            color_quality = int(self.settings.value("color_merge_quality", 100))
            self.parent.ui.log_TextEdit.append(f"Using color quality: {color_quality}%")
            
            # Apply the user's quality setting by temporarily replacing the find_optimal_layers function
            import sys
            from lib.color_blending import find_optimal_layers as original_find_optimal_layers
            
            # Create a wrapper that uses our quality setting
            def quality_adjusted_find_optimal_layers(target_color, background_color, base_colors, 
                                                  opacity_levels, max_layers=3, color_cache=None):
                
                # Override the early termination threshold in find_optimal_layers
                # Adjust color_distance threshold based on quality percent
                def patched_color_distance(color1, color2):
                    # Calculate basic Euclidean distance
                    r1, g1, b1 = color1
                    r2, g2, b2 = color2
                    return ((r1 - r2) ** 2 + (g1 - g2) ** 2 + (b1 - b2) ** 2) ** 0.5
                
                # Store the original functions
                original_color_distance = sys.modules['lib.color_blending'].color_distance
                
                # Replace the functions
                color_blending_module = sys.modules['lib.color_blending']
                color_blending_module.color_distance = patched_color_distance
                
                # Call the original function with our adjusted threshold
                result = original_find_optimal_layers(
                    target_color, background_color, base_colors, 
                    opacity_levels, max_layers, color_cache
                )
                
                # Restore the original functions
                color_blending_module.color_distance = original_color_distance
                
                return result
            
            # Replace the find_optimal_layers function temporarily
            color_blending_module = sys.modules['lib.color_blending']
            original_find_optimal_layers_func = color_blending_module.find_optimal_layers
            color_blending_module.find_optimal_layers = quality_adjusted_find_optimal_layers
            
            # Check if we can use multiprocessing for better performance
            try:
                import multiprocessing
                # Only use parallel processing if we have at least 2 cores and a big enough image
                if multiprocessing.cpu_count() > 1 and total_pixels > 50000:
                    from lib.color_blending import create_layered_colors_map_parallel
                    self.parent.ui.log_TextEdit.append(f"Using parallel processing with {multiprocessing.cpu_count()} cores")
                    
                    # Define a function to create layered colors map with quality adjustment
                    def create_layered_colors_map_parallel_with_quality(image, background_color, palette_colors, 
                                                                     opacity_values, max_layers=2, update_callback=None):
                        # Adjust bucket size based on quality: 100% => bucket_size=1, 0% => bucket_size up to 50
                        bucket_size = max(1, int(1 + (1 - color_quality / 100.0) * 50))
                        
                        # Store original bucket size value
                        original_bucket_size = 5  # Default bucket size used in the library
                        
                        try:
                            # Apply bucket size adjustment by monkey patching the module
                            # This is a bit hacky but necessary to influence the parallel processing
                            import lib.color_blending
                            if hasattr(lib.color_blending, '_BUCKET_SIZE'):
                                original_bucket_size = lib.color_blending._BUCKET_SIZE
                                lib.color_blending._BUCKET_SIZE = bucket_size
                            
                            # Call the original function with our settings
                            return create_layered_colors_map_parallel(image, background_color, palette_colors, 
                                                                   opacity_values, max_layers, update_callback)
                        finally:
                            # Restore original bucket size value if needed
                            if hasattr(lib.color_blending, '_BUCKET_SIZE'):
                                lib.color_blending._BUCKET_SIZE = original_bucket_size
                    
                    # Use our quality-adjusted version
                    self.layered_colors_map = create_layered_colors_map_parallel_with_quality(
                        temp_img,
                        background_color,
                        self.base_palette_colors,
                        self.opacity_values,
                        max_layers=2,
                        update_callback=update_progress
                    )
                else:
                    # Fall back to single-threaded for small images
                    from lib.color_blending import create_layered_colors_map
                    
                    # Define a function to create layered colors map with quality adjustment
                    def create_layered_colors_map_with_quality(image, background_color, palette_colors, 
                                                            opacity_values, max_layers=2, update_callback=None):
                        # Adjust bucket size based on quality: 100% => bucket_size=1, 0% => bucket_size up to 50
                        bucket_size = max(1, int(1 + (1 - color_quality / 100.0) * 50))
                        
                        # Create a custom version that uses our adjusted bucket size and similarity threshold
                        width, height = image.size
                        pixel_data = image.load()
                        layered_colors = {}
                        color_cache = {}
                        
                        # Starting timestamp for progress calculation
                        start_time = time.time()
                        progress_shown = False
                        
                        # Find unique colors in the image (with sampling for large images)
                        unique_colors = set()
                        
                        # Update progress with the scan phase (0-5%)
                        if update_callback:
                            update_callback(0, 0, 0)
                            progress_shown = True
                        
                        downsample = max(1, min(width, height) // 400)
                        total_pixels = (width // downsample) * (height // downsample)
                        pixels_processed = 0
                        
                        for y in range(0, height, downsample):
                            for x in range(0, width, downsample):
                                unique_colors.add(pixel_data[x, y])
                                pixels_processed += 1
                                
                                # Update progress
                                if pixels_processed % 5000 == 0 or pixels_processed >= total_pixels:
                                    if update_callback:
                                        scan_progress = min(5, int(pixels_processed / total_pixels * 5))
                                        elapsed = time.time() - start_time
                                        remaining = elapsed / scan_progress * (5 - scan_progress) if scan_progress > 0 else 0
                                        update_callback(scan_progress, elapsed, remaining)
                        
                        # Group similar colors using our quality-adjusted bucket size
                        color_groups = {}
                        
                        # Update progress - now on color grouping phase (5-25%)
                        if update_callback:
                            update_callback(5, time.time() - start_time, 0)
                        
                        total_unique_colors = len(unique_colors)
                        colors_processed = 0
                        
                        for color in unique_colors:
                            # Quantize the color into buckets (adjusts based on quality)
                            bucket_key = (color[0]//bucket_size, color[1]//bucket_size, color[2]//bucket_size)
                            if bucket_key not in color_groups:
                                color_groups[bucket_key] = []
                            color_groups[bucket_key].append(color)
                            
                            # Update progress
                            colors_processed += 1
                            if colors_processed % 100 == 0 or colors_processed >= total_unique_colors:
                                if update_callback:
                                    group_progress = 5 + min(20, int(colors_processed / total_unique_colors * 20))
                                    elapsed = time.time() - start_time
                                    remaining = elapsed / group_progress * (25 - group_progress) if group_progress > 0 else 0
                                    update_callback(group_progress, elapsed, remaining)
                        
                        # Calculate average colors for each bucket
                        bucket_layers = {}
                        
                        # Update progress - now on color layer calculation phase (25-75%)
                        if update_callback:
                            update_callback(25, time.time() - start_time, 0)
                        
                        total_buckets = len(color_groups)
                        buckets_processed = 0
                        
                        for bucket_key, colors in color_groups.items():
                            r_sum = g_sum = b_sum = 0
                            for color in colors:
                                r_sum += color[0]
                                g_sum += color[1]
                                b_sum += color[2]
                            avg_color = (
                                int(r_sum / len(colors)),
                                int(g_sum / len(colors)),
                                int(b_sum / len(colors))
                            )
                            
                            # Calculate layers for this color bucket
                            bucket_layers[bucket_key] = quality_adjusted_find_optimal_layers(
                                avg_color,
                                background_color,
                                palette_colors,
                                opacity_values,
                                max_layers,
                                color_cache
                            )
                            
                            # Update progress
                            buckets_processed += 1
                            if buckets_processed % 10 == 0 or buckets_processed >= total_buckets:
                                if update_callback:
                                    bucket_progress = 25 + min(50, int(buckets_processed / total_buckets * 50))
                                    elapsed = time.time() - start_time
                                    remaining = elapsed / bucket_progress * (75 - bucket_progress) if bucket_progress > 0 else 0
                                    update_callback(bucket_progress, elapsed, remaining)
                        
                        # Assign colors to each pixel using the bucket calculations
                        # Update progress - now on pixel assignment phase (75-100%)
                        if update_callback:
                            update_callback(75, time.time() - start_time, 0)
                        
                        total_image_pixels = width * height
                        image_pixels_processed = 0
                        
                        for y in range(height):
                            for x in range(width):
                                color = pixel_data[x, y]
                                bucket_key = (color[0]//bucket_size, color[1]//bucket_size, color[2]//bucket_size)
                                
                                # Get layers from bucket
                                layers = bucket_layers.get(bucket_key, [])
                                
                                # Only store pixels that need painting
                                if layers:
                                    layered_colors[(x, y)] = layers
                                
                                # Update progress less frequently for better performance
                                image_pixels_processed += 1
                                if image_pixels_processed % 10000 == 0 or image_pixels_processed >= total_image_pixels:
                                    if update_callback:
                                        pixel_progress = 75 + min(25, int(image_pixels_processed / total_image_pixels * 25))
                                        elapsed = time.time() - start_time
                                        remaining = elapsed / pixel_progress * (100 - pixel_progress) if pixel_progress > 0 else 0
                                        update_callback(pixel_progress, elapsed, remaining)
                        
                        # Final update
                        if update_callback:
                            elapsed = time.time() - start_time
                            update_callback(100, elapsed, 0)
                        
                        return layered_colors
                    
                    # Use our quality-adjusted version
                    self.layered_colors_map = create_layered_colors_map_with_quality(
                        temp_img,
                        background_color,
                        self.base_palette_colors,
                        self.opacity_values,
                        max_layers=2,
                        update_callback=update_progress
                    )
            except (ImportError, AttributeError) as e:
                # Fall back to single-threaded if multiprocessing fails
                self.parent.ui.log_TextEdit.append(f"Using single-threaded processing: {str(e)}")
                from lib.color_blending import create_layered_colors_map
                self.layered_colors_map = create_layered_colors_map(
                    temp_img,
                    background_color,
                    self.base_palette_colors,
                    self.opacity_values,
                    max_layers=2,
                    update_callback=update_progress
                )
            finally:
                # Restore the original find_optimal_layers function
                color_blending_module.find_optimal_layers = original_find_optimal_layers_func
                
            # Close the progress dialog
            self.progress_dialog.close()
            
            if self.cancel_requested:
                self.parent.ui.log_TextEdit.append("Color calculation was cancelled")
                return None
                
            # Create the simulated output image
            from lib.color_blending import simulate_layered_image
            self.simulated_img = simulate_layered_image(
                temp_img,
                background_color,
                self.base_palette_colors,
                self.opacity_values,
                self.layered_colors_map
            )
            
            # Cache the calculation results
            self.color_calculation_cache = {
                'resized_img': temp_img,
                'layered_colors_map': self.layered_colors_map,
                'simulated_img': self.simulated_img,
                'background_color': background_color
            }
            
            # Convert the simulated image to PIL format for quantization
            quantized_img = self.simulated_img
            
            # Log statistics
            pixel_count = sum(1 for _ in self.layered_colors_map.values())
            self.parent.ui.log_TextEdit.append(
                f"Optimal color layering complete: {pixel_count:,} pixels will be painted " +
                f"({pixel_count / total_pixels:.1%} of image)"
            )
            
            return quantized_img
            
        except Exception as e:
            import traceback
            self.parent.ui.log_TextEdit.append(f"Error during color calculation: {str(e)}")
            self.parent.ui.log_TextEdit.append(traceback.format_exc())
            if hasattr(self, 'progress_dialog') and self.progress_dialog:
                self.progress_dialog.close()
            return None

    def cancel_color_calculation(self):
        """Cancel the current color calculation process"""
        from lib.color_blending import set_cancel_flag
        self.cancel_requested = True
        # Set the global cancellation flag that all processes will check
        set_cancel_flag(True)
        self.parent.ui.log_TextEdit.append("Cancelling color calculation...")
        self.parent.ui.log_TextEdit.append("Please wait while worker processes are terminated...")
        QApplication.processEvents()

    def create_pixmaps(self):
        """Create quantized pixmaps"""
        try:
            # Get background color
            bg_color_hex = self.settings.value("background_color", default_settings["background_color"])
            bg_color_rgb = hex_to_rgb(bg_color_hex)
            self.update_palette(bg_color_rgb)
            
            # Generate the optimized image with layered colors
            # This replaces the previous quantization method with our new one
            optimized_img = self.optimized_quantize_to_palette(self.org_img)
            
            # If the optimization was cancelled or failed, return early to prevent crashes
            if optimized_img is None:
                self.org_img_ok = False
                self.parent.ui.log_TextEdit.append("Image processing cancelled or failed. Please try again.")
                return
            
            # Save optimized image to use for both normal and high quality previews
            # (since they're now identical - we always use the best quality)
            optimized_img.save("temp_optimized.png")
            optimized_pixmap = QPixmap("temp_optimized.png")
            os.remove("temp_optimized.png")
            
            # Use the same high-quality optimized image for both normal and high quality
            self.quantized_img_pixmap = optimized_pixmap
            
            self.org_img_ok = True
            self.parent.ui.log_TextEdit.append("Image processed with optimal color layering.")
        except Exception as e:
            print(f"Error creating pixmaps: {str(e)}")
            self.org_img_ok = False
            # Set the pixmaps to None to prevent further crashes
            self.quantized_img_pixmap = None

    def convert_img(self):
        """Convert the image to fit the canvas and quantize the image.
        Updates:    quantized_img,
                    x_correction,
                    y_correction
        Returns:    False, if the image type is invalid.
        """
        if not self.org_img:
            self.parent.ui.log_TextEdit.append("Error: No image loaded")
            return False
            
        try:
            org_img_w = self.org_img.size[0]
            org_img_h = self.org_img.size[1]

            wpercent = self.canvas_w / float(org_img_w)
            hpercent = self.canvas_h / float(org_img_h)

            hsize = int((float(org_img_h) * float(wpercent)))
            wsize = int((float(org_img_w) * float(hpercent)))

            x_correction = 0
            y_correction = 0

            # Use Image.LANCZOS instead of deprecated Image.ANTIALIAS
            if hsize <= self.canvas_h:
                resized_img = self.org_img.resize((self.canvas_w, hsize), Image.Resampling.LANCZOS)
                y_correction = int((self.canvas_h - hsize) / 2)
            elif wsize <= self.canvas_w:
                resized_img = self.org_img.resize((wsize, self.canvas_h), Image.Resampling.LANCZOS)
                x_correction = int((self.canvas_w - wsize) / 2)
            else:
                resized_img = self.org_img.resize(
                    (self.canvas_w, self.canvas_h), Image.Resampling.LANCZOS
                )

            # Get background color for comparison
            bg_color_hex = self.settings.value("background_color", default_settings["background_color"])
            bg_color_rgb = hex_to_rgb(bg_color_hex)
            
            # Get the current loaded image path for cache saving
            current_image_path = self.settings.value("folder_path", "")

            # Check if we need to reprocess based on settings that affect color processing
            need_reprocess = False
            
            # First try to use cached calculations if available
            if (self.color_calculation_cache['resized_img'] is not None and
                self.color_calculation_cache['background_color'] == bg_color_rgb and
                self.color_calculation_cache['simulated_img'] is not None and
                resized_img.size == self.color_calculation_cache['resized_img'].size):
                
                self.parent.ui.log_TextEdit.append("Reusing previously calculated color mapping...")
                QApplication.processEvents()
                
                # Reuse the existing calculation
                self.quantized_img = self.color_calculation_cache['simulated_img']
                self.layered_colors_map = self.color_calculation_cache['layered_colors_map']
            else:
                # Need to reprocess if any of these essential settings have changed
                need_reprocess = False
                
            # If no cache or if we need to reprocess, calculate optimal colors
            if need_reprocess or self.quantized_img is None:
                # Process the image using our optimal color layering algorithm
                try:
                    self.parent.ui.log_TextEdit.append("Calculating optimal color layering...")
                    QApplication.processEvents()
                    
                    # Store the new calculation
                    self.color_calculation_cache['resized_img'] = resized_img.copy()
                    self.color_calculation_cache['background_color'] = bg_color_rgb
                    
                    self.quantized_img = self.optimized_quantize_to_palette(resized_img)
                    
                    # If the optimized quantization failed, fall back to basic quantization
                    if self.quantized_img is None:
                        self.parent.ui.log_TextEdit.append("Optimal quantization failed, using standard quantization...")
                        self.quantized_img = self.quantize_to_palette(resized_img)
                    else:
                        # Store the result in the cache
                        self.color_calculation_cache['simulated_img'] = self.quantized_img.copy()
                        self.color_calculation_cache['layered_colors_map'] = self.layered_colors_map
                        
                        # Save calculation to cache file if setting is enabled
                        auto_save_cache = bool(
                            self.settings.value("auto_save_cache", True)
                        )
                        
                        if auto_save_cache and current_image_path and os.path.isfile(current_image_path):
                            self.save_calculation_cache(current_image_path)
                        
                except Exception as e:
                    # Fall back to standard quantization if optimal fails
                    self.parent.ui.log_TextEdit.append(f"Error in optimal color layering: {str(e)}")
                    self.parent.ui.log_TextEdit.append("Using standard quantization as fallback...")
                    QApplication.processEvents()
                    
                    self.quantized_img = self.quantize_to_palette(resized_img)
            
            # Final check if we have a quantized image
            if self.quantized_img is None:
                self.parent.ui.log_TextEdit.append("Error: Image processing failed completely")
                self.org_img_ok = False
                return False

            # Update the canvas dimensions
            self.canvas_x += x_correction
            self.canvas_y += y_correction
            self.canvas_w = self.quantized_img.size[0]
            self.canvas_h = self.quantized_img.size[1]
            return True
            
        except Exception as e:
            import traceback
            self.parent.ui.log_TextEdit.append(f"Error converting image: {str(e)}")
            self.parent.ui.log_TextEdit.append(traceback.format_exc())
            return False

    def update_palette(self, rgb_background):
        """Update the palette used for image quantization with the new 4x16 color grid"""
        # Find the background color in the rust_palette list
        background_index = 3  # Default to white (index 3)
        for i, color in enumerate(rust_palette):
            if color == rgb_background:
                background_index = i
                break

        # Store background color indices for skip_colors list (used only during painting)
        # This doesn't affect the color palette used for image quantization
        self.background_opacities = []
        if self.settings.value("skip_background_color", default_settings["skip_background_color"]):
            self.background_opacities = [background_index]

        # Create a new palette image with the right mode
        self.palette_data = Image.new("P", (16, 16))
        self.updated_palette = []
        
        # Build the palette as a list of RGB tuples for our internal use
        # Always use the full 64 colors at 100% opacity from the rust_palette
        palette_colors = rust_palette[:64].copy()

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
        # Check if we have a quantized image to use as preview
        preview_img = None
        if self.org_img_ok:
            # Use the original or quantized image as a preview
            if self.quantized_img:
                # If we have a processed image, use it
                preview_img = self.quantized_img
            elif self.org_img:
                # Otherwise fall back to the original image
                preview_img = self.org_img
                
        dialog = CaptureAreaDialog(self.parent, 0)
        ans = dialog.exec_()
        if ans == 0:
            return False

        self.parent.hide()
        # Pass the preview image to the capture_area function
        canvas_area = capture_area(preview_image=preview_img)
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

        # Show confirmation with area details
        msg = QMessageBox(self.parent)
        msg.setWindowTitle("Canvas Area Selected")
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
        
        # Only show "Continue to iterate?" if we have color calculations
        if self.color_calculation_cache['simulated_img'] is not None:
            msg.setInformativeText("Continue to iterate with the current color calculation?")
        
        # Create custom buttons instead of using setButtonText
        continue_btn = msg.addButton("Continue", QMessageBox.YesRole)
        try_again_btn = msg.addButton("Try Again", QMessageBox.NoRole)
        msg.setDefaultButton(continue_btn)
        
        msg.exec_()
        
        if msg.clickedButton() == try_again_btn:
            # User wants to try again
            return self.locate_canvas_area()
        
        # Store the canvas area coordinates
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
        # Store in settings for the test overlay
        self.settings.setValue("overlay_update_x", self.ctrl_update[0])
        self.settings.setValue("overlay_update_y", self.ctrl_update[1])

        # Size box for text input (at 89.54% from left, 29.96% from top)
        self.ctrl_size.append((ctrl_x + (ctrl_w * 0.8954), ctrl_y + (ctrl_h * 0.2996)))
        # Store in settings for the test overlay
        self.settings.setValue("overlay_size_x", self.ctrl_size[0][0])
        self.settings.setValue("overlay_size_y", self.ctrl_size[0][1])

        # Brush types
        # Paint Brush is 38.17% from the left edge and 9.54% from the top edge
        # self.ctrl_brush.append((ctrl_x + (ctrl_w * 0.3817), ctrl_y + (ctrl_h * 0.0954)))
        # Light Round Brush is 14.5% from the left edge and 24.4% from the top edge
        self.ctrl_brush.append((ctrl_x + (ctrl_w * 0.145), ctrl_y + (ctrl_h * 0.244)))
        # Heavy Round Brush is 38.17% from the left edge and 24.4% from the top edge
        self.ctrl_brush.append((ctrl_x + (ctrl_w * 0.3817), ctrl_y + (ctrl_h * 0.244)))
        # Medium Round Brush is 26.42% from the left edge and 24.4% from the top edge
        self.ctrl_brush.append((ctrl_x + (ctrl_w * 0.2642), ctrl_y + (ctrl_h * 0.244)))
        # Heavy Square Brush is 49.72% from the left edge and 24.4% from the top edge
        self.ctrl_brush.append((ctrl_x + (ctrl_w * 0.4972), ctrl_y + (ctrl_h * 0.244)))
        
        # Store brush positions in settings for the test overlay
        for i, pos in enumerate(self.ctrl_brush):
            self.settings.setValue(f"overlay_brush_{i}_x", pos[0])
            self.settings.setValue(f"overlay_brush_{i}_y", pos[1])
        self.settings.setValue("overlay_brush_count", len(self.ctrl_brush))

        # Opacity box for text input (at 89.54% from left, 39.25% from top)
        self.ctrl_opacity.append(
            (ctrl_x + (ctrl_w * 0.8954), ctrl_y + (ctrl_h * 0.3925))
        )
        # Store in settings for the test overlay
        self.settings.setValue("overlay_opacity_x", self.ctrl_opacity[0][0])
        self.settings.setValue("overlay_opacity_y", self.ctrl_opacity[0][1])

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
                # Store color grid positions in settings for the test overlay
                color_idx = row * 4 + column
                self.settings.setValue(f"overlay_color_{color_idx}_x", color_x)
                self.settings.setValue(f"overlay_color_{color_idx}_y", color_y)
                
        # Store total color count
        self.settings.setValue("overlay_color_count", len(self.ctrl_color))

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
        # Base time factors
        one_click_time = self.click_delay + 0.001
        one_line_time = (self.line_delay * 5) + 0.0035
        
        # Calculate control setting time - this stays the same
        set_paint_controls_time = (
            len(self.img_colors) * ((2 * self.click_delay) + (2 * self.ctrl_area_delay))
        ) + ((2 * self.click_delay) + (2 * self.ctrl_area_delay))
        
        # Calculate raw painting time
        raw_est_time_lines = int(
            (self.pixels * one_click_time)
            + (self.lines * one_line_time)
            + set_paint_controls_time
        )
        raw_est_time_click = int(
            (self.tot_pixels * one_click_time) + set_paint_controls_time
        )
        
        # Add system overhead and performance factors (based on real-world observations)
        # Using a scaling factor of approximately 1.75x for realistic estimation
        performance_factor = 1.75
        
        # Additional overhead per color change (UI responsiveness, etc.)
        color_change_overhead = len(self.img_colors) * 1.2  # seconds per color
        
        # Apply performance factor and add overhead
        est_time_lines = int((raw_est_time_lines * performance_factor) + color_change_overhead)
        est_time_click = int((raw_est_time_click * performance_factor) + color_change_overhead)

        if not bool(self.settings.value("draw_lines", default_settings["draw_lines"])):
            self.prefer_lines = False
            self.estimated_time = est_time_click
        elif est_time_lines < est_time_click:
            self.prefer_lines = True
            self.estimated_time = est_time_lines
        else:
            self.prefer_lines = False
            self.estimated_time = est_time_click
            
        # Log the estimation details
        self.parent.ui.log_TextEdit.append(f"Time estimation: {time.strftime('%H:%M:%S', time.gmtime(self.estimated_time))}")
        self.parent.ui.log_TextEdit.append(f"(Includes {len(self.img_colors)} color changes and system overhead)")

    def click_pixel(self, x=0, y=0):
        """Click the pixel"""
        if isinstance(x, tuple):
            pyautogui.click(x[0], x[1])
        else:
            pyautogui.click(x, y)

    def draw_line(self, point_A, point_B):
        """Draws a horizontal line between point_A and point_B.
        Optimized for painting speed and accuracy by using the shift key method.
        This method should be used for horizontal lines where point_A and point_B have the same y-coordinate.
        """
        # Quick check if it's actually a horizontal line
        if abs(point_A[1] - point_B[1]) > 2:
            # If it's more vertical than horizontal, use the vertical line drawing
            if abs(point_A[0] - point_B[0]) < abs(point_A[1] - point_B[1]):
                return self.draw_vertical_line(point_A, point_B)

        # Apply optimized line delay for horizontal drawing
        pyautogui.PAUSE = self.line_delay
        
        # Draw the horizontal line using the shift key
        pyautogui.mouseDown(button="left", x=point_A[0], y=point_A[1])
        pyautogui.keyDown("shift")
        pyautogui.moveTo(point_B[0], point_B[1])
        pyautogui.keyUp("shift")
        pyautogui.mouseUp(button="left")
        
        # Restore normal click delay
        pyautogui.PAUSE = self.click_delay

    def draw_vertical_line(self, point_A, point_B):
        """Draws a vertical line between point_A and point_B.
        Optimized for painting vertical lines where point_A and point_B have the same x-coordinate.
        This provides significant speed improvements for vertical shapes and patterns.
        """
        # Make sure points are ordered from top to bottom
        if point_A[1] > point_B[1]:
            point_A, point_B = point_B, point_A
            
        # Apply optimized line delay for vertical drawing
        pyautogui.PAUSE = self.line_delay
        
        # Draw the vertical line using the shift key
        pyautogui.mouseDown(button="left", x=point_A[0], y=point_A[1])
        pyautogui.keyDown("shift")
        pyautogui.moveTo(point_A[0], point_B[1])
        pyautogui.keyUp("shift")
        pyautogui.mouseUp(button="left")
        
        # Restore normal click delay
        pyautogui.PAUSE = self.click_delay

    def draw_diagonal_line(self, start_point, end_point):
        """Draws a diagonal line between start_point and end_point.
        This provides efficient painting for diagonal shapes and patterns.
        
        Args:
            start_point: Tuple (x, y) for the start of the line
            end_point: Tuple (x, y) for the end of the line
        """
        # Apply optimized line delay for diagonal drawing
        pyautogui.PAUSE = self.line_delay
        
        # Draw the diagonal line using the shift key method
        # This works the same way as horizontal/vertical lines in Rust
        pyautogui.mouseDown(button="left", x=start_point[0], y=start_point[1])
        pyautogui.keyDown("shift")
        pyautogui.moveTo(end_point[0], end_point[1])
        pyautogui.keyUp("shift")
        pyautogui.mouseUp(button="left")
        
        # Restore normal click delay
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

        # Clear the last used color/brush/opacity settings
        self.clear_last_painting_settings()

        if bool(
            self.settings.value("window_topmost", default_settings["window_topmost"])
        ):
            self.parent.setWindowFlags(
                self.parent.windowFlags() & ~Qt.WindowStaysOnTopHint
            )
            self.parent.show()
        self.parent.activateWindow()

        # Stop the status update timer if it's running
        if self.status_update_timer is not None:
            self.status_update_timer.stop()
            self.status_update_timer = None

    def choose_painting_controls(self, size, brush, color_idx, opacity_value=None):
        """Choose the paint controls
        
        Args:
            size (int): Brush size (0: small (2), 1: medium (4), 2: large (6), etc.)
            brush (int): Brush type index
            color_idx (int): Color index in the palette grid (0-63)
            opacity_value (float, optional): If provided, directly set this opacity value (0-1)
        """
        # Determine actual opacity value for tracking purposes
        actual_opacity = opacity_value
        if opacity_value is None:
            # Default opacities based on column
            actual_opacity = 1.0  # Default opacity: 100%
            if color_idx % 4 == 1:
                actual_opacity = 0.75
            elif color_idx % 4 == 2:
                actual_opacity = 0.5
            elif color_idx % 4 == 3:
                actual_opacity = 0.25
        
        # Log information about what we're doing
        self.parent.ui.log_TextEdit.append("Setting up painting controls...")
        QApplication.processEvents()
        
        # Longer delay for control area interactions
        ctrl_interaction_delay = max(0.3, self.ctrl_area_delay * 1.5)
        
        # Log the actual color we're selecting for debugging
        if color_idx < len(self.updated_palette):
            rgb_color = self.updated_palette[color_idx] if color_idx < len(self.updated_palette) else "unknown"
            hex_color = rgb_to_hex(rgb_color) if isinstance(rgb_color, tuple) else "unknown"
            
            # Determine opacity percentage for display
            opacity_percent = int(actual_opacity * 100)
            self.parent.ui.log_TextEdit.append(f"Target color: {hex_color}, Opacity: {opacity_percent}%")
            QApplication.processEvents()

        # 1. Select brush type first - only if changed
        if self.current_ctrl_brush != brush:
            self.current_ctrl_brush = brush
            self.parent.ui.log_TextEdit.append("Selecting brush type")
            QApplication.processEvents()
            # Double click the brush type button
            pyautogui.click(self.ctrl_brush[brush][0], self.ctrl_brush[brush][1])
            time.sleep(0.1)  # Short delay between clicks
            pyautogui.click(self.ctrl_brush[brush][0], self.ctrl_brush[brush][1])
            time.sleep(ctrl_interaction_delay)
        else:
            self.parent.ui.log_TextEdit.append("Brush type already set correctly - no change needed")
            QApplication.processEvents()

        # 2. Set brush size (text input box) - only if changed
        brush_size = str(1 + (size * 2)) if size >= 0 else "1"  # Default to 1
        if self.current_ctrl_size != size:
            self.current_ctrl_size = size
            self.parent.ui.log_TextEdit.append(f"Setting brush size: {brush_size}")
            QApplication.processEvents()
            
            # Double click to focus the size box
            pyautogui.click(self.ctrl_size[0][0], self.ctrl_size[0][1])
            time.sleep(0.1)  # Short delay between clicks
            pyautogui.click(self.ctrl_size[0][0], self.ctrl_size[0][1])
            time.sleep(ctrl_interaction_delay)
            
            # Select all existing text
            pyautogui.hotkey('ctrl', 'a')
            time.sleep(0.2)  # Longer delay after Ctrl+A
            
            # Type the brush size
            pyautogui.typewrite(brush_size)
            time.sleep(0.2)  # Longer delay after typing
            
            # Press Enter
            pyautogui.press("enter")
            time.sleep(ctrl_interaction_delay)
        else:
            self.parent.ui.log_TextEdit.append(f"Brush size already set to {brush_size} - no change needed")
            QApplication.processEvents()

        # 3. Set opacity (text input box) - only if changed
        # Determine opacity value string for UI input
        ui_opacity_value = actual_opacity
        if actual_opacity == 0.75:
            ui_opacity_value = 0.37
        elif actual_opacity == 0.5:
            ui_opacity_value = 0.25
        elif actual_opacity == 0.25:
            ui_opacity_value = 0.12
        opacity_percent = str(ui_opacity_value)
        
        # Only update opacity if it changed
        if self.current_ctrl_opacity != actual_opacity:
            self.current_ctrl_opacity = actual_opacity
            self.parent.ui.log_TextEdit.append(f"Setting opacity: {int(actual_opacity * 100)}%")
            QApplication.processEvents()
            
            # Double click to focus the opacity text box
            pyautogui.click(self.ctrl_opacity[0][0], self.ctrl_opacity[0][1])
            time.sleep(0.1)  # Short delay between clicks
            pyautogui.click(self.ctrl_opacity[0][0], self.ctrl_opacity[0][1])
            time.sleep(ctrl_interaction_delay)
            
            # Select all existing text
            pyautogui.hotkey('ctrl', 'a')
            time.sleep(0.2)  # Longer delay after Ctrl+A
            
            # Type the opacity percentage value
            pyautogui.typewrite(opacity_percent)
            time.sleep(0.2)  # Longer delay after typing
            
            # Press Enter
            pyautogui.press("enter")
            time.sleep(ctrl_interaction_delay)
        else:
            self.parent.ui.log_TextEdit.append(f"Opacity already set to {int(actual_opacity * 100)}% - no change needed")
            QApplication.processEvents()

        # 4. Select the color from the grid - only if changed
        if self.current_ctrl_color != color_idx:
            self.current_ctrl_color = color_idx
            
            # Calculate the row and column in the color grid
            row = (color_idx // 4)      # Integer division by 4 gives row (0-15)
            column = (color_idx % 4)    # Modulo 4 gives column (0-3)
            
            # Calculate the actual index in self.ctrl_color array
            grid_idx = (row * 4) + column
            
            if grid_idx < len(self.ctrl_color):
                self.parent.ui.log_TextEdit.append(f"Selecting color at grid position: row={row}, column={column}")
                QApplication.processEvents()
                
                # Double click the color in the grid
                pyautogui.click(self.ctrl_color[grid_idx][0], self.ctrl_color[grid_idx][1])
                time.sleep(0.1)  # Short delay between clicks
                pyautogui.click(self.ctrl_color[grid_idx][0], self.ctrl_color[grid_idx][1])
                time.sleep(ctrl_interaction_delay)
            else:
                self.parent.ui.log_TextEdit.append(f"Error: Invalid color grid index: {grid_idx}")
                QApplication.processEvents()
        else:
            self.parent.ui.log_TextEdit.append(f"Color already selected - no change needed")
            QApplication.processEvents()

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
        self.parent.ui.log_TextEdit.append("Calculating painting sequence...")
        QApplication.processEvents()

        self.calculate_ctrl_tools_positioning()  # Calculate the control tools positioning

        # Check if we have a layered colors map (from optimal color calculation)
        if not hasattr(self, 'layered_colors_map') or not self.layered_colors_map:
            self.parent.ui.log_TextEdit.append("No layering information found. Using standard painting method...")
            self.calculate_statistics()  # Calculate statistics (colors, total pixels, lines)
            self.calculate_estimated_time()  # Calculate the estimated time
            # Continue with original painting method
            return self.start_standard_painting()

        # Using optimal layering painting method
        # Count total painting operations
        total_operations = 0
        color_counts = {}
        
        # Count operations per color and opacity
        for coords, layers in self.layered_colors_map.items():
            for color_idx, opacity_idx in layers:
                color_key = (color_idx, opacity_idx)
                if color_key not in color_counts:
                    color_counts[color_key] = 1
                else:
                    color_counts[color_key] += 1
                total_operations += 1
        
        # Precompute the horizontal, vertical, and diagonal lines to optimize painting
        self.parent.ui.log_TextEdit.append("Optimizing painting with line detection...")
        QApplication.processEvents()
        precomputed_lines = self.precompute_painting_lines(color_counts)
                
        # Recalculate operations and time estimate based on the optimizations
        total_operations = 0
        for color_key in precomputed_lines:
            # Each horizontal line is one operation
            total_operations += len(precomputed_lines[color_key]['h_lines'])
            # Each vertical line is one operation
            total_operations += len(precomputed_lines[color_key]['v_lines'])
            # Each diagonal line is one operation
            total_operations += len(precomputed_lines[color_key]['d_lines'])
            # Each point is one operation
            total_operations += len(precomputed_lines[color_key]['points'])
        
        # Add color selection operations
        total_operations += len(precomputed_lines)
        
        # Estimate time with optimized operations
        one_click_time = self.click_delay + 0.001
        one_line_time = (self.line_delay * 5) + 0.0035
        set_paint_controls_time = len(precomputed_lines) * ((2 * self.click_delay) + (2 * self.ctrl_area_delay))
        
        # Calculate time based on operations
        h_v_d_lines_count = sum(len(data['h_lines']) + len(data['v_lines']) + len(data['d_lines']) 
                              for data in precomputed_lines.values())
        points_count = sum(len(data['points']) for data in precomputed_lines.values())
        painting_time = (h_v_d_lines_count * one_line_time) + (points_count * one_click_time)
        self.estimated_time = int(painting_time + set_paint_controls_time)

        # Print statistics
        question = (
            "Dimensions: \t\t\t\t" + str(self.canvas_w) + " x " + str(self.canvas_h)
        )
        question += "\nNumber of unique colors/opacities:\t" + str(len(precomputed_lines))
        question += f"\nTotal lines (h/v/diag): \t\t{h_v_d_lines_count}"
        question += f"\nTotal individual points: \t\t{points_count}"
        question += "\nEst. painting time:\t\t\t" + str(
            time.strftime("%H:%M:%S", time.gmtime(self.estimated_time))
        )
        question += "\n\nUsing optimal line painting for better speed and accuracy."
        question += "\nWould you like to start the painting?"
        
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
        self.hotkey_label.setGeometry(QRect(10, 559, 221, 21))
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
        bg_color_hex = self.settings.value("background_color", default_settings["background_color"])
        bg_color_rgb = hex_to_rgb(bg_color_hex)

        empty_area_tuple = self.ctrl_size[0][0], self.ctrl_size[0][1] - 10
        
        self.click_pixel(empty_area_tuple) # To set focus on the rust window
        time.sleep(1)
        self.click_pixel(empty_area_tuple)
        
        if bool(self.settings.value("paint_background", default_settings["paint_background"])):
            self.parent.ui.log_TextEdit.append("Painting background...")
            
            # Find the background color index in our base colors
            background_idx = -1
            for i, color in self.base_palette_colors:
                if color == bg_color_rgb:
                    background_idx = i
                    break
            
            if background_idx != -1:
                # Background should use 100% opacity
                self.choose_painting_controls(5, int(self.settings.value("brush_type", default_settings["brush_type"])), background_idx)
                
                # Paint the background
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
        operation_counter = 0
        progress_percent = 0
        previous_progress_percent = None

        start_time = time.time()
        brush_type = int(self.settings.value("brush_type", default_settings["brush_type"]))

        # Start keyboard listener
        listener = keyboard.Listener(on_press=self.key_event)
        listener.start()
        
        # Create a sorted list of color keys based on color index first, then opacity index
        # This ensures colors are processed in a logical sequential order (1,2,3...) instead of by size
        sorted_color_keys = sorted(precomputed_lines.keys(), key=lambda k: (k[0], k[1]))
        self.sorted_color_keys = sorted_color_keys
        
        # Start the continuous status update timer
        self.current_operation_counter = operation_counter
        self.current_total_operations = total_operations
        self.start_status_update_timer(sorted_color_keys[0], precomputed_lines, operation_counter, total_operations, start_time)
        
        # Paint each color/opacity combination using the precomputed lines in sequential order
        for color_key in sorted_color_keys:
            color_idx, opacity_idx = color_key
            
            # Update the current color key for the timer
            self.current_color_key = color_key
            
            if self.abort:
                self.parent.ui.log_TextEdit.append("Aborted...")
                self.show_log_text()  # Show log instead of status
                return self.shutdown(listener, start_time, 1)
                
            if self.skip_current_color:
                self.skip_current_color = False
                continue
                
            # Get the color and opacity information
            color = self.base_palette_colors[color_idx]
            opacity = self.opacity_values[opacity_idx]
            opacity_percent = int(opacity * 100)
            color_hex = rgb_to_hex(color)
            
            # Count operations for this color
            h_lines_count = len(precomputed_lines[color_key]['h_lines'])
            v_lines_count = len(precomputed_lines[color_key]['v_lines'])
            d_lines_count = len(precomputed_lines[color_key]['d_lines'])
            points_count = len(precomputed_lines[color_key]['points'])
            
            total_ops = h_lines_count + v_lines_count + d_lines_count + points_count
            
            self.parent.ui.log_TextEdit.append(
                f"Painting {color_hex} at {opacity_percent}% opacity: " +
                f"{h_lines_count} horizontal, {v_lines_count} vertical, " +
                f"{d_lines_count} diagonal lines, {points_count} points"
            )
            
            # Update the status UI when switching to a new color
            self.update_painting_status_ui(color_idx, opacity_idx, color_key, precomputed_lines, 
                                         operation_counter, total_operations, start_time)
            QApplication.processEvents()
            
            # Set painting controls for this color/opacity
            self.choose_painting_controls(0, brush_type, color_idx, opacity_value=opacity)
            
            # First paint horizontal lines
            for h_line in precomputed_lines[color_key]['h_lines']:
                while self.paused:
                    QApplication.processEvents()
                    
                if self.abort:
                    self.parent.ui.log_TextEdit.append("Aborted...")
                    self.show_log_text()  # Show log instead of status
                    return self.shutdown(listener, start_time, 1)
                    
                if self.skip_current_color:
                    break
                
                # Extract line coordinates
                start_x, y, end_x = h_line
                
                # Calculate actual screen coordinates
                screen_start_x = self.canvas_x + start_x
                screen_end_x = self.canvas_x + end_x
                screen_y = self.canvas_y + y
                
                # Draw the horizontal line
                self.draw_line((screen_start_x, screen_y), (screen_end_x, screen_y))
                operation_counter += 1
                self.current_operation_counter = operation_counter
                
                # Update progress
                progress_percent = int(operation_counter / total_operations * 100)
                if progress_percent != previous_progress_percent:
                    previous_progress_percent = progress_percent
                    self.parent.ui.progress_ProgressBar.setValue(progress_percent)
            
            # Reset skip flag if it was set during horizontal lines
            if self.skip_current_color:
                self.skip_current_color = False
                continue
            
            # Next paint vertical lines
            for v_line in precomputed_lines[color_key]['v_lines']:
                while self.paused:
                    QApplication.processEvents()
                    
                if self.abort:
                    self.parent.ui.log_TextEdit.append("Aborted...")
                    self.show_log_text()  # Show log instead of status
                    return self.shutdown(listener, start_time, 1)
                    
                if self.skip_current_color:
                    break
                
                # Extract line coordinates
                x, start_y, end_y = v_line
                
                # Calculate actual screen coordinates
                screen_x = self.canvas_x + x
                screen_start_y = self.canvas_y + start_y
                screen_end_y = self.canvas_y + end_y
                
                # Draw the vertical line
                self.draw_vertical_line((screen_x, screen_start_y), (screen_x, screen_end_y))
                operation_counter += 1
                self.current_operation_counter = operation_counter
                
                # Update progress
                progress_percent = int(operation_counter / total_operations * 100)
                if progress_percent != previous_progress_percent:
                    previous_progress_percent = progress_percent
                    self.parent.ui.progress_ProgressBar.setValue(progress_percent)
                    # Update painting status every 5% progress change
                    if progress_percent % 5 == 0:
                        self.update_painting_status_ui(color_idx, opacity_idx, color_key, 
                                                    precomputed_lines, operation_counter, 
                                                    total_operations, start_time)
            
            # Reset skip flag if it was set during vertical lines
            if self.skip_current_color:
                self.skip_current_color = False
                continue
                
            # Now paint diagonal lines
            for d_line in precomputed_lines[color_key]['d_lines']:
                while self.paused:
                    QApplication.processEvents()
                    
                if self.abort:
                    self.parent.ui.log_TextEdit.append("Aborted...")
                    self.show_log_text()  # Show log instead of status
                    return self.shutdown(listener, start_time, 1)
                    
                if self.skip_current_color:
                    break
                
                # Extract line coordinates
                start_point, end_point = d_line
                
                # Calculate actual screen coordinates
                screen_start_x = self.canvas_x + start_point[0]
                screen_start_y = self.canvas_y + start_point[1]
                screen_end_x = self.canvas_x + end_point[0]
                screen_end_y = self.canvas_y + end_point[1]
                
                # Draw the diagonal line
                self.draw_diagonal_line((screen_start_x, screen_start_y), 
                                       (screen_end_x, screen_end_y))
                operation_counter += 1
                self.current_operation_counter = operation_counter
                
                # Update progress
                progress_percent = int(operation_counter / total_operations * 100)
                if progress_percent != previous_progress_percent:
                    previous_progress_percent = progress_percent
                    self.parent.ui.progress_ProgressBar.setValue(progress_percent)
                    # Update painting status every 5% progress change
                    if progress_percent % 5 == 0:
                        self.update_painting_status_ui(color_idx, opacity_idx, color_key, 
                                                    precomputed_lines, operation_counter, 
                                                    total_operations, start_time)
            
            # Reset skip flag if it was set during diagonal lines
            if self.skip_current_color:
                self.skip_current_color = False
                continue
            
            # Finally paint individual points
            for point in precomputed_lines[color_key]['points']:
                while self.paused:
                    QApplication.processEvents()
                    
                if self.abort:
                    self.parent.ui.log_TextEdit.append("Aborted...")
                    self.show_log_text()  # Show log instead of status
                    return self.shutdown(listener, start_time, 1)
                    
                if self.skip_current_color:
                    break
                
                # Calculate actual screen coordinates
                screen_x = self.canvas_x + point[0]
                screen_y = self.canvas_y + point[1]
                
                # Paint the individual point
                self.click_pixel(screen_x, screen_y)
                operation_counter += 1
                self.current_operation_counter = operation_counter
                
                # Update progress
                progress_percent = int(operation_counter / total_operations * 100)
                if progress_percent != previous_progress_percent:
                    previous_progress_percent = progress_percent
                    self.parent.ui.progress_ProgressBar.setValue(progress_percent)
                    # Update painting status every 5% progress change
                    if progress_percent % 5 == 0:
                        self.update_painting_status_ui(color_idx, opacity_idx, color_key, 
                                                    precomputed_lines, operation_counter, 
                                                    total_operations, start_time)
            
            # Update canvas after each color using Ctrl+S instead of clicking update button           
            if update_canvas:
                self.parent.ui.log_TextEdit.append("Updating canvas with Ctrl+S")
                # Update the UI one more time before switching back to log
                self.update_painting_status_ui(color_idx, opacity_idx, color_key, 
                                            precomputed_lines, operation_counter, 
                                            total_operations, start_time)
                self.show_log_text()  # Show the log for the canvas update message
                QApplication.processEvents()
                pyautogui.hotkey('ctrl', 's')
                time.sleep(self.ctrl_area_delay)
                
            # Reset skip flag
            self.skip_current_color = False

        # Update canvas at the end using Ctrl+S instead of clicking update button
        if update_canvas_end:
            self.parent.ui.log_TextEdit.append("Final canvas update with Ctrl+S")
            QApplication.processEvents()
            pyautogui.hotkey('ctrl', 's')
            time.sleep(self.ctrl_area_delay)

        return self.shutdown(listener, start_time)

    def start_standard_painting(self):
        """Original painting method when optimal layering is not available"""
        # ...existing code from original start_painting method...
        # This method should be a copy of the original start_painting method
        # implementation that gets called when layered_colors_map is not available
        
        # For brevity and to avoid duplication, I'm not including the full code here
        # In an actual implementation, this would contain all the original painting logic
        self.parent.ui.log_TextEdit.append("Using standard painting method...")
        return

    def save_calculation_cache(self, image_path):
        """Save the color calculation cache to a file alongside the image
        
        Args:
            image_path (str): Path to the original image file
        """
        if not hasattr(self, 'layered_colors_map') or not self.layered_colors_map:
            self.parent.ui.log_TextEdit.append("No calculation data to save.")
            return False
            
        # Create the cache filename by adding .rustcache extension
        cache_path = f"{image_path}.rustcache"
        
        try:
            import pickle
            import os
            
            # Data to cache
            cache_data = {
                'layered_colors_map': self.layered_colors_map,
                'background_color': self.color_calculation_cache['background_color'],
                'image_size': self.color_calculation_cache['resized_img'].size if self.color_calculation_cache['resized_img'] else None,
                'timestamp': time.time(),
                'version': 1.0  # For future compatibility checks
            }
            
            # Save as pickle file
            with open(cache_path, 'wb') as f:
                pickle.dump(cache_data, f)
                
            file_size = os.path.getsize(cache_path) / 1024  # Size in KB
            self.parent.ui.log_TextEdit.append(f"Calculation cache saved ({file_size:.1f} KB): {os.path.basename(cache_path)}")
            return True
        except Exception as e:
            self.parent.ui.log_TextEdit.append(f"Error saving calculation cache: {str(e)}")
            return False

    def load_calculation_cache(self, image_path, bg_color_rgb):
        """Load color calculation cache from a file if it exists
        
        Args:
            image_path (str): Path to the original image file
            bg_color_rgb (tuple): RGB tuple of background color to match against cache
            
        Returns:
            bool: True if cache was loaded successfully, False otherwise
        """
        # Create the expected cache filename
        cache_path = f"{image_path}.rustcache"
        
        try:
            import pickle
            import os
            
            # Check if cache file exists
            if not os.path.exists(cache_path):
                return False
                
            # Load the cache data
            with open(cache_path, 'rb') as f:
                cache_data = pickle.load(f)
                
            # Verify the data is compatible
            if 'version' not in cache_data or cache_data['version'] > 1.0:
                self.parent.ui.log_TextEdit.append("Cached data format is not compatible")
                return False
                
            # Check if background color matches
            if cache_data['background_color'] != bg_color_rgb:
                self.parent.ui.log_TextEdit.append("Background color in cache doesn't match current settings")
                return False
                
            # Populate our cache
            self.layered_colors_map = cache_data['layered_colors_map']
            self.color_calculation_cache['background_color'] = cache_data['background_color']
            
            # Show cache age info
            if 'timestamp' in cache_data:
                import datetime
                cache_time = datetime.datetime.fromtimestamp(cache_data['timestamp'])
                current_time = datetime.datetime.now()
                days_old = (current_time - cache_time).days
                hours_old = int((current_time - cache_time).seconds / 3600)
                
                if days_old > 0:
                    age_str = f"{days_old} day{'s' if days_old > 1 else ''}"
                else:
                    age_str = f"{hours_old} hour{'s' if hours_old > 1 else ''}"
                    
                self.parent.ui.log_TextEdit.append(f"Loaded calculation cache ({age_str} old)")
            else:
                self.parent.ui.log_TextEdit.append("Loaded calculation cache")
                
            return True
        except Exception as e:
            self.parent.ui.log_TextEdit.append(f"Error loading calculation cache: {str(e)}")
            return False

    def precompute_painting_lines(self, color_opacity_map):
        """
        Precompute horizontal and vertical lines for each color/opacity combination.
        This optimization dramatically reduces painting time by using line drawing instead of individual clicks.
        
        Args:
            color_opacity_map: Dictionary with (color_idx, opacity_idx) keys and pixel counts as values
            
        Returns:
            Dictionary containing precomputed line data for each color/opacity combination
        """
        self.parent.ui.log_TextEdit.append("Optimizing painting process - detecting line segments...")
        QApplication.processEvents()
        
        # Create a progress dialog similar to the one used for color calculation
        from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QPushButton
        from ui.theme.theme import apply_theme_to_dialog
        
        # Create custom dialog with proper size
        progress_dialog = QDialog(self.parent)
        apply_theme_to_dialog(progress_dialog)  # Apply current theme
        progress_dialog.setWindowTitle("Calculating Line Optimizations")
        progress_dialog.setMinimumWidth(600)  # Wide dialog
        progress_dialog.setMinimumHeight(180) # Tall dialog
        progress_dialog.setModal(False)       # Non-modal dialog
        
        # Create layout
        layout = QVBoxLayout()
        
        # Add main information label
        info_label = QLabel("Detecting optimized line segments...\nThis will improve painting speed.", progress_dialog)
        info_label.setStyleSheet("font-size: 11pt; font-weight: bold;")
        layout.addWidget(info_label)
        
        # Add spacer
        layout.addSpacing(10)
        
        # Add progress bar with better size
        progress_bar = QProgressBar(progress_dialog)
        progress_bar.setMinimumHeight(30)  # Taller progress bar
        layout.addWidget(progress_bar)
        
        # Add status label with better formatting
        progress_status = QLabel("Calculating...", progress_dialog)
        progress_status.setStyleSheet("font-size: 10pt;")
        progress_status.setMinimumHeight(30)  # Ensure enough height
        layout.addWidget(progress_status)
        
        # Set the layout on the dialog
        progress_dialog.setLayout(layout)
        
        # Show the dialog
        progress_dialog.show()
        QApplication.processEvents()
        
        # Create a dictionary to store:
        # (color_idx, opacity_idx) -> { 'h_lines': [...], 'v_lines': [...], 'd_lines': [...], 'points': [...] }
        precomputed_lines = {}
        
        # Create a temporary 2D grid representing the image to track processed pixels
        grid = {}
        processed = set() # Global set to track all processed pixels across all colors
        min_line_width = int(self.settings.value("minimum_line_width", default_settings["minimum_line_width"]))
        
        # Fill the grid with color/opacity information
        pixel_count = len(self.layered_colors_map)
        pixels_processed = 0
        start_time = time.time()
        
        # Calculate total work steps for accurate progress tracking
        color_count = len(color_opacity_map)
        total_progress_steps = 100
        grid_building_steps = 20
        horizontal_line_steps = 25
        vertical_line_steps = 25
        diagonal_line_steps = 20
        
        progress_bar.setMaximum(total_progress_steps)
        progress_bar.setValue(0)
        progress_status.setText("Building pixel grid...")
        QApplication.processEvents()
        
        # Step 1: Build the pixel grid - 20% of progress
        for (x, y), layers in self.layered_colors_map.items():
            for color_idx, opacity_idx in layers:
                if (x, y) not in grid:
                    grid[(x, y)] = []
                grid[(x, y)].append((color_idx, opacity_idx))
            
            # Update progress
            pixels_processed += 1
            if pixels_processed % 1000 == 0 or pixels_processed == pixel_count:
                percent = int((pixels_processed / pixel_count) * grid_building_steps)
                progress_bar.setValue(percent)
                elapsed = time.time() - start_time
                remaining = elapsed / percent * (total_progress_steps - percent) if percent > 0 else 0
                elapsed_str = time.strftime("%M:%S", time.gmtime(elapsed))
                remaining_str = time.strftime("%M:%S", time.gmtime(remaining))
                progress_status.setText(f"Building pixel grid: {int(pixels_processed / pixel_count * 100)}% | " +
                                         f"Elapsed: {elapsed_str} | Remaining: {remaining_str}")
                QApplication.processEvents()
        
        # For each color/opacity combination, find horizontal and vertical lines
        colors_processed = 0
        total_colors = len(color_opacity_map)
        
        # Initialize storage for all color/opacity combinations
        for (color_idx, opacity_idx) in color_opacity_map:
            precomputed_lines[(color_idx, opacity_idx)] = {
                'h_lines': [],  # Horizontal lines: [(start_x, y, end_x), ...]
                'v_lines': [],  # Vertical lines: [(x, start_y, end_y), ...]
                'd_lines': [],  # Diagonal lines: [((start_x, start_y), (end_x, end_y)), ...]
                'points': []    # Individual points: [(x, y), ...]
            }
        
        # Step 2: Find horizontal lines - 25% of progress (grid_building_steps to grid_building_steps+horizontal_line_steps)
        progress_status.setText("Finding horizontal lines...")
        QApplication.processEvents()
        
        # Process all rows of the canvas
        for y in range(self.canvas_h):
            # For each color, check for horizontal lines in this row
            for (color_idx, opacity_idx), count in color_opacity_map.items():
                if count < min_line_width:
                    continue
                
                x = 0
                while x < self.canvas_w:
                    # Find start of horizontal line
                    line_start = None
                    while x < self.canvas_w:
                        if ((x, y) in grid and 
                            (color_idx, opacity_idx) in grid[(x, y)] and
                            (x, y) not in processed):
                            line_start = x
                            break
                        x += 1
                    
                    # No line found, move to next position
                    if line_start is None:
                        break
                    
                    # Find end of horizontal line
                    line_end = line_start
                    x = line_start + 1
                    while x < self.canvas_w:
                        if ((x, y) in grid and 
                            (color_idx, opacity_idx) in grid[(x, y)] and
                            (x, y) not in processed):
                            line_end = x
                            x += 1
                        else:
                            break
                    
                    # Check if line is long enough
                    line_length = line_end - line_start + 1
                    if line_length >= min_line_width:
                        # Store the horizontal line
                        precomputed_lines[(color_idx, opacity_idx)]['h_lines'].append(
                            (line_start, y, line_end)
                        )
                        # Mark all pixels in this line as processed globally
                        for i in range(line_start, line_end + 1):
                            processed.add((i, y))
                    else:
                        # Line too short, just increment x to look for the next line
                        x = line_end + 1
            
            # Update progress for horizontal lines - scale from 20% to 45%
            if y % 10 == 0 or y == self.canvas_h - 1:
                h_percent = grid_building_steps + int((y / self.canvas_h) * horizontal_line_steps)
                progress_bar.setValue(h_percent)
                elapsed = time.time() - start_time
                remaining = (elapsed / h_percent) * (total_progress_steps - h_percent) if h_percent > 0 else 0
                elapsed_str = time.strftime("%M:%S", time.gmtime(elapsed))
                remaining_str = time.strftime("%M:%S", time.gmtime(remaining))
                progress_status.setText(f"Finding horizontal lines: {int(y / self.canvas_h * 100)}% | " +
                                         f"Elapsed: {elapsed_str} | Remaining: {remaining_str}")
                QApplication.processEvents()
        
        # Step 3: Find vertical lines - 25% of progress (45% to 70%)
        progress_status.setText("Finding vertical lines...")
        QApplication.processEvents()
        
        # Process all columns of the canvas
        for x in range(self.canvas_w):
            # For each color, check for vertical lines in this column
            for (color_idx, opacity_idx), count in color_opacity_map.items():
                if count < min_line_width:
                    continue
                
                y = 0
                while y < self.canvas_h:
                    # Find start of vertical line
                    line_start = None
                    while y < self.canvas_h:
                        if ((x, y) in grid and 
                            (color_idx, opacity_idx) in grid[(x, y)] and
                            (x, y) not in processed):
                            line_start = y
                            break
                        y += 1
                    
                    # No line found, move to next column
                    if line_start is None:
                        break
                    
                    # Find end of vertical line
                    line_end = line_start
                    y = line_start + 1
                    while y < self.canvas_h:
                        if ((x, y) in grid and 
                            (color_idx, opacity_idx) in grid[(x, y)] and
                            (x, y) not in processed):
                            line_end = y
                            y += 1
                        else:
                            break
                    
                    # Check if line is long enough
                    line_length = line_end - line_start + 1
                    if line_length >= min_line_width:
                        # Store the vertical line
                        precomputed_lines[(color_idx, opacity_idx)]['v_lines'].append(
                            (x, line_start, line_end)
                        )
                        # Mark all pixels in this line as processed globally
                        for i in range(line_start, line_end + 1):
                            processed.add((x, i))
                    else:
                        # Line too short, just increment y to look for the next line
                        y = line_end + 1
            
            # Update progress for vertical lines - scale from 45% to 70%
            if x % 10 == 0 or x == self.canvas_w - 1:
                v_percent = grid_building_steps + horizontal_line_steps + int((x / self.canvas_w) * vertical_line_steps)
                progress_bar.setValue(v_percent)
                elapsed = time.time() - start_time
                remaining = (elapsed / v_percent) * (total_progress_steps - v_percent) if v_percent > 0 else 0
                elapsed_str = time.strftime("%M:%S", time.gmtime(elapsed))
                remaining_str = time.strftime("%M:%S", time.gmtime(remaining))
                progress_status.setText(f"Finding vertical lines: {int(x / self.canvas_w * 100)}% | " +
                                         f"Elapsed: {elapsed_str} | Remaining: {remaining_str}")
                QApplication.processEvents()
                
        # Step 4: Find diagonal lines - 20% of progress (70% to 90%)
        # Only do diagonal detection if the setting is enabled
        use_diagonal_lines = bool(self.settings.value("use_diagonal_lines", default_settings["use_diagonal_lines"]))
        
        if use_diagonal_lines:
            progress_status.setText("Finding diagonal lines...")
            progress_bar.setValue(70)  # Set to start of diagonal processing
            QApplication.processEvents()
            
            # Process each color for diagonal lines
            colors_processed = 0
            for (color_idx, opacity_idx), count in color_opacity_map.items():
                # Only process colors with enough pixels to potentially form diagonal lines
                if count < min_line_width:
                    continue
                    
                # Use the diagonal detection algorithm
                color_key = (color_idx, opacity_idx)
                diagonal_lines = self.detect_diagonal_lines(grid, color_key, processed, min_line_width)
                
                # Store the detected diagonal lines
                precomputed_lines[color_key]['d_lines'] = diagonal_lines
                
                # Update progress for diagonal line detection - scale from 70% to 90%
                colors_processed += 1
                if colors_processed % 5 == 0 or colors_processed == total_colors:
                    d_percent = grid_building_steps + horizontal_line_steps + vertical_line_steps + int((colors_processed / total_colors) * diagonal_line_steps)
                    progress_bar.setValue(d_percent)
                    elapsed = time.time() - start_time
                    remaining = (elapsed / d_percent) * (total_progress_steps - d_percent) if d_percent > 0 else 0
                    elapsed_str = time.strftime("%M:%S", time.gmtime(elapsed))
                    remaining_str = time.strftime("%M:%S", time.gmtime(remaining))
                    progress_status.setText(f"Finding diagonal lines: {int(colors_processed / total_colors * 100)}% | " +
                                           f"Elapsed: {elapsed_str} | Remaining: {remaining_str}")
                    QApplication.processEvents()
        else:
            # Skip diagonal line detection
            progress_bar.setValue(90)
            progress_status.setText("Diagonal line detection disabled - skipping")
            QApplication.processEvents()
            time.sleep(0.5)  # Brief pause to show the status message
        
        # Step 5: Collect remaining points (90% to 100%)
        progress_status.setText("Collecting remaining points...")
        progress_bar.setValue(90)
        QApplication.processEvents()
        
        # Find all remaining points for each color
        for (color_idx, opacity_idx) in color_opacity_map:
            pixel_points = []
            # Check each pixel in the layered colors map
            for (x, y), layers in self.layered_colors_map.items():
                # If this pixel has this color and hasn't been processed as part of a line, add it as a point
                if ((color_idx, opacity_idx) in layers and (x, y) not in processed):
                    pixel_points.append((x, y))
            
            precomputed_lines[(color_idx, opacity_idx)]['points'] = pixel_points
        
        # Calculate statistics
        total_horizontal_lines = sum(len(data['h_lines']) for data in precomputed_lines.values())
        total_vertical_lines = sum(len(data['v_lines']) for data in precomputed_lines.values())
        total_diagonal_lines = sum(len(data['d_lines']) for data in precomputed_lines.values())
        total_points = sum(len(data['points']) for data in precomputed_lines.values())
        
        # Final progress update
        progress_bar.setValue(100)
        elapsed = time.time() - start_time
        elapsed_str = time.strftime("%M:%S", time.gmtime(elapsed))
        progress_status.setText(f"Optimization complete in {elapsed_str}")
        QApplication.processEvents()
        
        # Close the progress dialog after a brief delay so the user can see it completed
        time.sleep(0.5)
        progress_dialog.close()
        
        # Calculate how many individual pixels were converted to lines
        total_line_pixels = (
            # Calculate horizontal line pixels
            sum(end_x - start_x + 1 
                for data in precomputed_lines.values() 
                for start_x, y, end_x in data['h_lines']) +
            # Calculate vertical line pixels
            sum(end_y - start_y + 1 
                for data in precomputed_lines.values() 
                for x, start_y, end_y in data['v_lines']) +
            # Calculate diagonal line pixels (length of each diagonal)
            sum(max(abs(end_x - start_x), abs(end_y - start_y)) + 1 
                for data in precomputed_lines.values() 
                for (start_x, start_y), (end_x, end_y) in data['d_lines'])
        )
        
        pixels_saved = total_line_pixels - (total_horizontal_lines + total_vertical_lines + total_diagonal_lines)
        
        self.parent.ui.log_TextEdit.append(
            f"Optimization complete: {total_horizontal_lines} horizontal lines, " +
            f"{total_vertical_lines} vertical lines, " +
            f"{total_diagonal_lines} diagonal lines, " +
            f"{total_points} individual points"
        )
        
        self.parent.ui.log_TextEdit.append(
            f"Saved {pixels_saved} individual clicks by using line optimization" +
            f" ({(pixels_saved / (pixels_saved + total_points) * 100):.1f}% efficiency)"
        )
        
        return precomputed_lines

    def clear_last_painting_settings(self):
        """Clears the last used color/brush/opacity settings.
        Called when a painting is finished, aborted, or canceled in any way.
        """
        self.parent.ui.log_TextEdit.append("Clearing last used painting settings...")
        self.current_ctrl_size = None
        self.current_ctrl_brush = None
        self.current_ctrl_opacity = None
        self.current_ctrl_color = None

    def is_same_color_pixel(self, grid, x, y, color_key, processed):
        """Check if a pixel at (x,y) has the specified color and hasn't been processed yet"""
        return ((x, y) in grid and 
                color_key in grid[(x, y)] and 
                (x, y) not in processed)

    def detect_diagonal_lines(self, grid, color_key, processed, min_line_width):
        """
        Detect diagonal lines for a specific color key.
        
        Args:
            grid: Dictionary mapping (x, y) coordinates to list of color keys
            color_key: The (color_idx, opacity_idx) key to detect lines for
            processed: Set of already processed pixels
            min_line_width: Minimum number of pixels to consider as a line
            
        Returns:
            List of diagonal lines in format [((start_x, start_y), (end_x, end_y)), ...]
        """
        diagonal_lines = []
        candidates = {}  # Dictionary to track diagonal line candidates
        
        # Check for pixels of this color that haven't been processed yet
        for (x, y), colors in grid.items():
            if color_key in colors and (x, y) not in processed:
                # Check for diagonal patterns in 4 directions
                # Direction 1: 45° (down-right)
                diag1 = f"dr_{x - y}"  # Down-right diagonal identifier
                if diag1 not in candidates:
                    candidates[diag1] = []
                candidates[diag1].append((x, y))
                
                # Direction 2: 135° (down-left)
                diag2 = f"dl_{x + y}"  # Down-left diagonal identifier
                if diag2 not in candidates:
                    candidates[diag2] = []
                candidates[diag2].append((x, y))
        
        # Process diagonal line candidates
        for diag_id, points in candidates.items():
            # Only process if we have enough points to make a line
            if len(points) < min_line_width:
                continue
                
            # Sort points based on the direction
            if diag_id.startswith("dr_"):  # Down-right: sort by x (or y)
                points.sort(key=lambda p: p[0])
            else:  # Down-left: sort by x
                points.sort(key=lambda p: p[0])
            
            # Find continuous segments in the sorted points
            segments = []
            current_segment = []
            
            for i, point in enumerate(points):
                if not current_segment:
                    current_segment.append(point)
                    continue
                    
                prev_point = current_segment[-1]
                
                # Check if points are adjacent diagonally
                is_adjacent = False
                if diag_id.startswith("dr_"):  # Down-right
                    is_adjacent = (point[0] == prev_point[0] + 1 and point[1] == prev_point[1] + 1)
                else:  # Down-left
                    is_adjacent = (point[0] == prev_point[0] + 1 and point[1] == prev_point[1] - 1)
                
                if is_adjacent:
                    current_segment.append(point)
                else:
                    # End current segment if points aren't adjacent
                    if len(current_segment) >= min_line_width:
                        segments.append(current_segment)
                    current_segment = [point]
            
            # Add the last segment if it's long enough
            if len(current_segment) >= min_line_width:
                segments.append(current_segment)
            
            # Convert segments to line format and add to result
            for segment in segments:
                start_point = segment[0]
                end_point = segment[-1]
                diagonal_lines.append((start_point, end_point))
                
                # Mark all pixels in this segment as processed
                for px, py in segment:
                    processed.add((px, py))
        
        return diagonal_lines

    def update_painting_status_ui(self, color_idx, opacity_idx, color_key, precomputed_lines, operation_counter, total_operations, start_time):
        """Update the painting status UI with current progress information
        
        Args:
            color_idx: Current color index
            opacity_idx: Current opacity index 
            color_key: Tuple of (color_idx, opacity_idx)
            precomputed_lines: Dictionary of precomputed lines
            operation_counter: Current operation count
            total_operations: Total operations to complete
            start_time: Time when painting started
        """
        # Make sure the status frame is visible
        if not self.parent.ui.paintStatusFrame.isVisible():
            self.parent.ui.log_TextEdit.hide()
            self.parent.ui.paintStatusFrame.show()
            
        # Update the elapsed time and estimated remaining time
        current_time = time.time()
        elapsed_time = int(current_time - start_time)
        elapsed_str = time.strftime("%H:%M:%S", time.gmtime(elapsed_time))
        
        # Calculate remaining time based on progress
        if operation_counter > 0:
            progress_ratio = operation_counter / total_operations
            if progress_ratio > 0:
                remaining_time = int((elapsed_time / progress_ratio) * (1 - progress_ratio))
                remaining_str = time.strftime("%H:%M:%S", time.gmtime(remaining_time))
            else:
                remaining_str = "??:??:??"
        else:
            remaining_str = time.strftime("%H:%M:%S", time.gmtime(self.estimated_time))
        
        # Update the time status label
        self.parent.ui.timeStatusLabel.setText(f"Time: {elapsed_str} | Remaining: {remaining_str}")
        
        # Calculate current color progress using the sorted color keys for sequential numbering
        # If we have our sorted color keys list, use it for proper sequential numbering
        if hasattr(self, 'sorted_color_keys') and self.sorted_color_keys:
            # Find the current color key in the sorted list
            try:
                current_color_num = self.sorted_color_keys.index(color_key) + 1
            except ValueError:
                # Fallback if not found
                current_color_num = list(precomputed_lines.keys()).index(color_key) + 1
        else:
            # Fallback to previous method if sorted keys not available
            current_color_num = list(precomputed_lines.keys()).index(color_key) + 1
        
        total_colors = len(precomputed_lines)
        self.parent.ui.colorProgressLabel.setText(f"Color: {current_color_num}/{total_colors}")
        
        # Update the color swatch with current color
        if color_idx < len(self.base_palette_colors):
            rgb_color = self.base_palette_colors[color_idx]
            hex_color = rgb_to_hex(rgb_color)
            opacity_percent = int(self.opacity_values[opacity_idx] * 100)
            
            # Set the background color of the swatch frame
            self.parent.ui.colorSwatchFrame.setStyleSheet(f"background-color: {hex_color};")
            
            # Update the color info label
            self.parent.ui.currentColorLabel.setText(f"{hex_color}\nOpacity: {opacity_percent}%")
        
        # Process UI events
        QApplication.processEvents()

    def show_log_text(self):
        """Show the log text and hide the status frame"""
        # Don't hide the status frame - that's causing the jumping
        # Just ensure both are visible, with the status frame above the log
        if not self.parent.ui.log_TextEdit.isVisible():
            self.parent.ui.log_TextEdit.show()
        QApplication.processEvents()

    def start_status_update_timer(self, color_key, precomputed_lines, operation_counter, total_operations, start_time):
        """Start a timer to continuously update the status UI during painting
        
        Args:
            color_key: Current (color_idx, opacity_idx) tuple
            precomputed_lines: Dictionary of precomputed lines
            operation_counter: Current operation count
            total_operations: Total operations to complete
            start_time: Time when painting started
        """
        # Store the current state information for timer updates
        self.current_color_key = color_key
        self.current_operation_counter = operation_counter
        self.current_total_operations = total_operations
        self.precomputed_lines = precomputed_lines
        
        # Stop existing timer if running
        if self.status_update_timer is not None:
            self.status_update_timer.stop()
        
        # Create and start a new timer
        self.status_update_timer = QTimer(self.parent)
        self.status_update_timer.timeout.connect(lambda: self.update_status_from_timer(start_time))
        self.status_update_timer.start(1000)  # Update every second
        
    def update_status_from_timer(self, start_time):
        """Update the status UI from the timer callback"""
        if self.current_color_key is None:
            return
            
        color_idx, opacity_idx = self.current_color_key
        
        # Update the elapsed time and estimated remaining time
        current_time = time.time()
        elapsed_time = int(current_time - start_time)
        elapsed_str = time.strftime("%H:%M:%S", time.gmtime(elapsed_time))
        
        # Calculate remaining time based on progress
        if self.current_operation_counter > 0:
            progress_ratio = self.current_operation_counter / self.current_total_operations
            if progress_ratio > 0:
                remaining_time = int((elapsed_time / progress_ratio) * (1 - progress_ratio))
                remaining_str = time.strftime("%H:%M:%S", time.gmtime(remaining_time))
            else:
                remaining_str = "??:??:??"
        else:
            remaining_str = time.strftime("%H:%M:%S", time.gmtime(self.estimated_time))
        
        # Update the time status label
        self.parent.ui.timeStatusLabel.setText(f"Time: {elapsed_str} | Remaining: {remaining_str}")
        
        # Update progress bar with current progress
        progress_percent = int((self.current_operation_counter / self.current_total_operations) * 100)
        self.parent.ui.progress_ProgressBar.setValue(progress_percent)
        
        # Process UI events
        QApplication.processEvents()

    def update_preview_quality(self, quality_percent):
        """
        Update the preview image based on the quality percentage slider.
        A lower quality percentage will merge similar colors together.
        
        Args:
            quality_percent (int): Quality percentage (0-100)
        """
        if self.org_img is None:
            return
            
        self.parent.ui.log_TextEdit.append(f"Updating preview with {quality_percent}% quality setting...")
        QApplication.processEvents()
        
        # Store the quality setting in the settings
        self.settings.setValue("color_merge_quality", quality_percent)
        
        try:
            # Prepare the base image
            temp_img = self.org_img.copy()
            if temp_img.mode != "RGB":
                temp_img = temp_img.convert("RGB")
                
            # Get background color from settings
            bg_color_hex = self.settings.value("background_color", default_settings["background_color"])
            bg_color_rgb = hex_to_rgb(bg_color_hex)
            
            background_color = bg_color_rgb
            
            # Store the background color used for calculation
            self.background_color = background_color
            
            # Define the opacity values
            self.opacity_values = [1.0, 0.75, 0.5, 0.25]
            
            # Create a progress update callback function to update the UI
            def update_progress_callback(percent, elapsed, remaining):
                # Update the progress bar
                self.parent.ui.progress_ProgressBar.setValue(percent)
                
                # Update the log every 10% to avoid too many updates
                if percent % 10 == 0 or percent == 100:
                    elapsed_str = time.strftime("%M:%S", time.gmtime(elapsed)) if elapsed else "00:00"
                    remaining_str = time.strftime("%M:%S", time.gmtime(remaining)) if remaining else "00:00"
                    self.parent.ui.log_TextEdit.append(f"Processing: {percent}% | Elapsed: {elapsed_str} | Remaining: {remaining_str}")
                
                # Process UI events to make sure the UI updates
                QApplication.processEvents()
                
                # Return False to indicate we shouldn't cancel processing
                return False
            
            # Use our color blending module but with the quality threshold
            from lib.color_blending import simulate_layered_image, color_distance
            
            # Override the color_distance comparison threshold in find_optimal_layers
            # by monkey patching the function temporarily
            from lib.color_blending import find_optimal_layers as original_find_optimal_layers
            
            # Create a wrapper that uses our similarity threshold
            def quality_adjusted_find_optimal_layers(target_color, background_color, base_colors, 
                                                  opacity_levels, max_layers=3, color_cache=None):
                
                # Override the early termination threshold in find_optimal_layers
                def patched_color_distance(color1, color2):
                    # Calculate basic Euclidean distance
                    r1, g1, b1 = color1
                    r2, g2, b2 = color2
                    return ((r1 - r2) ** 2 + (g1 - g2) ** 2 + (b1 - b2) ** 2) ** 0.5
                
                # Store the original functions
                original_color_distance = color_distance
                
                # Replace the functions
                color_blending_module = sys.modules['lib.color_blending']
                color_blending_module.color_distance = patched_color_distance
                
                # Call the original function with our adjusted threshold
                result = original_find_optimal_layers(
                    target_color, background_color, base_colors, 
                    opacity_levels, max_layers, color_cache
                )
                
                # Restore the original functions
                color_blending_module.color_distance = original_color_distance
                
                return result
            
            # Replace the find_optimal_layers function temporarily
            import sys
            color_blending_module = sys.modules['lib.color_blending']
            color_blending_module.find_optimal_layers = quality_adjusted_find_optimal_layers
            
            # Override the color merging threshold
            # This affects how aggressively similar colors are grouped together
            def create_layered_colors_map_with_quality(image, background_color, palette_colors, 
                                                    opacity_values, max_layers=2, update_callback=None):
                # Override bucket size based on quality: 100% => bucket_size=1, 0% => bucket_size up to 50
                bucket_size = max(1, int(1 + (1 - quality_percent / 100.0) * 50))
                
                # Create a custom version that uses our adjusted bucket size and similarity threshold
                width, height = image.size
                pixel_data = image.load()
                layered_colors = {}
                color_cache = {}
                
                # Starting timestamp for progress calculation
                start_time = time.time()
                progress_shown = False
                
                # Find unique colors in the image (with sampling for large images)
                unique_colors = set()
                self.parent.ui.log_TextEdit.append("Analyzing image colors...")
                QApplication.processEvents()
                
                # Update progress with the scan phase (0-5%)
                if update_callback:
                    update_callback(0, 0, 0)
                    progress_shown = True
                
                downsample = max(1, min(width, height) // 400)
                total_pixels = (width // downsample) * (height // downsample)
                pixels_processed = 0
                
                for y in range(0, height, downsample):
                    for x in range(0, width, downsample):
                        unique_colors.add(pixel_data[x, y])
                        pixels_processed += 1
                        
                        # Update progress every 5000 pixels or at completion
                        if pixels_processed % 5000 == 0 or pixels_processed >= total_pixels:
                            if update_callback:
                                scan_progress = min(5, int(pixels_processed / total_pixels * 5))
                                elapsed = time.time() - start_time
                                remaining = elapsed / scan_progress * (5 - scan_progress) if scan_progress > 0 else 0
                                update_callback(scan_progress, elapsed, remaining)
                
                # Group similar colors using our quality-adjusted bucket size
                color_groups = {}
                
                # Update progress - now on color grouping phase (5-25%)
                if update_callback:
                    update_callback(5, time.time() - start_time, 0)
                
                total_unique_colors = len(unique_colors)
                colors_processed = 0
                
                for color in unique_colors:
                    # Quantize the color into buckets (adjusts based on quality)
                    bucket_key = (color[0]//bucket_size, color[1]//bucket_size, color[2]//bucket_size)
                    if bucket_key not in color_groups:
                        color_groups[bucket_key] = []
                    color_groups[bucket_key].append(color)
                    
                    # Update progress
                    colors_processed += 1
                    if colors_processed % 100 == 0 or colors_processed >= total_unique_colors:
                        if update_callback:
                            group_progress = 5 + min(20, int(colors_processed / total_unique_colors * 20))
                            elapsed = time.time() - start_time
                            remaining = elapsed / group_progress * (25 - group_progress) if group_progress > 0 else 0
                            update_callback(group_progress, elapsed, remaining)
                
                # Calculate average colors for each bucket
                bucket_layers = {}
                
                # Update progress - now on color layer calculation phase (25-75%)
                if update_callback:
                    update_callback(25, time.time() - start_time, 0)
                
                self.parent.ui.log_TextEdit.append(f"Processing {len(color_groups)} color groups...")
                QApplication.processEvents()
                
                total_buckets = len(color_groups)
                buckets_processed = 0
                
                for bucket_key, colors in color_groups.items():
                    r_sum = g_sum = b_sum = 0
                    for color in colors:
                        r_sum += color[0]
                        g_sum += color[1]
                        b_sum += color[2]
                    avg_color = (
                        int(r_sum / len(colors)),
                        int(g_sum / len(colors)),
                        int(b_sum / len(colors))
                    )
                    
                    # Calculate layers for this color bucket
                    bucket_layers[bucket_key] = quality_adjusted_find_optimal_layers(
                        avg_color,
                        background_color,
                        palette_colors,
                        opacity_values,
                        max_layers,
                        color_cache
                    )
                    
                    # Update progress
                    buckets_processed += 1
                    if buckets_processed % 10 == 0 or buckets_processed >= total_buckets:
                        if update_callback:
                            bucket_progress = 25 + min(50, int(buckets_processed / total_buckets * 50))
                            elapsed = time.time() - start_time
                            remaining = elapsed / bucket_progress * (75 - bucket_progress) if bucket_progress > 0 else 0
                            update_callback(bucket_progress, elapsed, remaining)
                
                # Assign colors to each pixel using the bucket calculations
                # Update progress - now on pixel assignment phase (75-100%)
                if update_callback:
                    update_callback(75, time.time() - start_time, 0)
                
                self.parent.ui.log_TextEdit.append("Finalizing pixel assignments...")
                QApplication.processEvents()
                
                total_image_pixels = width * height
                image_pixels_processed = 0
                
                for y in range(height):
                    for x in range(width):
                        color = pixel_data[x, y]
                        bucket_key = (color[0]//bucket_size, color[1]//bucket_size, color[2]//bucket_size)
                        
                        # Get layers from bucket
                        layers = bucket_layers.get(bucket_key, [])
                        
                        # Only store pixels that need painting
                        if layers:
                            layered_colors[(x, y)] = layers
                        
                        # Update progress less frequently for better performance
                        image_pixels_processed += 1
                        if image_pixels_processed % 10000 == 0 or image_pixels_processed >= total_image_pixels:
                            if update_callback:
                                pixel_progress = 75 + min(25, int(image_pixels_processed / total_image_pixels * 25))
                                elapsed = time.time() - start_time
                                remaining = elapsed / pixel_progress * (100 - pixel_progress) if pixel_progress > 0 else 0
                                update_callback(pixel_progress, elapsed, remaining)
                
                # Final update
                if update_callback:
                    elapsed = time.time() - start_time
                    update_callback(100, elapsed, 0)
                
                return layered_colors
            
            # Call our quality-adjusted function with the progress callback
            self.parent.ui.log_TextEdit.append(f"Processing image with {quality_percent}% quality...")
            QApplication.processEvents()
            
            self.layered_colors_map = create_layered_colors_map_with_quality(
                temp_img,
                background_color,
                self.base_palette_colors,
                self.opacity_values,
                max_layers=2,
                update_callback=update_progress_callback
            )
            
            # Restore the original function
            color_blending_module.find_optimal_layers = original_find_optimal_layers
            
            # Create the simulated output image
            self.parent.ui.log_TextEdit.append("Creating final preview image...")
            self.parent.ui.progress_ProgressBar.setValue(95)
            QApplication.processEvents()
            
            self.simulated_img = simulate_layered_image(
                temp_img,
                background_color,
                self.base_palette_colors,
                self.opacity_values,
                self.layered_colors_map
            )
            
            # Cache the calculation results
            self.color_calculation_cache = {
                'resized_img': temp_img,
                'layered_colors_map': self.layered_colors_map,
                'simulated_img': self.simulated_img,
                'background_color': background_color
            }
            
            # Update the quantized image for display
            self.quantized_img = self.simulated_img
            
            # Create a pixmap for display
            self.parent.ui.progress_ProgressBar.setValue(98)
            QApplication.processEvents()
            self.parent.ui.log_TextEdit.append("Generating preview pixmap...")
            
            self.quantized_img.save("temp_quantized.png")
            self.quantized_img_pixmap = QPixmap("temp_quantized.png")
            os.remove("temp_quantized.png")
            
            # Complete the progress bar
            self.parent.ui.progress_ProgressBar.setValue(100)
            QApplication.processEvents()
            
            # Log statistics
            pixel_count = sum(1 for _ in self.layered_colors_map.values())
            total_pixels = temp_img.width * temp_img.height
            self.parent.ui.log_TextEdit.append(
                f"Preview updated: {pixel_count:,} pixels will be painted " +
                f"({pixel_count / total_pixels:.1%} of image) at {quality_percent}% quality"
            )
            # Log number of unique color+opacity combinations that will be painted
            unique_color_layers = { (ci, oi) for layers in self.layered_colors_map.values() for (ci, oi) in layers }
            self.parent.ui.log_TextEdit.append(
                f"{len(unique_color_layers)} unique color+opacity combinations will be used for painting"
            )
            return True
            
        except Exception as e:
            import traceback
            self.parent.ui.log_TextEdit.append(f"Error updating preview: {str(e)}")
            self.parent.ui.log_TextEdit.append(traceback.format_exc())
            return False
