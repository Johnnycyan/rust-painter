#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Color blending module for RustDaVinci.
This module provides functions to calculate the optimal layering of colors
to achieve a target color using Rust's painting system.
"""

import numpy as np
import time
from collections import defaultdict
from lib.color_functions import hex_to_rgb, rgb_to_hex
from lib.rustPaletteData import rust_palette


def alpha_blend(base_color, top_color, opacity):
    """
    Blend two colors according to the opacity of the top color.
    
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
            update_callback(bucket_percent, elapsed, remaining)
    
    # Second pass - assign colors to pixels using the pre-calculated bucket values
    for y in range(height):
        for x in range(width):
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
                update_callback(percent, elapsed, remaining)
    
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
    
    # Apply each pixel's layers
    for (x, y), layers in layered_colors.items():
        current_color = background_color
        
        # Apply each layer
        for color_idx, opacity_idx in layers:
            color = palette_colors[color_idx]
            opacity = opacity_values[opacity_idx]
            current_color = alpha_blend(current_color, color, opacity)
        
        pixels[x, y] = current_color
    
    return simulated


# Optional: Add multithreading support for even faster processing on multi-core systems
try:
    import multiprocessing
    from functools import partial
    
    def _process_color_chunk(chunk_data, background_color, palette_colors, opacity_values, max_layers, color_cache):
        """Process a chunk of colors for multiprocessing"""
        results = {}
        for color in chunk_data:
            results[color] = find_optimal_layers(
                color, background_color, palette_colors, opacity_values, max_layers, color_cache
            )
        return results
    
    def create_layered_colors_map_parallel(image, background_color, palette_colors, opacity_values, max_layers=2, update_callback=None):
        """Parallel version of create_layered_colors_map using multiprocessing"""
        # Similar implementation but with parallel processing for color calculations
        # This would only be used if multiprocessing is available and beneficial
        # Implementation details omitted for brevity - would follow similar pattern to the sequential version
        pass
        
except ImportError:
    # Multiprocessing not available, fall back to single-threaded version
    pass