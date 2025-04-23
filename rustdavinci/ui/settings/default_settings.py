#!/usr/bin/env python3
# -*- coding: utf-8 -*-


default_settings = {
    "window_topmost": 1,
    # quality setting removed as we now only have one quality option
    "ctrl_x": 0,
    "ctrl_y": 0,
    "ctrl_w": 0,
    "ctrl_h": 0,
    "skip_background_color": 1,
    "background_color": "#FFFFFF",  # Updated to pure white (255, 255, 255) which exists in the new palette
    "skip_colors": [],
    "pause_key": "f10",
    "skip_key": "f11",
    "abort_key": "esc",
    "update_canvas": 1,
    "update_canvas_end": 1,
    "draw_lines": 1,
    "show_information": 1,
    "show_preview_load": 1,
    "hide_preview_paint": 1,
    "paint_background":  0,
    "brush_opacities": 1,
    "click_delay": 20,
    "ctrl_area_delay": 180,
    "line_delay": 30,
    "minimum_line_width": 10,
    "brush_type": 1,
    "use_diagonal_lines": 1,      # Enable diagonal line detection (greatly improves efficiency)
    # New cache settings
    "use_cached_data": 1,         # Whether to use cached color calculations if available
    "auto_save_cache": 1          # Whether to automatically save color calculations to cache
}
