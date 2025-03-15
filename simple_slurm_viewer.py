#!/usr/bin/env python3
import sys
import subprocess
from PyQt5.QtWidgets import (QApplication, QMainWindow, QFrame, QLabel, 
                            QGridLayout, QVBoxLayout, QScrollArea, QWidget)
from PyQt5.QtGui import QIcon, QPixmap, QPainter, QColor, QBrush, QPen
from PyQt5.QtCore import Qt, QSize, QRect

class PartitionIcon(QFrame):
    """Simple widget to display a SLURM partition"""
    
    def __init__(self, text, node_count=0, parent=None):
        super().__init__(parent)
        
        # Check if this is a default partition (ends with *)
        self.is_default = text.endswith('*')
        
        # Remove the asterisk for display purposes
        if self.is_default:
            self.partition_name = text[:-1]  # Remove the asterisk
        else:
            self.partition_name = text
            
        self.node_count = node_count
        
        # Set fixed size for the icon
        self.setFixedSize(140, 140)
        
        # Set style for the frame
        self.setFrameStyle(QFrame.Box | QFrame.Raised)
        self.setLineWidth(1)
        
        # Create a layout for this widget
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        
        # Create label for the partition name
        self.name_label = QLabel(self.partition_name)
        self.name_label.setAlignment(Qt.AlignCenter)
        
        # Set special style for default partition
        if self.is_default:
            self.name_label.setStyleSheet("font-weight: bold; font-size: 14px; color: #2980b9;")
            # Set special background for default partition
            self.setStyleSheet("background-color: #d5e8f8; border: 2px solid #2980b9;")
        else:
            self.name_label.setStyleSheet("font-weight: bold; font-size: 14px;")
            self.setStyleSheet("background-color: #f0f0f0;")
        
        # Create label for the icon
        self.icon_label = QLabel()
        self.icon_label.setAlignment(Qt.AlignCenter)
        
        # Try to load the queue.png icon
        icon = QIcon("queue.png")
        pixmap = icon.pixmap(QSize(48, 48))
        
        # Check if the pixmap is valid/non-empty
        if not pixmap.isNull() and pixmap.width() > 0:
            self.icon_label.setPixmap(pixmap)
        else:
            print("Warning: Could not load queue.png icon: File not found or invalid")
            # Fallback to text if icon can't be loaded
            self.icon_label.setText("🖥️")
            self.icon_label.setStyleSheet("font-size: 32px;")
        
        # Create label for node count
        self.node_count_label = QLabel(f"{node_count} nodes")
        self.node_count_label.setAlignment(Qt.AlignCenter)
        
        # Create label for default indicator if this is a default partition
        if self.is_default:
            default_label = QLabel("DEFAULT")
            default_label.setAlignment(Qt.AlignCenter)
            default_label.setStyleSheet("color: #2980b9; font-weight: bold; font-size: 10px;")
            layout.addWidget(default_label)
        
        # Add widgets to layout
        layout.addWidget(self.icon_label)
        layout.addWidget(self.name_label)
        layout.addWidget(self.node_count_label)
        
        # Set the background color
        self.setStyleSheet("background-color: #f0f0f0;")

    def update_node_count(self, count):
        """Update the node count display"""
        self.node_count = count
        self.node_count_label.setText(f"{count} nodes")

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # Set window properties
        self.setWindowTitle("SLURM Partitions")
        self.setMinimumSize(800, 600)
        
        # Try to set the window icon
        icon = QIcon("queue.png")
        if not icon.isNull():
            self.setWindowIcon(icon)
        else:
            print("Warning: Could not set window icon: File not found or invalid")
        
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
        self.grid_layout.setSpacing(10)
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
                            partitions.append((partition_name, node_count))
                    except (ValueError, IndexError) as e:
                        print(f"Error parsing partition info: {e} for line: {line}")
            
            # Sort partitions alphabetically, but put default partitions first
            partitions.sort(key=lambda x: (not x[0].endswith('*'), x[0].rstrip('*').lower()))
            
            # Create and place partition icons in the grid
            for i, (partition_name, node_count) in enumerate(partitions):
                row = i // 4  # 4 icons per row
                col = i % 4
                
                partition_icon = PartitionIcon(partition_name, node_count)
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