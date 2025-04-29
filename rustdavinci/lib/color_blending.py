#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Color blending module for Rust Painter.
This module provides functions to calculate the optimal layering of colors
to achieve a target color using Rust's painting system.
"""

import numpy as np
import time
from collections import defaultdict
from lib.color_functions import hex_to_rgb, rgb_to_hex
from lib.rustPaletteData import rust_palette
import numba as nb

# Global variable for cancellation support across processes
_cancel_processing = False

def alpha_blend(base_color, top_color, opacity):
    """
    Blend two colors according to the opacity of the top color.
    This simulates how Rust's paint system blends colors when painting with opacity.
    
    Args:
        base_color (tuple): RGB tuple of the base color (R,G,B)
        top_color (tuple): RGB tuple of the top color (R,G,B)
        opacity (float): Opacity value between 0 and 1
        
    Returns:
        tuple: The resulting blended RGB color
    """
    r1, g1, b1 = base_color
    r2, g2, b2 = top_color
    
    # Alpha blending formula: result = base * (1 - opacity) + top * opacity
    r = int(r1 * (1 - opacity) + r2 * opacity)
    g = int(g1 * (1 - opacity) + g2 * opacity)
    b = int(b1 * (1 - opacity) + b2 * opacity)
    
    return (r, g, b)


def color_distance(color1, color2):
    """
    Calculate the perceptual distance between two colors.
    Uses a weighted Euclidean distance that accounts for human perception.
    
    Args:
        color1 (tuple): First RGB color tuple
        color2 (tuple): Second RGB color tuple
        
    Returns:
        float: Perceptual distance between the colors
    """
    # Convert to numpy arrays for easier calculation
    c1 = np.array(color1)
    c2 = np.array(color2)
    
    # Weights based on human perception (R:G:B ≈ 3:6:1)
    weights = np.array([0.3, 0.6, 0.1])
    
    # Weighted Euclidean distance
    delta = c1 - c2
    return np.sqrt(np.sum(weights * (delta ** 2)))

# JIT-compiled versions of the core color functions
@nb.jit(nopython=True)
def alpha_blend_numba(base_color, top_color, opacity):
    """
    JIT-compiled version of alpha_blend.
    """
    r1, g1, b1 = base_color
    r2, g2, b2 = top_color
    
    # Alpha blending formula: result = base * (1 - opacity) + top * opacity
    r = int(r1 * (1 - opacity) + r2 * opacity)
    g = int(g1 * (1 - opacity) + g2 * opacity)
    b = int(b1 * (1 - opacity) + b2 * opacity)
    
    return (r, g, b)


@nb.jit(nopython=True)
def color_distance_numba(color1, color2):
    """
    JIT-compiled version of color_distance.
    Uses weighted Euclidean distance for better perceptual accuracy.
    """
    # Weights based on human perception (R:G:B ≈ 3:6:1)
    r_weight = 0.3
    g_weight = 0.6
    b_weight = 0.1
    
    # Calculate weighted distance component by component (numba-friendly)
    dr = (color1[0] - color2[0]) ** 2 * r_weight
    dg = (color1[1] - color2[1]) ** 2 * g_weight
    db = (color1[2] - color2[2]) ** 2 * b_weight
    
    return np.sqrt(dr + dg + db)


@nb.jit(nopython=True)
def find_best_layer_numba(current_color, target_color, base_colors, opacity_levels, improvement_threshold):
    """
    JIT-optimized helper function to find the best layer combination.
    This is extracted from find_optimal_layers to enable JIT optimization.
    
    Returns:
        best_distance, best_layer_color_idx, best_layer_opacity_idx, best_result
    """
    best_distance = float('inf')
    best_layer_color_idx = -1
    best_layer_opacity_idx = -1
    best_result = current_color
    
    for color_idx in range(len(base_colors)):
        color = base_colors[color_idx]
        
        # Skip colors that are too different from target (optimization)
        base_distance = color_distance_numba(color, target_color)
        if base_distance > 5 * color_distance_numba(current_color, target_color):
            continue
            
        for opacity_idx in range(len(opacity_levels)):
            opacity = opacity_levels[opacity_idx]
            
            # Skip 0% opacity as it's useless
            if opacity == 0:
                continue
                
            # Calculate the result if we apply this layer
            result = alpha_blend_numba(current_color, color, opacity)
            
            # Calculate how close this gets us to the target
            distance = color_distance_numba(result, target_color)
            
            if distance < best_distance:
                best_distance = distance
                best_layer_color_idx = color_idx
                best_layer_opacity_idx = opacity_idx
                best_result = result
    
    return best_distance, best_layer_color_idx, best_layer_opacity_idx, best_result


def find_optimal_layers(target_color, background_color, base_colors, opacity_levels, max_layers=3, color_cache=None):
    """
    Find the optimal sequence of color layers to achieve a target color.
    Uses a greedy approach to find a good approximation.
    
    Args:
        target_color (tuple): The target RGB color to achieve
        background_color (tuple): The background RGB color
        base_colors (list): List of available base colors (RGB tuples)
        opacity_levels (list): List of available opacity values (0-1)
        max_layers (int): Maximum number of layers to apply
        color_cache (dict): Cache of previously calculated color combinations
        
    Returns:
        list: A list of (color_index, opacity_index) tuples representing the layers
              from bottom to top
    """
    # Check for cancellation
    global _cancel_processing
    if _cancel_processing:
        return []
    
    # Cache lookup for target color
    if color_cache is not None:
        key = (target_color, background_color)
        if key in color_cache:
            return color_cache[key]
    
    current_color = background_color
    layers = []
    
    # Initial distance to target
    initial_distance = color_distance(current_color, target_color)
    
    # Early termination if colors are very close already (increased threshold for better color match)
    if initial_distance < 1.0:  # Lower threshold for more accurate color matching
        return []
    
    # Try up to max_layers
    for layer_idx in range(max_layers):
        best_distance = float('inf')
        best_layer = None
        best_result = None
        
        # Track improvement to enable early termination (reduced threshold for better fidelity)
        improvement_threshold = 0.05  # Smaller improvement threshold for better color accuracy
        
        # Try all combinations of base color and opacity
        for color_idx, color in enumerate(base_colors):
            # Skip calculations for extremely distant colors to improve speed
            # But be less aggressive in skipping colors for better accuracy
            base_distance = color_distance(color, target_color)
            if base_distance > 5 * initial_distance and layer_idx > 0:
                continue  # Skip colors that are too different from target
                
            for opacity_idx, opacity in enumerate(opacity_levels):
                # Skip 0% opacity as it's useless
                if opacity == 0:
                    continue
                    
                # Calculate the result if we apply this layer
                result = alpha_blend(current_color, color, opacity)
                
                # Calculate how close this gets us to the target
                distance = color_distance(result, target_color)
                
                if distance < best_distance:
                    best_distance = distance
                    best_layer = (color_idx, opacity_idx)
                    best_result = result
        
        # If we found a layer that improves the result
        if best_layer and best_distance < color_distance(current_color, target_color) - improvement_threshold:
            layers.append(best_layer)
            current_color = best_result
            
            # Early termination if we're close enough
            # Increased threshold for better color accuracy
            if best_distance < 2.0:  # More strict "Good enough" threshold for better color fidelity
                break
        else:
            # No improvement possible with additional layers
            break
    
    # Cache the result
    if color_cache is not None:
        key = (target_color, background_color)
        color_cache[key] = layers
    
    return layers


def find_optimal_layers_numba(target_color, background_color, base_colors, opacity_levels, max_layers=3, color_cache=None):
    """
    Numba-optimized version of find_optimal_layers function.
    Uses JIT-compiled helper functions for the most intensive calculations.
    
    Args:
        target_color (tuple): The target RGB color to achieve
        background_color (tuple): The background RGB color
        base_colors (list): List of available base colors (RGB tuples)
        opacity_levels (list): List of available opacity values (0-1)
        max_layers (int): Maximum number of layers to apply
        color_cache (dict): Cache of previously calculated color combinations
        
    Returns:
        list: A list of (color_index, opacity_index) tuples representing the layers
    """
    # Check for cancellation
    global _cancel_processing
    if _cancel_processing:
        return []
    
    # Cache lookup for target color
    if color_cache is not None:
        key = (target_color, background_color)
        if key in color_cache:
            return color_cache[key]
    
    # Convert inputs to numpy arrays for Numba compatibility
    base_colors_array = np.array(base_colors, dtype=np.int32)
    opacity_levels_array = np.array(opacity_levels, dtype=np.float32)
    
    current_color = background_color
    layers = []
    
    # Initial distance to target using numba version
    initial_distance = color_distance_numba(current_color, target_color)
    
    # Early termination if colors are very close already
    if initial_distance < 1.0:
        return []
    
    # Try up to max_layers
    for layer_idx in range(max_layers):
        # Improvement threshold for early termination
        improvement_threshold = 0.05
        
        # Use the JIT-compiled helper function to find the best layer
        best_distance, best_color_idx, best_opacity_idx, best_result = find_best_layer_numba(
            current_color, 
            target_color,
            base_colors_array,
            opacity_levels_array,
            improvement_threshold
        )
        
        # If we found a layer that improves the result
        if best_color_idx >= 0 and best_distance < color_distance_numba(current_color, target_color) - improvement_threshold:
            layers.append((best_color_idx, best_opacity_idx))
            current_color = best_result
            
            # Early termination if we're close enough
            if best_distance < 2.0:
                break
        else:
            # No improvement possible with additional layers
            break
    
    # Cache the result
    if color_cache is not None:
        key = (target_color, background_color)
        color_cache[key] = layers
    
    return layers


def create_layered_colors_map(image, background_color, palette_colors, opacity_values, max_layers=2, update_callback=None):
    """
    Process an entire image to find the optimal color layering for each pixel.
    
    Args:
        image: PIL Image object
        background_color: RGB tuple of background color
        palette_colors: List of base RGB colors
        opacity_values: List of opacity values (0-1)
        max_layers: Maximum number of layers to apply
        update_callback: Function to call with progress updates (percentage, time_elapsed, time_remaining)
        
    Returns:
        dict: A dictionary mapping pixel coordinates to layers list
    """
    # Reset cancellation flag
    global _cancel_processing
    _cancel_processing = False
    
    width, height = image.size
    pixel_data = image.load()
    layered_colors = {}
    
    # Cache for already calculated color mappings
    color_cache = {}
    
    # Performance metrics
    total_pixels = width * height
    processed_pixels = 0
    start_time = time.time()
    update_interval = max(1, total_pixels // 100)  # Update every 1% of pixels
    last_update_time = start_time
    
    # Color similarity bucketing for faster processing
    # Group similar colors together to avoid recalculating
    color_groups = defaultdict(list)
    
    # Use downsampling for large images to reduce computation time
    # Adjusted to smaller downsampling factor for better color fidelity
    downsample = max(1, min(width, height) // 800)  # Less aggressive downsampling for better quality
    downsample_active = total_pixels > 200000  # Only downsample larger images
    
    # First pass - identify unique colors and build color groups
    unique_colors = set()
    for y in range(0, height, 1 + (downsample if downsample_active else 0)):
        for x in range(0, width, 1 + (downsample if downsample_active else 0)):
            unique_colors.add(pixel_data[x, y])
    
    # Create color buckets (group similar colors)
    # Using finer buckets (smaller bucket size) for better color accuracy
    for color in unique_colors:
        # Quantize the color into buckets (reduces color space)
        # Smaller divisor = finer buckets = better color accuracy but more calculation
        bucket_key = (color[0]//5, color[1]//5, color[2]//5)  # Smaller bucket size for better fidelity
        color_groups[bucket_key].append(color)
    
    # Calculate optimal layers for each color bucket (not individual pixels)
    bucket_layers = {}
    bucket_count = len(color_groups)
    bucket_processed = 0
    
    for bucket_key, colors in color_groups.items():
        # Check for cancellation
        if _cancel_processing:
            if update_callback:
                update_callback(0, 0, 0)  # Reset progress
            return {}  # Return empty result
        
        # Use the average color in this bucket
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
        
        # Calculate layers for this color
        bucket_layers[bucket_key] = find_optimal_layers(
            avg_color,
            background_color,
            palette_colors,
            opacity_values,
            max_layers,
            color_cache
        )
        
        # Update progress for bucket calculations
        bucket_processed += 1
        if update_callback and time.time() - last_update_time > 0.25:
            last_update_time = time.time()
            bucket_percent = int((bucket_processed / bucket_count) * 50)  # First 50% of progress
            elapsed = time.time() - start_time
            remaining = (elapsed / bucket_percent) * (100 - bucket_percent) if bucket_percent > 0 else 0
            stop_processing = update_callback(bucket_percent, elapsed, remaining)
            if stop_processing:
                _cancel_processing = True
                return {}  # Return empty result
    
    # Second pass - assign colors to pixels using the pre-calculated bucket values
    for y in range(height):
        for x in range(width):
            # Check for cancellation periodically
            if _cancel_processing:
                return {}  # Return empty result
                
            color = pixel_data[x, y]
            bucket_key = (color[0]//5, color[1]//5, color[2]//5)  # Match bucket size from above
            
            # Get layers from bucket or calculate directly for better accuracy if needed
            layers = bucket_layers.get(bucket_key, [])
            
            # For important colors (high contrast areas), recalculate exactly
            # This improves color accuracy for important details
            is_important_pixel = False
            if x > 0 and y > 0 and x < width-1 and y < height-1:
                # Check surrounding pixels for color contrast (edge detection)
                neighbors = [
                    pixel_data[x-1, y],
                    pixel_data[x+1, y],
                    pixel_data[x, y-1],
                    pixel_data[x, y+1]
                ]
                
                for neighbor in neighbors:
                    if color_distance(color, neighbor) > 30:  # High contrast threshold
                        is_important_pixel = True
                        break
            
            # For important pixels, calculate exact layers
            if is_important_pixel:
                layers = find_optimal_layers(
                    color,
                    background_color,
                    palette_colors,
                    opacity_values,
                    max_layers,
                    color_cache
                )
            
            if layers:  # Only store pixels that need painting
                layered_colors[(x, y)] = layers
            
            # Update progress
            processed_pixels += 1
            if update_callback and processed_pixels % update_interval == 0:
                # Scale from 50% to 100% for the second phase
                percent = 50 + int((processed_pixels / total_pixels) * 50)
                elapsed = time.time() - start_time
                remaining = (elapsed / percent) * (100 - percent) if percent > 0 else 0
                stop_processing = update_callback(percent, elapsed, remaining)
                if stop_processing:
                    _cancel_processing = True
                    return {}  # Return empty result
    
    return layered_colors


def create_layered_colors_map_numba(image, background_color, palette_colors, opacity_values, max_layers=2, update_callback=None):
    """
    Numba-optimized version of create_layered_colors_map.
    Uses JIT-compiled functions for the most intensive calculations.
    
    Args:
        image: PIL Image object
        background_color: RGB tuple of background color
        palette_colors: List of base RGB colors
        opacity_values: List of opacity values (0-1)
        max_layers: Maximum number of layers to apply
        update_callback: Function to call with progress updates (percentage, time_elapsed, time_remaining)
        
    Returns:
        dict: A dictionary mapping pixel coordinates to layers list
    """
    # Reset cancellation flag
    global _cancel_processing
    _cancel_processing = False
    
    # Convert inputs to numpy arrays for Numba compatibility
    base_colors_array = np.array(palette_colors, dtype=np.int32)
    opacity_array = np.array(opacity_values, dtype=np.float32)
    
    width, height = image.size
    pixel_data = image.load()
    layered_colors = {}
    
    # Cache for already calculated color mappings
    color_cache = {}
    
    # Performance metrics
    total_pixels = width * height
    processed_pixels = 0
    start_time = time.time()
    update_interval = max(1, total_pixels // 100)  # Update every 1% of pixels
    last_update_time = start_time
    
    # Color similarity bucketing for faster processing
    color_groups = defaultdict(list)
    
    # Use downsampling for large images to reduce computation time
    downsample = max(1, min(width, height) // 800)
    downsample_active = total_pixels > 200000  # Only downsample larger images
    
    # First pass - identify unique colors and build color groups
    unique_colors = set()
    for y in range(0, height, 1 + (downsample if downsample_active else 0)):
        for x in range(0, width, 1 + (downsample if downsample_active else 0)):
            unique_colors.add(pixel_data[x, y])
    
    # Create color buckets (group similar colors)
    for color in unique_colors:
        # Quantize the color into buckets (reduces color space)
        bucket_key = (color[0]//5, color[1]//5, color[2]//5)  # Bucket size for better fidelity
        color_groups[bucket_key].append(color)
    
    # Calculate optimal layers for each color bucket (not individual pixels)
    bucket_layers = {}
    bucket_count = len(color_groups)
    bucket_processed = 0
    
    # Pre-compile JIT functions by calling them once (this improves first-run performance)
    _ = color_distance_numba((0, 0, 0), (255, 255, 255))
    _ = alpha_blend_numba((0, 0, 0), (255, 255, 255), 0.5)
    
    for bucket_key, colors in color_groups.items():
        # Check for cancellation
        if _cancel_processing:
            if update_callback:
                update_callback(0, 0, 0)  # Reset progress
            return {}  # Return empty result
        
        # Use the average color in this bucket
        if len(colors) > 0:
            # Vectorized calculation of average color using numpy
            colors_array = np.array(colors)
            avg_color = tuple(np.mean(colors_array, axis=0).astype(int))
            
            # Calculate layers for this color using Numba-optimized function
            bucket_layers[bucket_key] = find_optimal_layers_numba(
                avg_color,
                background_color,
                base_colors_array,
                opacity_array,
                max_layers,
                color_cache
            )
        
        # Update progress for bucket calculations
        bucket_processed += 1
        if update_callback and time.time() - last_update_time > 0.25:
            last_update_time = time.time()
            bucket_percent = int((bucket_processed / bucket_count) * 50)  # First 50% of progress
            elapsed = time.time() - start_time
            remaining = (elapsed / bucket_percent) * (100 - bucket_percent) if bucket_percent > 0 else 0
            stop_processing = update_callback(bucket_percent, elapsed, remaining)
            if stop_processing:
                _cancel_processing = True
                return {}  # Return empty result
    
    # Second pass - assign colors to pixels using the pre-calculated bucket values
    # Use numpy arrays for more efficient neighbor checking
    # Create a list to store important pixel coordinates for batch processing
    important_pixels = []
    
    # First identify all important pixels (high contrast areas)
    for y in range(height):
        for x in range(width):
            # Check for cancellation periodically
            if _cancel_processing:
                return {}  # Return empty result
                
            color = pixel_data[x, y]
            bucket_key = (color[0]//5, color[1]//5, color[2]//5)
            
            # Get layers from bucket or calculate directly for better accuracy if needed
            layers = bucket_layers.get(bucket_key, [])
            
            # For important colors (high contrast areas), we'll recalculate exactly
            is_important_pixel = False
            if x > 0 and y > 0 and x < width-1 and y < height-1:
                # Check surrounding pixels for color contrast using JIT-optimized function
                neighbors = [
                    pixel_data[x-1, y],
                    pixel_data[x+1, y],
                    pixel_data[x, y-1],
                    pixel_data[x, y+1]
                ]
                
                for neighbor in neighbors:
                    if color_distance_numba(color, neighbor) > 30:  # High contrast threshold
                        is_important_pixel = True
                        break
            
            # For important pixels, calculate exact layers or add to list for batch processing
            if is_important_pixel:
                important_pixels.append((x, y, color))
            elif layers:  # Only store pixels that need painting
                layered_colors[(x, y)] = layers
            
            # Update progress
            processed_pixels += 1
            if update_callback and processed_pixels % update_interval == 0:
                # Scale from 50% to 100% for the second phase
                percent = 50 + int((processed_pixels / total_pixels) * 50)
                elapsed = time.time() - start_time
                remaining = (elapsed / percent) * (100 - percent) if percent > 0 else 0
                stop_processing = update_callback(percent, elapsed, remaining)
                if stop_processing:
                    _cancel_processing = True
                    return {}  # Return empty result
    
    # Process important pixels
    for x, y, color in important_pixels:
        if _cancel_processing:
            return {}
            
        # Calculate exact layers using Numba-optimized function
        layers = find_optimal_layers_numba(
            color,
            background_color,
            base_colors_array,
            opacity_array,
            max_layers,
            color_cache
        )
        
        if layers:  # Only store pixels that need painting
            layered_colors[(x, y)] = layers
    
    return layered_colors


def simulate_layered_image(image, background_color, palette_colors, opacity_values, layered_colors):
    """
    Create a simulated image based on layered color application.
    
    Args:
        image: Original PIL Image
        background_color: RGB tuple of background color
        palette_colors: List of base RGB colors
        opacity_values: List of opacity values (0-1)
        layered_colors: Dictionary mapping pixel coordinates to layers list
        
    Returns:
        PIL Image: Simulated image after applying all color layers
    """
    from PIL import Image
    
    width, height = image.size
    simulated = Image.new("RGB", (width, height), background_color)
    pixels = simulated.load()
    
    # First, fill all pixels with background color
    for y in range(height):
        for x in range(width):
            pixels[x, y] = background_color
    
    # Apply each pixel's layers - ensure no pixels are left uncolored
    for (x, y), layers in layered_colors.items():
        if not layers:
            continue
            
        current_color = background_color
        
        # Apply each layer
        for color_idx, opacity_idx in layers:
            if color_idx < len(palette_colors) and opacity_idx < len(opacity_values):
                color = palette_colors[color_idx]
                opacity = opacity_values[opacity_idx]
                current_color = alpha_blend(current_color, color, opacity)
            
        # Only set the pixel if we've calculated a valid color
        # This prevents white speckling
        if current_color != (0, 0, 0) or background_color == (0, 0, 0):
            pixels[x, y] = current_color
    
    return simulated


def simulate_layered_image_numba(image, background_color, palette_colors, opacity_values, layered_colors):
    """
    Numba-optimized version of simulate_layered_image function.
    Creates a simulated image based on layered color application using JIT-compiled functions.
    
    Args:
        image: Original PIL Image
        background_color: RGB tuple of background color
        palette_colors: List of base RGB colors
        opacity_values: List of opacity values (0-1)
        layered_colors: Dictionary mapping pixel coordinates to layers list
        
    Returns:
        PIL Image: Simulated image after applying all color layers
    """
    from PIL import Image
    
    width, height = image.size
    simulated = Image.new("RGB", (width, height), background_color)
    pixels = simulated.load()
    
    # Convert palette colors and opacity values to numpy arrays for Numba
    palette_array = np.array(palette_colors, dtype=np.int32)
    opacity_array = np.array(opacity_values, dtype=np.float32)
    
    # First, fill all pixels with background color (faster to do in one step)
    for y in range(height):
        for x in range(width):
            pixels[x, y] = background_color
    
    # Apply each pixel's layers
    for (x, y), layers in layered_colors.items():
        if not layers:
            continue
            
        current_color = background_color
        
        # Apply each layer using the JIT-compiled alpha_blend function
        for color_idx, opacity_idx in layers:
            if color_idx < len(palette_colors) and opacity_idx < len(opacity_values):
                color = palette_array[color_idx]
                opacity = opacity_array[opacity_idx]
                current_color = alpha_blend_numba(current_color, color, opacity)
            
        # Only set the pixel if we've calculated a valid color
        if current_color != (0, 0, 0) or background_color == (0, 0, 0):
            pixels[x, y] = current_color
    
    return simulated


# These functions need to be at module level for multiprocessing to work
def _process_color_chunk(chunk_data):
    """Process a chunk of colors for multiprocessing"""
    # Unpack the arguments from the tuple
    bucket_items, background_color, palette_colors, opacity_values, max_layers = chunk_data
    
    # Check for cancellation
    global _cancel_processing
    if _cancel_processing:
        return {}
    
    local_results = {}
    local_cache = {}  # Local cache for this process
    
    for bucket_key, avg_color in bucket_items:
        # Check for cancellation periodically
        if _cancel_processing:
            return {}
            
        local_results[bucket_key] = find_optimal_layers(
            avg_color,
            background_color,
            palette_colors,
            opacity_values,
            max_layers,
            local_cache
        )
    return local_results

def _process_image_strip(strip_data):
    """Process an image strip for multiprocessing"""
    # Unpack the arguments from the tuple
    strip_bounds, image_data, width, height, bucket_layers, background_color, palette_colors, opacity_values, max_layers = strip_data
    
    # Check for cancellation
    global _cancel_processing
    if _cancel_processing:
        return {}
    
    local_results = {}
    local_cache = {}  # Local cache for this process
    start_x, end_x, start_y, end_y = strip_bounds
    
    for y in range(start_y, end_y):
        for x in range(start_x, end_x):
            # Check for cancellation periodically
            if _cancel_processing:
                return {}
                
            # Get pixel color from the serialized image data
            if 0 <= x < width and 0 <= y < height:
                color = image_data[y * width + x]
                
                bucket_key = (color[0]//5, color[1]//5, color[2]//5)
                
                # Get layers from bucket or calculate directly
                layers = bucket_layers.get(bucket_key, [])
                
                # Check if this is an important pixel (high contrast area)
                is_important_pixel = False
                if x > 0 and y > 0 and x < width-1 and y < height-1:
                    neighbors = []
                    # Get the four surrounding pixels
                    if x > 0:
                        neighbors.append(image_data[y * width + (x-1)])
                    if x < width-1:
                        neighbors.append(image_data[y * width + (x+1)])
                    if y > 0:
                        neighbors.append(image_data[(y-1) * width + x])
                    if y < height-1:
                        neighbors.append(image_data[(y+1) * width + x])
                    
                    for neighbor in neighbors:
                        if color_distance(color, neighbor) > 30:
                            is_important_pixel = True
                            break
                
                # For important pixels, calculate exact layers
                if is_important_pixel:
                    layers = find_optimal_layers(
                        color,
                        background_color,
                        palette_colors,
                        opacity_values,
                        max_layers,
                        local_cache
                    )
                
                if layers:  # Only store pixels that need painting
                    local_results[(x, y)] = layers
    
    return local_results

def set_cancel_flag(cancel=True):
    """Set the global cancellation flag that all processes will check"""
    global _cancel_processing
    _cancel_processing = cancel
    print(f"Cancellation flag set to: {_cancel_processing}")

def create_layered_colors_map_parallel(image, background_color, palette_colors, opacity_values, max_layers=2, update_callback=None):
    """Replaced with Numba-optimized version for better single-core performance"""
    print("Multiprocessing version has been replaced with Numba-optimized single process version")
    return create_layered_colors_map_optimized(image, background_color, palette_colors, opacity_values, max_layers, update_callback)

def create_layered_colors_map_optimized(image, background_color, palette_colors, opacity_values, max_layers=2, update_callback=None):
    """
    Smart wrapper for color map creation that uses the Numba-optimized implementation.
    This is intended to replace the multiprocessing version with a highly optimized single-process version.
    
    Args:
        Same as create_layered_colors_map
        
    Returns:
        dict: A dictionary mapping pixel coordinates to layers list
    """
    print("Using Numba JIT optimization for color processing")
    return create_layered_colors_map_numba(image, background_color, palette_colors, opacity_values, max_layers, update_callback)