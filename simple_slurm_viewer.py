#!/usr/bin/env python3
import sys
import subprocess
import json
import os
from PyQt5.QtWidgets import (QApplication, QMainWindow, QFrame, QLabel, 
                            QGridLayout, QVBoxLayout, QScrollArea, QWidget,
                            QMenu, QAction, QMessageBox)
from PyQt5.QtGui import QIcon, QPixmap, QPainter, QColor, QBrush, QPen
from PyQt5.QtCore import Qt, QSize, QRect

# Import settings
import settings

# Import interactive job functionality
from interactive_job import InteractiveJobDialog, start_interactive_job

class PartitionIcon(QFrame):
    """Simple widget to display a SLURM partition"""
    
    def __init__(self, text, node_count=0, gpu_info=None, parent=None):
        super().__init__(parent)
        
        # Check if this is a default partition (ends with *)
        self.is_default = text.endswith('*')
        
        # Remove the asterisk for display purposes
        if self.is_default:
            self.partition_name = text[:-1]  # Remove the asterisk
        else:
            self.partition_name = text
            
        self.node_count = node_count
        self.gpu_info = gpu_info
        
        # Set fixed size for the icon
        self.setFixedSize(settings.PARTITION_ICON_SIZE, settings.PARTITION_ICON_SIZE)
        
        # Set style for the frame
        self.setFrameStyle(QFrame.Box | QFrame.Raised)
        self.setLineWidth(1)
        
        # Create a layout for this widget
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(4)  # Reduce spacing to fit more information
        
        # Create label for the partition name
        self.name_label = QLabel(self.partition_name)
        self.name_label.setAlignment(Qt.AlignCenter)
        self.name_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        
        # Create label for the icon
        self.icon_label = QLabel()
        self.icon_label.setAlignment(Qt.AlignCenter)
        
        # Try to load the queue.png icon
        icon = QIcon(settings.QUEUE_ICON_PATH)
        pixmap = icon.pixmap(QSize(48, 48))
        
        # Check if the pixmap is valid/non-empty
        if not pixmap.isNull() and pixmap.width() > 0:
            self.icon_label.setPixmap(pixmap)
        else:
            print(f"Warning: Could not load icon: {settings.QUEUE_ICON_PATH} - File not found or invalid")
            # Fallback to text if icon can't be loaded
            self.icon_label.setText("🖥️")
            self.icon_label.setStyleSheet("font-size: 32px;")
        
        # Create label for node count
        self.node_count_label = QLabel(f"{node_count} nodes")
        self.node_count_label.setAlignment(Qt.AlignCenter)
        
        # Create label for default indicator if this is a default partition
        if self.is_default:
            default_label = QLabel(settings.DEFAULT_PARTITION_LABEL)
            default_label.setAlignment(Qt.AlignCenter)
            default_label.setStyleSheet(f"color: {settings.DEFAULT_PARTITION_COLOR}; font-weight: bold; font-size: 10px;")
            layout.addWidget(default_label)
        
        # Add widgets to layout
        layout.addWidget(self.icon_label)
        layout.addWidget(self.name_label)
        layout.addWidget(self.node_count_label)
        
        # Add GPU information if available
        if self.gpu_info and len(self.gpu_info) > 0:
            # Calculate total GPU count
            total_gpus = sum(count for _, count in self.gpu_info)
            
            # Format GPU types in parentheses
            gpu_types = []
            for gpu_type, count in self.gpu_info:
                if count == 1:
                    gpu_types.append(f"{gpu_type}")
                else:
                    gpu_types.append(f"{count} {gpu_type}")
            
            gpu_type_text = ", ".join(gpu_types)
            
            # Create label for GPU information
            gpu_label = QLabel(f"{gpu_type_text} per node")
            gpu_label.setAlignment(Qt.AlignCenter)
            gpu_label.setStyleSheet(f"color: {settings.GPU_INDICATOR_COLOR}; font-weight: bold; font-size: 11px;")
            layout.addWidget(gpu_label)
            
            # If this is a GPU partition, highlight it with a small corner indicator
            self.has_gpus = True
        else:
            self.has_gpus = False
        
        # Set the background color
        self.setStyleSheet(f"background-color: {settings.PARTITION_ICON_BACKGROUND};")
        
        # Enable context menu
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)
           
    def paintEvent(self, event):
        """Custom paint event to draw GPU indicator if needed"""
        super().paintEvent(event)
        
        # If this partition has GPUs, draw a small GPU indicator in the corner
        if self.has_gpus:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.Antialiasing)
            
            # Define color for GPU indicator
            gpu_color = QColor(settings.GPU_CORNER_COLOR)
            
            # Draw a small triangle in the top-right corner
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(gpu_color))
            
            triangle = QRect(self.width() - 25, 0, 25, 17)
            painter.drawRect(triangle)
            
            # Draw a small "GPU" text - moved a bit to the left to fully show the "U"
            painter.setPen(QPen(Qt.white))
            painter.drawText(self.width() - 25, 13, settings.GPU_CORNER_TEXT)
    
    def show_context_menu(self, position):
        """Show context menu for this partition"""
        menu = QMenu(self)
        
        # Set stylesheet for menu to change background color of selected items
        menu.setStyleSheet("""
            QMenu {
                background-color: white;
                border: 1px solid #d0d0d0;
            }
            QMenu::item {
                padding: 6px 20px;
                color: black;
            }
            QMenu::item:selected {
                background-color: #2980b9;
                color: white;
            }
        """)
        
        # Add interactive job action
        interactive_action = QAction("Start Interactive Job", self)
        interactive_action.triggered.connect(self.show_job_dialog)
        menu.addAction(interactive_action)
        
        # Add run application submenu
        app_menu = QMenu("Run Application", self)
        # Apply same stylesheet to application menu
        app_menu.setStyleSheet(menu.styleSheet())
        
        # Try to load applications from app_menu.json
        try:
            if os.path.exists(settings.APP_MENU_JSON):
                with open(settings.APP_MENU_JSON, 'r') as f:
                    app_data = json.load(f)
                    
                    # Create a submenu for each category
                    for category, apps in app_data.items():
                        category_menu = QMenu(category, app_menu)
                        # Apply same stylesheet to category menu
                        category_menu.setStyleSheet(menu.styleSheet())
                        
                        # Add enabled applications to the category menu
                        for app in apps:
                            # Only add if 'enabled' is true (default to not enabled)
                            if app.get('enabled', False):
                                app_name = app.get('name', 'Unknown')
                                app_icon_path = app.get('icon', '')
                                
                                # Try to load icon if available
                                if app_icon_path and os.path.exists(app_icon_path):
                                    icon = QIcon(app_icon_path)
                                    app_action = QAction(icon, app_name, self)
                                else:
                                    app_action = QAction(app_name, self)
                                
                                # Store the exec command in the action's data
                                app_exec = app.get('exec', '')
                                app_action.setData(app_exec)
                                # Connect action to launch method
                                app_action.triggered.connect(
                                    lambda checked, app_name=app_name, app_exec=app_exec: 
                                    self.show_app_job_dialog(app_name, app_exec)
                                )
                                
                                category_menu.addAction(app_action)
                        
                        # Only add the category menu if it has any actions
                        if not category_menu.isEmpty():
                            app_menu.addMenu(category_menu)
        except Exception as e:
            print(f"Error loading application menu: {e}")
            # Add a placeholder action when loading fails
            error_action = QAction("Error loading applications", self)
            error_action.setEnabled(False)
            app_menu.addAction(error_action)
        
        # Add the application menu to the main menu
        menu.addMenu(app_menu)
        
        menu.exec_(self.mapToGlobal(position))
    
    def show_job_dialog(self):
        """Show the interactive job dialog"""
        # Get original partition name (with asterisk if default)
        original_name = self.partition_name
        if self.is_default:
            original_name += "*"
            
        dialog = InteractiveJobDialog(original_name, self)
        if dialog.exec_():
            self.start_interactive_job(
                dialog.get_selected_time(),
                dialog.get_selected_cpus(),
                dialog.get_selected_memory(),
                dialog.get_selected_gpus(),
                dialog.get_selected_project()
            )
    
    def show_app_job_dialog(self, app_name, app_exec):
        """Show the interactive job dialog for running an application"""
        # Get original partition name (with asterisk if default)
        original_name = self.partition_name
        if self.is_default:
            original_name += "*"
            
        # Create a dialog with the application name in the title
        dialog = InteractiveJobDialog(original_name, self, app_title=f"Run {app_name}")
        if dialog.exec_():
            self.start_interactive_job_with_app(
                dialog.get_selected_time(),
                dialog.get_selected_cpus(),
                dialog.get_selected_memory(),
                dialog.get_selected_gpus(),
                dialog.get_selected_project(),
                app_exec
            )
    
    def start_interactive_job(self, time_limit, cpus_per_task, memory, gpus=None, project="staff"):
        """Start an interactive job on this partition"""
        # Call the function from the imported module
        success = start_interactive_job(
            self.partition_name,
            time_limit,
            cpus_per_task,
            memory,
            gpus,
            project
        )
        
        if not success:
            QMessageBox.warning(
                self,
                "Error",
                f"Failed to start interactive job on {self.partition_name}. Check terminal for details."
            )
    
    def start_interactive_job_with_app(self, time_limit, cpus_per_task, memory, gpus=None, project="staff", app_command=None):
        """Start an interactive job on this partition with an application"""
        # Call the function from the imported module
        success = start_interactive_job(
            self.partition_name,
            time_limit,
            cpus_per_task,
            memory,
            gpus,
            project,
            app_command
        )
        
        if not success:
            QMessageBox.warning(
                self,
                "Error",
                f"Failed to start interactive job on {self.partition_name}. Check terminal for details."
            )

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # Set window properties
        self.setWindowTitle(settings.WINDOW_TITLE)
        self.setMinimumSize(settings.WINDOW_MIN_WIDTH, settings.WINDOW_MIN_HEIGHT)
        
        # Try to set the window icon
        icon = QIcon(settings.QUEUE_ICON_PATH)
        if not icon.isNull():
            self.setWindowIcon(icon)
        else:
            print(f"Warning: Could not set window icon: {settings.QUEUE_ICON_PATH} - File not found or invalid")
        
        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Create a scroll area for the grid
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        
        # Create a widget to hold the grid
        grid_widget = QWidget()
        self.grid_layout = QGridLayout(grid_widget)
        
        # Add spacing to the grid
        self.grid_layout.setSpacing(settings.GRID_SPACING)
        self.grid_layout.setContentsMargins(10, 10, 10, 10)
        
        # Set the grid widget as the scroll area's widget
        scroll_area.setWidget(grid_widget)
        
        # Set the main layout for the central widget
        main_layout = QVBoxLayout(central_widget)
        main_layout.addWidget(scroll_area)
        
        # Load and display SLURM partitions
        self.load_partitions()

    def load_partitions(self):
        """Query SLURM for partition information and create icons"""
        try:
            # Run sinfo command to get partition information
            # Format: partition name, node count - preserve the asterisk for default partitions
            result = subprocess.run(
                ["sinfo", "--noheader", "--format=%P,%D"],
                capture_output=True,
                text=True,
                check=True
            )
            
            # Process output and create partition icons
            partitions = []
            for line in result.stdout.strip().split('\n'):
                if line:
                    try:
                        partition_info = line.strip().split(',')
                        if len(partition_info) >= 2:
                            partition_name = partition_info[0]
                            node_count = int(partition_info[1])
                            
                            # Get GPU information for this partition
                            gpu_info = self.get_gpu_info(partition_name.rstrip('*'))
                            
                            partitions.append((partition_name, node_count, gpu_info))
                    except (ValueError, IndexError) as e:
                        print(f"Error parsing partition info: {e} for line: {line}")
            
            # Sort partitions alphabetically, but put default partitions first
            partitions.sort(key=lambda x: (not x[0].endswith('*'), x[0].rstrip('*').lower()))
            
            # Create and place partition icons in the grid
            for i, partition_data in enumerate(partitions):
                row = i // settings.PARTITION_ICON_COLUMNS  # Icons per row based on settings
                col = i % settings.PARTITION_ICON_COLUMNS
                
                if len(partition_data) == 3:
                    partition_name, node_count, gpu_info = partition_data
                else:
                    partition_name, node_count = partition_data
                    gpu_info = None
                
                partition_icon = PartitionIcon(partition_name, node_count, gpu_info)
                self.grid_layout.addWidget(partition_icon, row, col)
            
            # If no partitions were found, show a message
            if not partitions:
                message = QLabel("No SLURM partitions found or 'sinfo' command not available.")
                message.setAlignment(Qt.AlignCenter)
                self.grid_layout.addWidget(message, 0, 0)
                
        except subprocess.CalledProcessError as e:
            # Handle case where sinfo command fails
            message = QLabel(f"Error querying SLURM: {e.stderr}")
            message.setAlignment(Qt.AlignCenter)
            self.grid_layout.addWidget(message, 0, 0)
        except Exception as e:
            # Handle any other errors
            message = QLabel(f"Unexpected error: {str(e)}")
            message.setAlignment(Qt.AlignCenter)
            self.grid_layout.addWidget(message, 0, 0)
    
    def get_gpu_info(self, partition_name):
        """Get GPU information for a partition"""
        try:
            # Run sinfo to get GRES info (which includes GPU info)
            result = subprocess.run(
                ["sinfo", "-p", partition_name, "--noheader", "--format=%G"],
                capture_output=True,
                text=True,
                check=True
            )
            
            # Process the output to extract GPU info
            gres_info = result.stdout.strip()
            
            # If we have GPU info, parse it
            if gres_info and "gpu" in gres_info.lower():
                # Examples of possible GRES formats:
                # "gpu:v100:4" - 4 V100 GPUs
                # "gpu:4" - 4 GPUs of unspecified type
                # "(null)" - No GPUs
                
                try:
                    # Ignore lines with "(null)" or empty lines
                    if gres_info == "(null)" or not gres_info:
                        return None
                    
                    # There might be multiple GRES entries, split by comma
                    gpu_entries = []
                    for entry in gres_info.split(","):
                        if "gpu" in entry.lower():
                            parts = entry.split(":")
                            
                            if len(parts) == 3:  # Format: gpu:type:count
                                gpu_type = parts[1].upper()
                                gpu_count = int(parts[2])
                                gpu_entries.append((gpu_type, gpu_count))
                            elif len(parts) == 2:  # Format: gpu:count
                                gpu_count = int(parts[1])
                                gpu_entries.append(("GPU", gpu_count))
                    
                    # If we found GPU entries, return them
                    if gpu_entries:
                        return gpu_entries
                except Exception as e:
                    print(f"Error parsing GPU info for partition {partition_name}: {e}")
            
            return None
            
        except subprocess.CalledProcessError as e:
            print(f"Error getting GPU info for partition {partition_name}: {e}")
            return None
        except Exception as e:
            print(f"Unexpected error getting GPU info: {e}")
            return None

def main():
    # Check if SLURM commands are available
    try:
        result = subprocess.run(
            ["sinfo", "--version"],
            capture_output=True,
            text=True,
            check=False  # Don't raise exception, we'll handle it
        )
        if result.returncode != 0:
            print("Warning: SLURM commands may not be available.")
            print(f"sinfo test returned: {result.stderr}")
    except FileNotFoundError:
        print("Warning: SLURM commands are not found in PATH.")
        print("The application will still run, but partition information cannot be retrieved.")
    
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main() 