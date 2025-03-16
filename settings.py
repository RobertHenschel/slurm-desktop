#!/usr/bin/env python3
"""
Configuration settings for SLURM Partition Viewer
"""

# File paths
QUEUE_ICON_PATH = "queue.png"

# UI settings
PARTITION_ICON_SIZE = 140  # Size in pixels of partition icons
DEFAULT_PARTITION_LABEL = "DEFAULT"
DEFAULT_PARTITION_COLOR = "#2980b9"  # Blue color for default partition labels
PARTITION_ICON_BACKGROUND = "#f0f0f0"  # Background color for partition icons

# GPU settings
GPU_INDICATOR_COLOR = "#16a085"  # Green color for GPU text
GPU_CORNER_COLOR = "#2ecc71"  # Green color for GPU corner indicator
GPU_CORNER_TEXT = "GPU"

# Grid settings
PARTITION_ICON_COLUMNS = 4  # Number of icons per row
GRID_SPACING = 10  # Spacing between grid items

# Window settings
WINDOW_MIN_WIDTH = 800
WINDOW_MIN_HEIGHT = 600
WINDOW_TITLE = "SLURM Partitions"

# Interactive job defaults
DEFAULT_TIME_LIMIT = "4:00:00"  # Default time limit for interactive jobs
DEFAULT_CPUS = 4  # Default number of CPUs for interactive jobs
DEFAULT_MEMORY = 16  # Default memory in GB for interactive jobs
DEFAULT_PROJECT = "staff"  # Default project for interactive jobs
TERMINAL_COMMAND = "mate-terminal"  # Terminal command to use for interactive jobs
