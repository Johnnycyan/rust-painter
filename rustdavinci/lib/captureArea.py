#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from pynput import keyboard
from PIL import Image, ImageTk

import tkinter as tk
import pyautogui
import win32api
import time
import numpy as np

abort_capturing_mode = False


def key_event(key):
    """Abort capturing mode"""
    global abort_capturing_mode
    abort_capturing_mode = True


def capture_area(preview_image=None):
    """Capture an area on the screen by clicking and dragging the mouse to the bottom right corner.
    
    Args:
        preview_image: Optional PIL Image to show as preview in selection area
        
    Returns:    area_x,
                area_y,
                area_w,
                area_h
                or False if canceled
    """
    global abort_capturing_mode
    abort_capturing_mode = False  # Reset in case of previous abort
    
    # Set up keyboard listener for escape key to abort
    listener = keyboard.Listener(on_press=key_event)
    listener.start()

    # Initialize Tkinter window for overlay
    root = tk.Tk()
    root.withdraw()
    area = tk.Toplevel(root)
    area.overrideredirect(1)  # No window decorations
    area.attributes("-topmost", True)  # Keep on top
    
    # Initialize with appropriate transparency
    area.wm_attributes("-alpha", 0.8 if preview_image is not None else 0.5)
    area.geometry("0x0")  # Start with zero size
    
    # Canvas for drawing the preview image
    canvas = tk.Canvas(area, highlightthickness=0)
    canvas.pack(fill=tk.BOTH, expand=True)
    
    # Tracking variables
    prev_state = win32api.GetKeyState(0x01)  # Left mouse button
    pressed, active = False, False
    area_TL = (0, 0)  # Top-left coordinates
    photo_image = None  # Will hold the Tkinter photo image
    
    # Moving and resizing state
    drag_start_x, drag_start_y = 0, 0
    is_moving = False
    
    # Function to update the preview image in the selection area
    def update_preview(width, height):
        nonlocal photo_image
        
        if preview_image is not None and width > 10 and height > 10:
            try:
                # Calculate the aspect ratio of the original image
                orig_width, orig_height = preview_image.size
                orig_aspect = orig_width / orig_height
                
                # Calculate the aspect ratio of the selection area
                selection_aspect = width / height
                
                # Determine the size to resize the image while maintaining aspect ratio
                if orig_aspect > selection_aspect:
                    # Image is wider than the selection area
                    resize_width = width
                    resize_height = int(width / orig_aspect)
                else:
                    # Image is taller than the selection area
                    resize_height = height
                    resize_width = int(height * orig_aspect)
                
                # Resize the preview image to fit the current selection area
                resized_img = preview_image.copy().resize((resize_width, resize_height), Image.LANCZOS)
                
                # Create a centered image with background color
                centered_img = Image.new("RGB", (width, height), (50, 50, 50))
                
                # Calculate position to paste the resized image (center it)
                paste_x = (width - resize_width) // 2
                paste_y = (height - resize_height) // 2
                
                # Paste the resized image onto the centered image
                centered_img.paste(resized_img, (paste_x, paste_y))
                
                # Convert to PhotoImage for display
                photo_image = ImageTk.PhotoImage(centered_img)
                
                # Update canvas dimensions and draw the image
                canvas.config(width=width, height=height)
                canvas.delete("all")  # Clear previous content
                canvas.create_image(0, 0, image=photo_image, anchor=tk.NW)
                
                # Add a border to help with visibility
                canvas.create_rectangle(0, 0, width-1, height-1, outline='#FF4040', width=2)
                
                # Force update to ensure image is shown
                canvas.update()
            except Exception as e:
                print(f"Preview update error: {e}")
    
    # Mouse button handlers
    def on_left_click(event):
        nonlocal is_moving, drag_start_x, drag_start_y
        # Start moving the window
        is_moving = True
        drag_start_x = event.x
        drag_start_y = event.y
        
    def on_left_release(event):
        nonlocal is_moving
        is_moving = False
    
    def on_mouse_move(event):
        nonlocal area_TL, is_moving
        if is_moving:
            # Calculate the displacement
            dx = event.x_root - drag_start_x - area_TL[0]
            dy = event.y_root - drag_start_y - area_TL[1]
            
            # Update the position
            new_x = area_TL[0] + dx
            new_y = area_TL[1] + dy
            area_TL = (new_x, new_y)
            
            # Move the window
            area.geometry(f"+{new_x}+{new_y}")
    
    # Instructions label
    instructions = tk.Label(
        area, 
        text="Drag to position • Resize with corners • Right-click to confirm • Press ESC to cancel", 
        bg="#333333", 
        fg="#FFFFFF",
        font=("Arial", 9),
        padx=5,
        pady=3
    )
    instructions.pack(side=tk.BOTTOM, fill=tk.X)
    
    # Resize handles
    handle_size = 10
    handles = []
    handle_dragging = None
    
    # Handle drag events
    def handle_press(event, corner):
        nonlocal handle_dragging
        handle_dragging = corner
    
    def handle_release(event):
        nonlocal handle_dragging
        handle_dragging = None

    def create_corner_handle(corner):
        """Create a handle for resizing the selection area"""
        handle = tk.Label(area, bg="#FF4040", width=1, height=1)
        handle.place(x=0, y=0, width=handle_size, height=handle_size)
        
        # Bind events
        handle.bind("<ButtonPress-1>", lambda e, c=corner: handle_press(e, c))
        handle.bind("<ButtonRelease-1>", handle_release)
        
        handles.append((handle, corner))
        return handle
    
    # Create the handles at each corner
    nw_handle = create_corner_handle("nw")  # Northwest
    ne_handle = create_corner_handle("ne")  # Northeast
    sw_handle = create_corner_handle("sw")  # Southwest
    se_handle = create_corner_handle("se")  # Southeast
    
    # Flag to track if selection was confirmed
    selection_confirmed = False
    selection_result = None
    
    # Confirm selection on right-click
    def confirm_selection(event):
        nonlocal active, selection_confirmed, selection_result
        if active:
            try:
                # Get current dimensions - store them before destroying the window
                width = area.winfo_width()
                height = area.winfo_height()
                
                if width < 10 or height < 10:
                    return  # Too small, ignore
                
                # Store the result before destroying windows
                selection_result = (area_TL[0], area_TL[1], width, height)
                selection_confirmed = True
                
                # Clean up
                listener.stop()
                area.destroy()
                root.destroy()
            except Exception as e:
                print(f"Selection confirmation error: {e}")
    
    # Bind all the events
    area.bind("<ButtonPress-1>", on_left_click)
    area.bind("<ButtonRelease-1>", on_left_release)
    area.bind("<B1-Motion>", on_mouse_move)
    area.bind("<ButtonPress-3>", confirm_selection)
    
    # Main event loop
    try:
        while True:
            if abort_capturing_mode:
                # User canceled with escape key
                abort_capturing_mode = False
                listener.stop()
                area.destroy()
                root.destroy()
                return False
                
            # Check if selection was confirmed
            if selection_confirmed:
                return selection_result

            # Track mouse state
            current_state = win32api.GetKeyState(0x01)
            mouse = pyautogui.position()

            if current_state != prev_state:
                prev_state = current_state
                pressed = True if current_state < 0 else False

            try:
                if pressed:
                    if not active:
                        # Initial click to start selection
                        area_TL = mouse
                        area.geometry(f"+{area_TL[0]}+{area_TL[1]}")
                        active = True
                    
                    # Handle corner drag resizing
                    if handle_dragging:
                        # Get current dimensions
                        width = area.winfo_width()
                        height = area.winfo_height()
                        
                        # Calculate new dimensions based on corner being dragged
                        if handle_dragging == "se":  # Southeast
                            width = max(10, mouse[0] - area_TL[0])
                            height = max(10, mouse[1] - area_TL[1])
                        
                        elif handle_dragging == "sw":  # Southwest
                            old_width = width
                            width = max(10, area_TL[0] + old_width - mouse[0])
                            height = max(10, mouse[1] - area_TL[1])
                            area_TL = (mouse[0], area_TL[1])
                        
                        elif handle_dragging == "ne":  # Northeast
                            width = max(10, mouse[0] - area_TL[0])
                            old_height = height
                            height = max(10, area_TL[1] + old_height - mouse[1])
                            area_TL = (area_TL[0], mouse[1])
                        
                        elif handle_dragging == "nw":  # Northwest
                            old_width = width
                            old_height = height
                            width = max(10, area_TL[0] + old_width - mouse[0])
                            height = max(10, area_TL[1] + old_height - mouse[1])
                            area_TL = (mouse[0], mouse[1])
                        
                        # Update the area size and position
                        area.geometry(f"{width}x{height}+{area_TL[0]}+{area_TL[1]}")
                        update_preview(width, height)
                    
                    # Handle regular drag to create initial selection
                    elif not handle_dragging and not is_moving:
                        width = max(10, mouse[0] - area_TL[0])
                        height = max(10, mouse[1] - area_TL[1])
                        area.geometry(f"{width}x{height}")
                        update_preview(width, height)
                        
                elif not pressed and active:
                    # Update handle positions after resizing or moving
                    width = area.winfo_width()
                    height = area.winfo_height()
                    
                    # Position the corner handles
                    for handle, corner in handles:
                        if corner == "nw":
                            handle.place(x=0, y=0)
                        elif corner == "ne":
                            handle.place(x=width-handle_size, y=0)
                        elif corner == "sw":
                            handle.place(x=0, y=height-handle_size)
                        elif corner == "se":
                            handle.place(x=width-handle_size, y=height-handle_size)

            except Exception as e:
                print(f"Error updating selection area: {e}")
                # Only print the error, don't fail the function

            # Short sleep to reduce CPU usage
            time.sleep(0.01)
            
            # Update UI safely
            try:
                if area.winfo_exists():
                    area.update_idletasks()
                    area.update()
                else:
                    # Window was destroyed, check if we have a result
                    if selection_confirmed:
                        return selection_result
                    else:
                        return False
            except tk.TclError:
                # Window was destroyed
                if selection_confirmed:
                    return selection_result
                else:
                    return False
                
    except Exception as e:
        print(f"Exception in capture_area: {e}")
        # Clean up
        if listener.is_alive():
            listener.stop()
        try:
            if 'area' in locals() and area.winfo_exists():
                area.destroy()
        except:
            pass
        try:
            if 'root' in locals() and root.winfo_exists():
                root.destroy()
        except:
            pass
        return False


def show_area(x, y, w, h):
    """Set a grey box at the coordinates"""
    global abort_capturing_mode
    listener = keyboard.Listener(on_press=key_event)
    listener.start()

    root = tk.Tk()
    root.withdraw()
    area = tk.Toplevel(root)
    area.overrideredirect(1)
    area.wm_attributes("-alpha", 0.5)
    area.geometry("0x0")

    area.geometry("%dx%d+%d+%d" % (w, h, x, y))

    area.update_idletasks()
    area.update()

    time.sleep(3)

    area.destroy()
