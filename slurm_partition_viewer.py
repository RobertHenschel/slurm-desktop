#!/usr/bin/env python3
import sys
import subprocess
import os
import re
import datetime
import threading
import time
import json
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, # type: ignore
                           QLabel, QGridLayout, QFrame, QStyle, QMenu, QAction,
                           QDialog, QPushButton, QSlider, QSpinBox, QDialogButtonBox, QGroupBox, QMessageBox,
                           QTableWidget, QTableWidgetItem, QHeaderView, QTextEdit, QComboBox)
from PyQt5.QtCore import Qt, QSize, QRect, QPoint, QTimer, QSettings, QDateTime, pyqtSignal # type: ignore
from PyQt5.QtGui import QIcon, QPixmap, QPainter, QColor, QFont, QPen, QBrush, QCursor, QPolygon, QTextCursor # type: ignore

class NodeCountBadge(QLabel):
    def __init__(self, count, parent=None):
        super().__init__(parent)
        self.count = count
        self.setFixedSize(28, 28)
        self.setAlignment(Qt.AlignCenter)
        # Make the label transparent
        self.setAttribute(Qt.WA_TranslucentBackground)
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Draw circle
        painter.setPen(QPen(QColor("#2c3e50"), 1))
        painter.setBrush(QBrush(QColor("#3498db")))
        painter.drawEllipse(2, 2, 24, 24)
        
        # Draw text
        painter.setPen(QColor("white"))
        painter.setFont(QFont("Arial", 10, QFont.Bold))
        painter.drawText(QRect(2, 2, 24, 24), Qt.AlignCenter, str(self.count))
        
        painter.end()

class JobStatusBadge(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(24, 24)
        self.setAlignment(Qt.AlignCenter)
        # Make the label transparent
        self.setAttribute(Qt.WA_TranslucentBackground)
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Draw green circle
        painter.setPen(QPen(QColor("#1e8449"), 1))
        painter.setBrush(QBrush(QColor("#2ecc71")))
        painter.drawEllipse(2, 2, 20, 20)
        
        # Draw play triangle
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(QColor("white")))
        
        # Create a triangle (play symbol)
        triangle = QPolygon()
        triangle.append(QPoint(8, 6))    # Left point
        triangle.append(QPoint(18, 12))  # Right point
        triangle.append(QPoint(8, 18))   # Bottom point
        
        painter.drawPolygon(triangle)
        painter.end()

class TimeSelectionDialog(QDialog):
    def __init__(self, partition_name, parent=None):
        super().__init__(parent)
        self.partition_name = partition_name
        self.setWindowTitle(f"Interactive Job - {partition_name}")
        self.setMinimumWidth(450)
        
        # Get partition information
        self.max_hours = self.get_max_walltime(partition_name)
        self.max_cpus = self.get_max_cpus_per_node(partition_name)
        self.max_memory = self.get_max_memory_per_node(partition_name)
        self.gpu_info = self.get_gpu_info(partition_name)
        
        # Determine granularity based on max walltime
        self.use_minutes = self.max_hours <= 4
        
        # Create layout
        layout = QVBoxLayout(self)
        
        # Add info label
        info_label = QLabel(f"Configure interactive job for partition: <b>{partition_name}</b>")
        layout.addWidget(info_label)
        
        # Add time selection widgets
        time_group = QGroupBox("Time Limit")
        time_layout = QVBoxLayout(time_group)
        
        if self.use_minutes:
            # For short walltimes (≤ 4 hours), use minutes with 15-minute granularity
            slider_layout = QHBoxLayout()
            time_label = QLabel("Walltime:")
            self.time_slider = QSlider(Qt.Horizontal)
            self.time_slider.setMinimum(15)  # 15 minutes minimum
            self.time_slider.setMaximum(self.max_hours * 60)  # Convert hours to minutes
            self.time_slider.setValue(60)  # Default to 1 hour
            self.time_slider.setTickPosition(QSlider.TicksBelow)
            self.time_slider.setTickInterval(15)  # 15-minute intervals
            self.time_slider.setSingleStep(15)  # 15-minute steps
            
            slider_layout.addWidget(time_label)
            slider_layout.addWidget(self.time_slider)
            time_layout.addLayout(slider_layout)
            
            # Create a custom spinbox for hours and minutes
            spinbox_layout = QHBoxLayout()
            
            self.hours_spinbox = QSpinBox()
            self.hours_spinbox.setMinimum(0)
            self.hours_spinbox.setMaximum(self.max_hours)
            self.hours_spinbox.setValue(1)  # Default to 1 hour
            
            self.minutes_spinbox = QSpinBox()
            self.minutes_spinbox.setMinimum(0)
            self.minutes_spinbox.setMaximum(45)  # 0, 15, 30, 45 minutes
            self.minutes_spinbox.setValue(0)  # Default to 0 minutes
            self.minutes_spinbox.setSingleStep(15)  # 15-minute steps
            
            spinbox_layout.addWidget(self.hours_spinbox)
            spinbox_layout.addWidget(QLabel("hours"))
            spinbox_layout.addWidget(self.minutes_spinbox)
            spinbox_layout.addWidget(QLabel("minutes"))
            spinbox_layout.addStretch()
            time_layout.addLayout(spinbox_layout)
            
            # Connect slider and spinboxes
            self.time_slider.valueChanged.connect(self.slider_to_spinboxes)
            self.hours_spinbox.valueChanged.connect(self.spinboxes_to_slider)
            self.minutes_spinbox.valueChanged.connect(self.spinboxes_to_slider)
            
            # Add max time info with minutes
            max_time_text = f"Maximum allowed walltime: {self.max_hours} hour"
            if self.max_hours != 1:
                max_time_text += "s"
            max_time_label = QLabel(max_time_text)
            time_layout.addWidget(max_time_label)
        else:
            # For longer walltimes (> 4 hours), use hours with 1-hour granularity
            slider_layout = QHBoxLayout()
            time_label = QLabel("Walltime (hours):")
            self.time_slider = QSlider(Qt.Horizontal)
            self.time_slider.setMinimum(1)
            self.time_slider.setMaximum(self.max_hours)
            self.time_slider.setValue(4)  # Default to 4 hours
            self.time_slider.setTickPosition(QSlider.TicksBelow)
            self.time_slider.setTickInterval(max(1, self.max_hours // 10))
            
            slider_layout.addWidget(time_label)
            slider_layout.addWidget(self.time_slider)
            time_layout.addLayout(slider_layout)
            
            spinbox_layout = QHBoxLayout()
            self.hours_spinbox = QSpinBox()
            self.hours_spinbox.setMinimum(1)
            self.hours_spinbox.setMaximum(self.max_hours)
            self.hours_spinbox.setValue(4)  # Default to 4 hours
            
            spinbox_layout.addWidget(self.hours_spinbox)
            spinbox_layout.addWidget(QLabel("hours"))
            spinbox_layout.addStretch()
            time_layout.addLayout(spinbox_layout)
            
            # Connect slider and spinbox
            self.time_slider.valueChanged.connect(self.hours_spinbox.setValue)
            self.hours_spinbox.valueChanged.connect(self.time_slider.setValue)
            
            # Add max time info
            max_time_label = QLabel(f"Maximum allowed walltime: {self.max_hours} hours")
            time_layout.addWidget(max_time_label)
        
        layout.addWidget(time_group)
        
        # Add CPU selection widgets
        cpu_group = QGroupBox("CPU Resources")
        cpu_layout = QVBoxLayout(cpu_group)
        
        # CPU slider
        cpu_slider_layout = QHBoxLayout()
        cpu_label = QLabel("CPUs per task:")
        self.cpu_slider = QSlider(Qt.Horizontal)
        self.cpu_slider.setMinimum(1)
        self.cpu_slider.setMaximum(self.max_cpus)
        self.cpu_slider.setValue(8)  # Default to 8 CPUs
        self.cpu_slider.setTickPosition(QSlider.TicksBelow)
        self.cpu_slider.setTickInterval(max(1, self.max_cpus // 10))
        
        cpu_slider_layout.addWidget(cpu_label)
        cpu_slider_layout.addWidget(self.cpu_slider)
        cpu_layout.addLayout(cpu_slider_layout)
        
        # CPU spinbox
        cpu_spinbox_layout = QHBoxLayout()
        self.cpu_spinbox = QSpinBox()
        self.cpu_spinbox.setMinimum(1)
        self.cpu_spinbox.setMaximum(self.max_cpus)
        self.cpu_spinbox.setValue(8)  # Default to 8 CPUs
        
        cpu_spinbox_layout.addWidget(self.cpu_spinbox)
        cpu_spinbox_layout.addWidget(QLabel("CPUs"))
        cpu_spinbox_layout.addStretch()
        cpu_layout.addLayout(cpu_spinbox_layout)
        
        # Connect CPU slider and spinbox
        self.cpu_slider.valueChanged.connect(self.cpu_spinbox.setValue)
        self.cpu_spinbox.valueChanged.connect(self.cpu_slider.setValue)
        
        # Add max CPU info
        max_cpu_label = QLabel(f"Maximum CPUs per node: {self.max_cpus}")
        cpu_layout.addWidget(max_cpu_label)
        
        layout.addWidget(cpu_group)
        
        # Add Memory selection widgets
        memory_group = QGroupBox("Memory Resources")
        memory_layout = QVBoxLayout(memory_group)
        
        # Memory slider
        memory_slider_layout = QHBoxLayout()
        memory_label = QLabel("Memory:")
        self.memory_slider = QSlider(Qt.Horizontal)
        self.memory_slider.setMinimum(1)
        self.memory_slider.setMaximum(self.max_memory)
        self.memory_slider.setValue(32)  # Default to 32 GB
        self.memory_slider.setTickPosition(QSlider.TicksBelow)
        self.memory_slider.setTickInterval(max(1, self.max_memory // 10))
        
        memory_slider_layout.addWidget(memory_label)
        memory_slider_layout.addWidget(self.memory_slider)
        memory_layout.addLayout(memory_slider_layout)
        
        # Memory spinbox
        memory_spinbox_layout = QHBoxLayout()
        self.memory_spinbox = QSpinBox()
        self.memory_spinbox.setMinimum(1)
        self.memory_spinbox.setMaximum(self.max_memory)
        self.memory_spinbox.setValue(32)  # Default to 32 GB
        
        memory_spinbox_layout.addWidget(self.memory_spinbox)
        memory_spinbox_layout.addWidget(QLabel("GB"))
        memory_spinbox_layout.addStretch()
        memory_layout.addLayout(memory_spinbox_layout)
        
        # Connect Memory slider and spinbox
        self.memory_slider.valueChanged.connect(self.memory_spinbox.setValue)
        self.memory_spinbox.valueChanged.connect(self.memory_slider.setValue)
        
        # Add max memory info
        max_memory_label = QLabel(f"Maximum memory per node: {self.max_memory} GB")
        memory_layout.addWidget(max_memory_label)
        
        layout.addWidget(memory_group)

        # Add GPU selection widgets if GPUs are available
        if self.gpu_info:
            gpu_group = QGroupBox("GPU Resources")
            gpu_layout = QVBoxLayout(gpu_group)
            
            # GPU type info
            gpu_type_label = QLabel(f"GPU Type: {self.gpu_info['type']}")
            gpu_layout.addWidget(gpu_type_label)
            
            # GPU count slider
            gpu_slider_layout = QHBoxLayout()
            gpu_label = QLabel("Number of GPUs:")
            self.gpu_slider = QSlider(Qt.Horizontal)
            self.gpu_slider.setMinimum(1)
            self.gpu_slider.setMaximum(self.gpu_info['count'])
            self.gpu_slider.setValue(1)  # Default to 1 GPU
            self.gpu_slider.setTickPosition(QSlider.TicksBelow)
            self.gpu_slider.setTickInterval(1)
            
            gpu_slider_layout.addWidget(gpu_label)
            gpu_slider_layout.addWidget(self.gpu_slider)
            gpu_layout.addLayout(gpu_slider_layout)
            
            # GPU spinbox
            gpu_spinbox_layout = QHBoxLayout()
            self.gpu_spinbox = QSpinBox()
            self.gpu_spinbox.setMinimum(1)
            self.gpu_spinbox.setMaximum(self.gpu_info['count'])
            self.gpu_spinbox.setValue(1)  # Default to 1 GPU
            
            gpu_spinbox_layout.addWidget(self.gpu_spinbox)
            gpu_spinbox_layout.addWidget(QLabel("GPUs"))
            gpu_spinbox_layout.addStretch()
            gpu_layout.addLayout(gpu_spinbox_layout)
            
            # Connect GPU slider and spinbox
            self.gpu_slider.valueChanged.connect(self.gpu_spinbox.setValue)
            self.gpu_spinbox.valueChanged.connect(self.gpu_slider.setValue)
            
            # Add max GPU info
            max_gpu_label = QLabel(f"Maximum GPUs per node: {self.gpu_info['count']}")
            gpu_layout.addWidget(max_gpu_label)
            
            layout.addWidget(gpu_group)
        
        # Add buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
    
    def slider_to_spinboxes(self, value):
        # Convert slider value (in minutes) to hours and minutes
        hours = value // 60
        minutes = value % 60
        # Round minutes to nearest 15
        minutes = round(minutes / 15) * 15
        if minutes == 60:
            hours += 1
            minutes = 0
            
        # Update spinboxes without triggering their signals
        self.hours_spinbox.blockSignals(True)
        self.minutes_spinbox.blockSignals(True)
        self.hours_spinbox.setValue(hours)
        self.minutes_spinbox.setValue(minutes)
        self.hours_spinbox.blockSignals(False)
        self.minutes_spinbox.blockSignals(False)
    
    def spinboxes_to_slider(self):
        # Convert hours and minutes to slider value (in minutes)
        if self.use_minutes:
            total_minutes = self.hours_spinbox.value() * 60 + self.minutes_spinbox.value()
            # Update slider without triggering its signal
            self.time_slider.blockSignals(True)
            self.time_slider.setValue(total_minutes)
            self.time_slider.blockSignals(False)
    
    def get_max_walltime(self, partition_name):
        # Try to get the actual max walltime from SLURM
        try:
            result = subprocess.run(
                ['sinfo', '-p', partition_name, '--format=%l', '-h'],
                capture_output=True, text=True
            )
            time_limit = result.stdout.strip()
            
            # Parse the time limit (format could be "1-00:00:00" for 1 day, "2:00:00" for 2 hours, etc.)
            if time_limit == "infinite" or time_limit == "":
                return 72  # Default to 72 hours if infinite or not specified
            
            hours = 0
            if "-" in time_limit:  # Format: days-hours:minutes:seconds
                days, time_part = time_limit.split("-")
                hours += int(days) * 24
                time_parts = time_part.split(":")
                if len(time_parts) >= 1:
                    hours += int(time_parts[0])
            else:  # Format: hours:minutes:seconds
                time_parts = time_limit.split(":")
                if len(time_parts) >= 1:
                    hours += int(time_parts[0])
            
            return max(1, hours)  # Ensure at least 1 hour
        except Exception as e:
            print(f"Error getting max walltime: {e}")
            return 24  # Default to 24 hours if there's an error
    
    def get_max_cpus_per_node(self, partition_name):
        # Try to get the max CPUs per node from SLURM
        try:
            # Get CPU count for nodes in this partition
            result = subprocess.run(
                ['sinfo', '-p', partition_name, '--format=%c', '-h'],
                capture_output=True, text=True
            )
            cpu_count = result.stdout.strip()
            
            # Parse the CPU count
            try:
                return max(1, int(cpu_count))  # Ensure at least 1 CPU
            except ValueError:
                # If we can't parse the CPU count, try another approach
                # Get node list for the partition
                result = subprocess.run(
                    ['sinfo', '-p', partition_name, '--format=%N', '-h'],
                    capture_output=True, text=True
                )
                node_list = result.stdout.strip().split(',')[0]  # Take the first node
                
                # Get CPU count for this node
                if node_list:
                    result = subprocess.run(
                        ['scontrol', 'show', 'node', node_list, '-o'],
                        capture_output=True, text=True
                    )
                    node_info = result.stdout.strip()
                    
                    # Extract CPU count from node info
                    import re
                    cpu_match = re.search(r'CPUTot=(\d+)', node_info)
                    if cpu_match:
                        return max(1, int(cpu_match.group(1)))
            
            # If all else fails, return a reasonable default
            return 32
        except Exception as e:
            print(f"Error getting max CPUs per node: {e}")
            return 32  # Default to 32 CPUs if there's an error
    
    def get_max_memory_per_node(self, partition_name):
        # Try to get the max memory per node from SLURM
        try:
            # Get node list for the partition
            result = subprocess.run(
                ['sinfo', '-p', partition_name, '--format=%N', '-h'],
                capture_output=True, text=True
            )
            node_list = result.stdout.strip().split(',')[0]  # Take the first node
            
            # If we have a node, get its memory
            if node_list:
                result = subprocess.run(
                    ['scontrol', 'show', 'node', node_list, '-o'],
                    capture_output=True, text=True
                )
                node_info = result.stdout.strip()
                
                # Extract memory from node info
                import re
                # Look for RealMemory which is in MB
                memory_match = re.search(r'RealMemory=(\d+)', node_info)
                if memory_match:
                    # Convert MB to GB and round up
                    memory_mb = int(memory_match.group(1))
                    memory_gb = (memory_mb + 1023) // 1024  # Round up to nearest GB
                    return max(1, memory_gb)
                
                # Alternative: look for Memory which might be in format like "32000M"
                memory_match = re.search(r'Memory=(\d+)([MG])', node_info)
                if memory_match:
                    memory_val = int(memory_match.group(1))
                    memory_unit = memory_match.group(2)
                    if memory_unit == 'M':
                        memory_gb = (memory_val + 1023) // 1024  # Convert MB to GB and round up
                    else:  # 'G'
                        memory_gb = memory_val
                    return max(1, memory_gb)
            
            # If we couldn't get memory info, try another approach
            # Get memory info from sinfo
            result = subprocess.run(
                ['sinfo', '-p', partition_name, '--format=%m', '-h'],
                capture_output=True, text=True
            )
            memory_info = result.stdout.strip()
            
            # Try to parse memory info (could be in format like "32000M" or "32G")
            if memory_info:
                memory_match = re.search(r'(\d+)([MG])?', memory_info)
                if memory_match:
                    memory_val = int(memory_match.group(1))
                    memory_unit = memory_match.group(2) if memory_match.group(2) else 'M'
                    if memory_unit == 'M':
                        memory_gb = (memory_val + 1023) // 1024  # Convert MB to GB and round up
                    else:  # 'G'
                        memory_gb = memory_val
                    return max(1, memory_gb)
            
            # If all else fails, return a reasonable default
            return 128
        except Exception as e:
            print(f"Error getting max memory per node: {e}")
            return 128  # Default to 128 GB if there's an error
    
    def get_selected_time(self):
        if self.use_minutes:
            hours = self.hours_spinbox.value()
            minutes = self.minutes_spinbox.value()
            return f"{hours}:{minutes:02d}:00"  # Format as HH:MM:00
        else:
            hours = self.hours_spinbox.value()
            return f"{hours}:00:00"  # Format as HH:00:00
    
    def get_selected_cpus(self):
        return self.cpu_spinbox.value()
    
    def get_selected_memory(self):
        return self.memory_spinbox.value()

    def get_gpu_info(self, partition_name):
        """Get GPU information for the partition."""
        try:
            # Get GRES (Generic Resource) info for the partition
            result = subprocess.run(
                ['sinfo', '-p', partition_name, '--format=%G', '-h'],
                capture_output=True, text=True
            )
            gres_info = result.stdout.strip()
            
            # Check if there are GPUs
            if gres_info == '(null)' or not gres_info:
                return None
            
            # Parse GPU information (format: gpu:type:count)
            gpu_match = re.match(r'gpu:([^:]+):(\d+)', gres_info)
            if gpu_match:
                return {
                    'type': gpu_match.group(1).upper(),  # e.g., 'V100', 'H100'
                    'count': int(gpu_match.group(2))
                }
            
            return None
            
        except Exception as e:
            print(f"Error getting GPU information: {e}")
            return None

    def get_selected_gpus(self):
        """Get the number of GPUs selected by the user."""
        if hasattr(self, 'gpu_spinbox'):
            return self.gpu_spinbox.value()
        return None

class FileViewerWindow(QMainWindow):
    """Window for viewing job output/error files with tail -f functionality."""
    
    # Define a custom signal for updating text
    update_text_signal = pyqtSignal(str)
    
    def __init__(self, job_id, file_type, file_path, parent=None):
        super().__init__(parent)
        self.job_id = job_id
        self.file_type = file_type
        self.file_path = file_path
        self.running = True
        
        # Set window properties
        self.setWindowTitle(f"Job {job_id} - {file_type.upper()} File")
        self.setGeometry(200, 200, 800, 600)
        
        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Create header label
        header_label = QLabel(f"Viewing {file_type.upper()} file for job <b>{job_id}</b>")
        header_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(header_label)
        
        # Create path label
        path_label = QLabel(f"File path: {file_path}")
        layout.addWidget(path_label)
        
        # Create text display
        self.text_display = QTextEdit()
        self.text_display.setReadOnly(True)
        self.text_display.setLineWrapMode(QTextEdit.NoWrap)
        self.text_display.setFont(QFont("Monospace", 10))
        layout.addWidget(self.text_display)
        
        # Connect the update signal to the update slot
        self.update_text_signal.connect(self.update_text_slot)
        
        # Start monitoring thread
        self.monitor_thread = threading.Thread(target=self.monitor_file)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()
    
    def closeEvent(self, event):
        """Stop the monitoring thread when the window is closed."""
        self.running = False
        super().closeEvent(event)
    
    def monitor_file(self):
        """Monitor the file for changes (similar to tail -f)."""
        try:
            # Check if file exists
            if not os.path.exists(self.file_path):
                self.update_text_signal.emit("Waiting for file to be created...\n")
            
            # Keep track of file size
            last_size = 0
            
            # Monitor loop
            while self.running:
                if os.path.exists(self.file_path):
                    current_size = os.path.getsize(self.file_path)
                    
                    # If file size has changed
                    if current_size > last_size:
                        with open(self.file_path, 'r') as f:
                            # Seek to the last position we read
                            f.seek(last_size)
                            # Read new content
                            new_content = f.read()
                            # Update display
                            self.update_text_signal.emit(new_content)
                        
                        # Update last size
                        last_size = current_size
                
                # Sleep to avoid high CPU usage
                time.sleep(1)
                
        except Exception as e:
            self.update_text_signal.emit(f"\nError monitoring file: {str(e)}\n")
    
    def update_text_slot(self, text):
        """Update the text display (thread-safe slot)."""
        cursor = self.text_display.textCursor()
        cursor.movePosition(QTextCursor.End)
        cursor.insertText(text)
        self.text_display.setTextCursor(cursor)
        self.text_display.ensureCursorVisible()

class JobHistoryWindow(QMainWindow):
    def __init__(self, partition_name, parent=None):
        super().__init__(parent)
        self.partition_name = partition_name
        self.setWindowTitle(f"Job History - {partition_name}")
        
        # Create settings object
        self.settings = QSettings("SLURM", "PartitionViewer")
        
        # Restore window geometry from settings
        settings_key = f"jobHistoryGeometry_{partition_name}"
        self.restoreGeometry(self.settings.value(settings_key, b""))
        
        # If no saved geometry, use default
        if not self.size().isValid():
            self.setGeometry(150, 150, 1000, 600)
        
        # Store references to file viewer windows
        self.file_viewers = {}
        
        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Create toolbar with refresh button
        toolbar = self.addToolBar("Tools")
        refresh_action = QAction(QIcon.fromTheme("view-refresh") or 
                               self.style().standardIcon(QStyle.SP_BrowserReload), 
                               "Refresh", self)
        refresh_action.triggered.connect(self.refresh_data)
        toolbar.addAction(refresh_action)
        
        # Create header label
        header_label = QLabel(f"Your jobs in partition <b>{partition_name}</b>")
        header_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(header_label)
        
        # Create queued jobs section
        queued_group = QGroupBox("Queued/Running Jobs")
        queued_layout = QVBoxLayout(queued_group)
        
        # Create queued jobs table
        self.queued_table = QTableWidget()
        self.queued_table.setColumnCount(7)
        self.queued_table.setHorizontalHeaderLabels([
            "Job ID", "Job Name", "State", "Start Time", "CPUs", "Memory", "Time Limit"
        ])
        
        # Set queued table properties
        self.queued_table.setAlternatingRowColors(True)
        self.queued_table.setEditTriggers(QTableWidget.NoEditTriggers)  # Read-only
        self.queued_table.setSortingEnabled(True)
        self.queued_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        
        # Enable context menu for queued table
        self.queued_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.queued_table.customContextMenuRequested.connect(self.show_queued_context_menu)
        
        queued_layout.addWidget(self.queued_table)
        layout.addWidget(queued_group, 1)  # 1 = stretch factor
        
        # Create completed jobs section
        completed_group = QGroupBox("Completed Jobs (Last 30 Days)")
        completed_group.setObjectName("completed_jobs_group")
        completed_layout = QVBoxLayout(completed_group)
        
        # Create completed jobs table
        self.completed_table = QTableWidget()
        self.completed_table.setObjectName("completed_table")
        self.completed_table.setColumnCount(8)
        self.completed_table.setHorizontalHeaderLabels([
            "Job ID", "Job Name", "State", "Start Time", "End Time", 
            "CPUs", "Memory", "Runtime"
        ])
        
        # Set completed table properties
        self.completed_table.setAlternatingRowColors(True)
        self.completed_table.setEditTriggers(QTableWidget.NoEditTriggers)  # Read-only
        self.completed_table.setSortingEnabled(True)
        self.completed_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        
        completed_layout.addWidget(self.completed_table)
        layout.addWidget(completed_group, 3)  # 3 = stretch factor (3x size of queued table)
        
        # Load job data
        self.load_job_data()
    
    def closeEvent(self, event):
        """Save window geometry before closing."""
        settings_key = f"jobHistoryGeometry_{self.partition_name}"
        self.settings.setValue(settings_key, self.saveGeometry())
        
        # Close any file viewers
        for viewer in self.file_viewers.values():
            if viewer.isVisible():
                viewer.close()
        
        super().closeEvent(event)
    
    def show_queued_context_menu(self, position):
        """Show context menu for the selected job in the queued table."""
        # Get the row under the cursor
        row = self.queued_table.rowAt(position.y())
        if row < 0:
            return
        
        # Get job ID from the selected row
        job_id_item = self.queued_table.item(row, 0)
        if not job_id_item:
            return
            
        job_id = job_id_item.text()
        
        # Get job state from the selected row
        job_state_item = self.queued_table.item(row, 2)
        job_state = job_state_item.text() if job_state_item else ""
        
        # Create context menu
        menu = QMenu()
        
        # Add actions
        view_output_action = QAction("View Output File", self)
        view_output_action.triggered.connect(lambda: self.view_job_file(job_id, "out"))
        menu.addAction(view_output_action)
        
        view_error_action = QAction("View Error File", self)
        view_error_action.triggered.connect(lambda: self.view_job_file(job_id, "err"))
        menu.addAction(view_error_action)
        
        # Add separator
        menu.addSeparator()
        
        # Add cancel job action
        cancel_job_action = QAction("Cancel Job", self)
        cancel_job_action.triggered.connect(lambda: self.cancel_job(job_id))
        # Set icon if available
        cancel_icon = QIcon.fromTheme("process-stop") or self.style().standardIcon(QStyle.SP_DialogCancelButton)
        if not cancel_icon.isNull():
            cancel_job_action.setIcon(cancel_icon)
        menu.addAction(cancel_job_action)
        
        # Show the menu at the cursor position
        menu.exec_(self.queued_table.viewport().mapToGlobal(position))
    
    def cancel_job(self, job_id):
        """Cancel a SLURM job."""
        try:
            # Ask for confirmation
            reply = QMessageBox.question(
                self, 
                "Cancel Job", 
                f"Are you sure you want to cancel job {job_id}?",
                QMessageBox.Yes | QMessageBox.No, 
                QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                # Run scancel command
                result = subprocess.run(
                    ['scancel', job_id],
                    capture_output=True, text=True
                )
                
                if result.returncode == 0:
                    QMessageBox.information(self, "Job Cancelled", f"Job {job_id} has been cancelled.")
                    # Refresh the job list
                    self.refresh_data()
                else:
                    error_msg = result.stderr.strip() if result.stderr else "Unknown error"
                    QMessageBox.warning(self, "Error", f"Error cancelling job {job_id}: {error_msg}")
        
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error cancelling job: {str(e)}")
            print(f"Error cancelling job: {e}")
    
    def view_job_file(self, job_id, file_type):
        """Open a window to view the job output or error file with tail -f functionality."""
        try:
            # Get the job's details
            print(f"Finding {file_type} file for job {job_id}...")
            
            result = subprocess.run(
                ['scontrol', 'show', 'job', job_id],
                capture_output=True, text=True
            )
            
            # Log the scontrol output for debugging
            print(f"scontrol output: {result.stdout}")
            
            # First, try to get the custom output/error file path from scontrol output
            file_path = None
            
            if file_type == "out":
                # Look for StdOut in scontrol output
                stdout_match = re.search(r'StdOut=([^\s]+)', result.stdout)
                if stdout_match and stdout_match.group(1) != "StdOut":
                    file_path = stdout_match.group(1)
                    print(f"Found custom output file path in StdOut: {file_path}")
            else:  # err
                # Look for StdErr in scontrol output
                stderr_match = re.search(r'StdErr=([^\s]+)', result.stdout)
                if stderr_match and stderr_match.group(1) != "StdErr":
                    file_path = stderr_match.group(1)
                    print(f"Found custom error file path in StdErr: {file_path}")
            
            # If no custom path found, use the default path
            if not file_path or file_path == "(null)":
                # Extract working directory from scontrol output
                work_dir_match = re.search(r'WorkDir=([^\s]+)', result.stdout)
                if not work_dir_match:
                    print(f"Could not find WorkDir in scontrol output")
                    QMessageBox.warning(self, "File Not Found", 
                                       f"Could not determine working directory for job {job_id}")
                    return
                
                work_dir = work_dir_match.group(1)
                print(f"Found working directory: {work_dir}")
                
                # Construct default file path
                if file_type == "out":
                    file_path = os.path.join(work_dir, f"slurm-{job_id}.out")
                    print(f"Using default output file path: {file_path}")
                else:  # err
                    file_path = os.path.join(work_dir, f"slurm-{job_id}.err")
                    print(f"Using default error file path: {file_path}")
            
            print(f"Looking for file at: {file_path}")
            
            # Create a unique key for this viewer
            viewer_key = f"{job_id}_{file_type}"
            
            # Check if we already have a viewer open for this file
            if viewer_key in self.file_viewers and self.file_viewers[viewer_key].isVisible():
                # Bring existing viewer to front
                self.file_viewers[viewer_key].raise_()
                self.file_viewers[viewer_key].activateWindow()
            else:
                # Create new viewer
                viewer = FileViewerWindow(job_id, file_type, file_path, self)
                viewer.show()
                
                # Store reference to prevent garbage collection
                self.file_viewers[viewer_key] = viewer
            
        except Exception as e:
            print(f"Error opening file viewer: {e}")
            QMessageBox.critical(self, "Error", f"Error opening file viewer: {str(e)}")
    
    def refresh_data(self):
        """Refresh job data."""
        # Refresh queued jobs
        self.load_queued_jobs()
        
        # For completed jobs, completely recreate the table
        self.recreate_completed_table()
    
    def recreate_completed_table(self):
        """Completely recreate the completed jobs table to ensure a clean refresh."""
        # Get the parent layout
        completed_group = self.findChild(QGroupBox, "completed_jobs_group")
        if not completed_group:
            print("Could not find completed jobs group")
            return
        
        # Remove the old table
        layout = completed_group.layout()
        if self.completed_table:
            layout.removeWidget(self.completed_table)
            self.completed_table.deleteLater()
        
        # Create a new table
        self.completed_table = QTableWidget()
        self.completed_table.setObjectName("completed_table")
        self.completed_table.setColumnCount(8)
        self.completed_table.setHorizontalHeaderLabels([
            "Job ID", "Job Name", "State", "Start Time", "End Time", 
            "CPUs", "Memory", "Runtime"
        ])
        
        # Set table properties
        self.completed_table.setAlternatingRowColors(True)
        self.completed_table.setEditTriggers(QTableWidget.NoEditTriggers)  # Read-only
        self.completed_table.setSortingEnabled(True)
        self.completed_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        
        # Add the new table to the layout
        layout.addWidget(self.completed_table)
        
        # Load the data
        self.load_completed_jobs()
    
    def load_job_data(self):
        """Load both queued and completed job data."""
        self.load_queued_jobs()
        self.load_completed_jobs()
    
    def load_queued_jobs(self):
        """Load queued and running jobs for the current user in the specified partition."""
        try:
            # Clear the table before loading new data
            self.queued_table.setRowCount(0)
            
            # Get current username
            username = os.environ.get('USER') or os.environ.get('USERNAME')
            if not username:
                try:
                    import pwd
                    username = pwd.getpwuid(os.getuid()).pw_name
                except (ImportError, AttributeError):
                    print("Could not determine username")
                    return
            
            # Run squeue command to get queued/running jobs
            # Format: JobID,Name,State,StartTime,NumCPUs,MinMemory,TimeLimit
            result = subprocess.run([
                'squeue', 
                '-u', username,
                '-p', self.partition_name,
                '--format=%i,%j,%T,%S,%C,%m,%l',
                '--noheader'
            ], capture_output=True, text=True)
            
            # Process the output
            job_data = []
            for line in result.stdout.strip().split('\n'):
                if line:
                    fields = line.split(',')
                    if len(fields) >= 7:
                        job_data.append(fields)
            
            # Populate the table
            self.queued_table.setRowCount(len(job_data))
            for row, job in enumerate(job_data):
                for col, value in enumerate(job[:7]):  # Only use the first 7 columns
                    self.queued_table.setItem(row, col, QTableWidgetItem(value))
            
            # Sort by job ID (descending)
            self.queued_table.sortItems(0, Qt.DescendingOrder)
            
        except Exception as e:
            print(f"Error loading queued jobs: {e}")
            # For testing in non-SLURM environments
            self.populate_dummy_queued_data()
    
    def load_completed_jobs(self):
        """Load completed jobs for the current user in the specified partition."""
        try:
            # Clear the table before loading new data
            self.completed_table.setRowCount(0)
            
            # Get current username
            username = os.environ.get('USER') or os.environ.get('USERNAME')
            if not username:
                try:
                    import pwd
                    username = pwd.getpwuid(os.getuid()).pw_name
                except (ImportError, AttributeError):
                    print("Could not determine username")
                    return
            
            # Calculate date 30 days ago
            thirty_days_ago = datetime.datetime.now() - datetime.timedelta(days=30)
            start_date = thirty_days_ago.strftime("%Y-%m-%d")
            
            # Run sacct command to get job history
            # Format: JobID,JobName,State,Start,End,NCPUS,ReqMem,Elapsed
            result = subprocess.run([
                'sacct', 
                '-u', username,
                '-r', self.partition_name,
                '-S', start_date,
                '--format=JobID,JobName,State,Start,End,NCPUS,ReqMem,Elapsed',
                '-P',  # Parsable output
                '--noheader'  # No header in output
            ], capture_output=True, text=True)
            
            # Process the output
            job_data = []
            for line in result.stdout.strip().split('\n'):
                if line and not line.isspace():
                    fields = line.split('|')
                    # Ensure we have at least 8 fields, padding with empty strings if necessary
                    while len(fields) < 8:
                        fields.append("")
                    
                    if not fields[0].endswith('.batch'):
                        # Only include completed jobs (not queued or running)
                        state = fields[2].upper()
                        if state in ['COMPLETED', 'FAILED', 'TIMEOUT', 'CANCELLED', 'NODE_FAIL']:
                            job_data.append(fields)
            
            # Populate the table
            if job_data:
                self.completed_table.setRowCount(len(job_data))
                for row, job in enumerate(job_data):
                    for col, value in enumerate(job[:8]):  # Only use the first 8 columns
                        item = QTableWidgetItem(value)
                        self.completed_table.setItem(row, col, item)
            
                # Sort by start time (descending)
                self.completed_table.sortItems(3, Qt.DescendingOrder)
        
        except Exception as e:
            print(f"Error loading completed jobs: {e}")
            # For testing in non-SLURM environments
            self.populate_dummy_completed_data()
    
    def populate_dummy_queued_data(self):
        """Populate the queued table with dummy data for testing."""
        dummy_data = [
            ["12350", "test_job6", "PENDING", "N/A", "4", "16G", "04:00:00"],
            ["12351", "test_job7", "RUNNING", "2023-05-06T09:30:00", "8", "32G", "08:00:00"],
            ["12352", "analysis2", "RUNNING", "2023-05-06T10:15:00", "16", "64G", "12:00:00"]
        ]
        
        self.queued_table.setRowCount(len(dummy_data))
        for row, job in enumerate(dummy_data):
            for col, value in enumerate(job):
                self.queued_table.setItem(row, col, QTableWidgetItem(value))
    
    def populate_dummy_completed_data(self):
        """Populate the completed table with dummy data for testing."""
        dummy_data = [
            ["12345", "test_job1", "COMPLETED", "2023-05-01T10:00:00", "2023-05-01T11:30:00", "4", "16G", "01:30:00"],
            ["12346", "test_job2", "FAILED", "2023-05-02T14:00:00", "2023-05-02T14:05:00", "8", "32G", "00:05:00"],
            ["12347", "analysis", "COMPLETED", "2023-05-03T09:00:00", "2023-05-03T15:00:00", "16", "64G", "06:00:00"],
            ["12348", "simulation", "TIMEOUT", "2023-05-04T08:00:00", "2023-05-04T12:00:00", "32", "128G", "04:00:00"],
            ["12349", "data_proc", "COMPLETED", "2023-05-05T13:00:00", "2023-05-05T14:30:00", "8", "16G", "01:30:00"]
        ]
        
        self.completed_table.setRowCount(len(dummy_data))
        for row, job in enumerate(dummy_data):
            for col, value in enumerate(job):
                self.completed_table.setItem(row, col, QTableWidgetItem(value))

class PartitionIcon(QFrame):
    def __init__(self, text, node_count=0, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.StyledPanel)
        self.setFrameShadow(QFrame.Raised)
        
        # Store partition name for context menu actions
        # Remove asterisk from partition name for SLURM commands
        self.display_name = text
        self.partition_name = text.rstrip('*')
        
        # Flag to track if user has jobs in this partition
        self.has_active_jobs = False
        
        # Create layout for the label
        layout = QVBoxLayout(self)
        
        # Create icon container (for positioning the badge)
        icon_container = QWidget()
        icon_container.setFixedSize(80, 80)
        icon_layout = QVBoxLayout(icon_container)
        icon_layout.setContentsMargins(0, 0, 0, 0)
        
        # Create icon label
        self.icon_label = QLabel()
        self.icon_label.setAlignment(Qt.AlignCenter)
        self.icon_label.setObjectName("iconLabel")
        # Prevent focus border
        self.icon_label.setFocusPolicy(Qt.NoFocus)
        
        # Use queue icon
        queue_icon = QIcon("queue.png")
        if not queue_icon.isNull():
            pixmap = queue_icon.pixmap(QSize(40, 40))
        else:
            # Fallback to a built-in style icon if queue.png is not available
            folder_icon = self.style().standardIcon(QStyle.SP_DirIcon)
            pixmap = folder_icon.pixmap(QSize(64, 64))
        
        self.icon_label.setPixmap(pixmap)
        icon_layout.addWidget(self.icon_label)
        
        # Add node count badge if count > 0
        if node_count > 0:
            self.badge = NodeCountBadge(node_count)
            # Position the badge at the top-right corner of the icon
            self.badge.setParent(icon_container)
            self.badge.move(52, 0)
        
        # Create job status badge (initially hidden)
        self.job_badge = JobStatusBadge()
        self.job_badge.setParent(icon_container)
        self.job_badge.move(52, 52)  # Position at bottom-right
        self.job_badge.setVisible(False)
        
        # Create text label
        self.text_label = QLabel(self.display_name)
        self.text_label.setAlignment(Qt.AlignCenter)
        self.text_label.setObjectName("textLabel")
        # Prevent focus border
        self.text_label.setFocusPolicy(Qt.NoFocus)
        
        # Add widgets to layout
        layout.addWidget(icon_container)
        layout.addWidget(self.text_label)
        
        # Set fixed size for the widget
        self.setFixedSize(120, 120)
        
        # Enable context menu
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)
        
        # Enable drag and drop
        self.setAcceptDrops(True)
        
        # Normal style (not highlighted)
        self.normal_style = """
            QFrame {
                background-color: #f5f5f5;
                border: 1px solid #ddd;
                border-radius: 8px;
            }
            QFrame:hover {
                background-color: #e0e0e0;
                border: 1px solid #aaa;
            }
            QLabel {
                background-color: transparent;
                border: none;
                outline: none;
            }
            QLabel:hover {
                border: none;
                outline: none;
                background-color: transparent;
            }
            #iconLabel, #textLabel {
                border: none;
                outline: none;
            }
            #iconLabel:hover, #textLabel:hover {
                border: none;
                outline: none;
                background-color: transparent;
            }
        """
        
        # Highlighted style (when dragging over)
        self.highlight_style = """
            QFrame {
                background-color: #d0e8f2;
                border: 2px solid #3498db;
                border-radius: 8px;
            }
            QLabel {
                background-color: transparent;
                border: none;
                outline: none;
            }
            #iconLabel, #textLabel {
                border: none;
                outline: none;
            }
        """
        
        # Set initial style
        self.setStyleSheet(self.normal_style)
        
        # Enable mouse tracking for double-click
        self.setMouseTracking(True)
    
    def update_job_status(self, has_jobs):
        """Update the job status badge visibility based on whether the user has jobs in this partition."""
        if has_jobs != self.has_active_jobs:
            self.has_active_jobs = has_jobs
            self.job_badge.setVisible(has_jobs)
    
    def dragEnterEvent(self, event):
        # Check if the drag contains URLs (files)
        if event.mimeData().hasUrls():
            # Check if at least one URL is a .sh file
            for url in event.mimeData().urls():
                file_path = url.toLocalFile()
                if file_path.endswith('.sh'):
                    # Highlight the partition icon
                    self.setStyleSheet(self.highlight_style)
                    event.accept()
                    return
        event.ignore()
    
    def dragLeaveEvent(self, event):
        # Reset the style when drag leaves
        self.setStyleSheet(self.normal_style)
        event.accept()
    
    def dragMoveEvent(self, event):
        # Same check as dragEnterEvent
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                file_path = url.toLocalFile()
                if file_path.endswith('.sh'):
                    event.accept()
                    return
        event.ignore()
    
    def dropEvent(self, event):
        # Reset the style
        self.setStyleSheet(self.normal_style)
        
        # Check if the drop contains URLs (files)
        if event.mimeData().hasUrls():
            # Filter for .sh files
            sh_files = []
            for url in event.mimeData().urls():
                file_path = url.toLocalFile()
                if file_path.endswith('.sh'):
                    sh_files.append(file_path)
            
            if sh_files:
                # Process each dropped .sh file
                for script_path in sh_files:
                    # Check if the script contains any #SBATCH lines
                    has_sbatch_directives = self.check_for_sbatch_directives(script_path)
                    
                    if has_sbatch_directives:
                        # If it has SBATCH directives, submit directly
                        self.submit_batch_job_direct(script_path)
                    else:
                        # If no SBATCH directives, show job configuration dialog
                        self.show_batch_job_dialog(script_path)
                
                # Accept the event
                event.accept()
                return
        
        event.ignore()

    def check_for_sbatch_directives(self, script_path):
        """Check if a script contains any #SBATCH directives."""
        try:
            with open(script_path, 'r') as f:
                content = f.read()
                return '#SBATCH' in content
        except Exception as e:
            print(f"Error checking script for SBATCH directives: {e}")
            return False

    def show_batch_job_dialog(self, script_path):
        """Show a dialog to configure batch job parameters."""
        # Create a dialog based on TimeSelectionDialog but with additional options
        dialog = BatchJobDialog(self.partition_name, script_path, self)
        if dialog.exec_() == QDialog.Accepted:
            # Get the parameters from the dialog
            time_limit = dialog.get_selected_time()
            cpus_per_task = dialog.get_selected_cpus()
            memory = dialog.get_selected_memory()
            nodes = dialog.get_selected_nodes()
            project = dialog.get_selected_project()
            
            # Submit the job with the selected parameters
            self.submit_batch_job_with_params(script_path, time_limit, cpus_per_task, memory, nodes, project)

    def submit_batch_job_with_params(self, script_path, time_limit, cpus_per_task, memory, nodes, project):
        """Submit a batch job with specified parameters."""
        try:
            # Construct the sbatch command with parameters
            command = [
                "sbatch", 
                "-p", self.partition_name,
                "-N", str(nodes),
                "-A", project,
                "--cpus-per-task", str(cpus_per_task),
                "--mem", f"{memory}G",
                "--time", time_limit,
                script_path
            ]
            
            # Run the sbatch command
            result = subprocess.run(command, capture_output=True, text=True)
            
            if result.returncode == 0:
                # Extract job ID from sbatch output (typically "Submitted batch job 12345")
                job_id_match = re.search(r"Submitted batch job (\d+)", result.stdout)
                if job_id_match:
                    job_id = job_id_match.group(1)
                    print(f"Successfully submitted job {job_id} to partition {self.partition_name}")
                    
                    # Show a success message to the user
                    self.show_job_submitted_message(script_path, job_id)
                else:
                    print(f"Job submitted to partition {self.partition_name}, but couldn't extract job ID")
                    print(f"Output: {result.stdout}")
            else:
                # Show error message
                error_msg = result.stderr.strip() if result.stderr else "Unknown error"
                print(f"Error submitting job to partition {self.partition_name}: {error_msg}")
                
                # Show an error message to the user
                self.show_job_error_message(script_path, error_msg)
        
        except Exception as e:
            print(f"Exception when submitting job: {e}")
            # Show an error message to the user
            self.show_job_error_message(script_path, str(e))
    
    def show_job_submitted_message(self, script_path, job_id):
        """Show a message box indicating the job was submitted successfully."""
        script_name = os.path.basename(script_path)
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Information)
        msg_box.setWindowTitle("Job Submitted")
        msg_box.setText(f"Job submitted successfully")
        msg_box.setInformativeText(f"Script: {script_name}\nJob ID: {job_id}\nPartition: {self.partition_name}")
        msg_box.exec_()
    
    def show_job_error_message(self, script_path, error_msg):
        """Show a message box indicating there was an error submitting the job."""
        script_name = os.path.basename(script_path)
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Critical)
        msg_box.setWindowTitle("Job Submission Error")
        msg_box.setText(f"Error submitting job")
        msg_box.setInformativeText(f"Script: {script_name}\nPartition: {self.partition_name}")
        msg_box.setDetailedText(error_msg)
        msg_box.exec_()
    
    def show_context_menu(self, position):
        menu = QMenu(self)
        
        # Add the standard actions
        job_action = menu.addAction("Run Interactive Job")
        job_action.triggered.connect(self.show_job_dialog)
        
        history_action = menu.addAction("Show Job History")
        history_action.triggered.connect(self.show_job_history)
        
        # Try to load the menu structure from JSON
        try:
            menu_structure_path = "menu_structure.json"
            if os.path.exists(menu_structure_path):
                with open(menu_structure_path, 'r') as f:
                    menu_structure = json.load(f)
                
                # Track if we've added any bash scripts
                has_bash_scripts = False
                
                # Create application menus
                directory_menus = {}
                
                # First pass: find all bash scripts and organize by directory
                for directory_name, apps in menu_structure.items():
                    bash_apps = []
                    
                    # Filter for applications with Exec starting with "bash -i " or "mate-terminal -e"
                    for app in apps:
                        app_name = app.get("name", "Unknown")
                        app_exec = app.get("exec", "")
                        
                        # Process bash -i commands directly
                        if app_exec and app_exec.startswith("bash -i "):
                            bash_apps.append(app)
                        
                        # Process mate-terminal commands and extract the bash part
                        elif app_exec and app_exec.startswith("mate-terminal -e "):
                            # Extract the command inside the quotes
                            match = re.search(r'mate-terminal -e\s+"([^"]+)"', app_exec)
                            if match:
                                bash_cmd = match.group(1)
                                # Only include if it contains a bash command
                                if "bash -i " in bash_cmd:
                                    # Create a copy of the app with the modified exec command
                                    modified_app = app.copy()
                                    modified_app["exec"] = bash_cmd
                                    bash_apps.append(modified_app)
                        
                        # Include shell scripts from the RED bin directory
                        elif app_exec and app_exec.startswith("/N/soft/rhel8/red/bin/") and app_exec.endswith(".sh"):
                            # Create a copy of the app with a modified exec command that uses bash -i
                            modified_app = app.copy()
                            modified_app["exec"] = f"bash -i {app_exec}"
                            bash_apps.append(modified_app)
                    
                    # Only create a submenu if there are bash scripts in this directory
                    if bash_apps:
                        has_bash_scripts = True
                        directory_menus[directory_name] = bash_apps
                
                # Add a separator before the application menus if we have any bash scripts
                if has_bash_scripts:
                    menu.addSeparator()
                    
                    # Add the filtered menus
                    for directory_name, bash_apps in directory_menus.items():
                        # Create a submenu for each directory
                        submenu = QMenu(directory_name, menu)
                        
                        # Add applications to the submenu
                        for app in bash_apps:
                            app_name = app.get("name", "Unknown")
                            app_exec = app.get("exec", "")
                            app_icon = app.get("icon", "")
                            
                            # Create action with icon if available
                            if app_icon:
                                # Try to get the icon from theme first
                                icon = QIcon.fromTheme(app_icon)
                                
                                # If theme icon not found, try as a file path
                                if icon.isNull():
                                    # Check if it's an absolute path
                                    if os.path.isabs(app_icon) and os.path.exists(app_icon):
                                        icon = QIcon(app_icon)
                                    # Check if it's a relative path
                                    elif os.path.exists(app_icon):
                                        icon = QIcon(app_icon)
                                    # Fallback to application icon
                                    else:
                                        icon = QIcon.fromTheme("application-x-executable")
                                
                                app_action = submenu.addAction(icon, app_name)
                            else:
                                app_action = submenu.addAction(app_name)
                                
                            # Use a lambda with default arguments to capture the current app_exec value
                            app_action.triggered.connect(lambda checked, cmd=app_exec: self.launch_application(cmd))
                        
                        # Add the submenu to the main menu
                        menu.addMenu(submenu)
        except Exception as e:
            print(f"Error loading menu structure: {e}")
        
        menu.exec_(self.mapToGlobal(position))
    
    def launch_application(self, command):
        """Launch an application as a SLURM job in the partition."""
        try:
            # Remove any field codes like %u, %f, etc.
            command = re.sub(r'%[a-zA-Z]', '', command).strip()
            
            # Get the partition name - the text is stored in a label inside the PartitionIcon
            # Find the label that contains the partition name
            partition_name = None
            for child in self.children():
                if isinstance(child, QLabel) and not isinstance(child, NodeCountBadge) and not isinstance(child, JobStatusBadge):
                    partition_name = child.text()
                    break
            
            if not partition_name:
                # Fallback - try to get the partition name from the object name
                partition_name = self.objectName()
                if not partition_name:
                    raise ValueError("Could not determine partition name")
            
            # Show the time selection dialog to let the user choose resources
            dialog = TimeSelectionDialog(self.partition_name, self)
            
            # Set the window title to indicate we're launching an application
            app_name = command.split('/')[-1] if '/' in command else command
            dialog.setWindowTitle(f"Launch {app_name} - {self.partition_name}")
            
            if dialog.exec_() == QDialog.Accepted:
                # Get the selected resources
                time_limit = dialog.get_selected_time()
                cpus_per_task = dialog.get_selected_cpus()
                memory = dialog.get_selected_memory()
                gpus = dialog.get_selected_gpus()
                
                # Generate a unique job name with timestamp
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                job_name = f"{app_name}_{timestamp}"
                
                # Construct the srun command
                srun_cmd = [
                    "srun",
                    "--partition=" + self.partition_name,
                    "--time=" + time_limit,
                    "--cpus-per-task=" + str(cpus_per_task),
                    "--mem=" + str(memory) + "G",
                    "--nodes=1",
                    "--account=staff",
                    "--job-name=" + job_name,
                    "--x11",
                    "--pty",
                ]
                
                # Add GPU settings if requested
                if gpus:
                    srun_cmd.append(f"--gres=gpu:{gpus}")
                
                # Add the application command
                full_cmd = srun_cmd + command.split()
                
                # Print the full command to the console
                print("Executing command:", " ".join(full_cmd))
                
                # Execute the command in a new process
                subprocess.Popen(full_cmd)
        except Exception as e:
            QMessageBox.warning(self, "Launch Error", f"Failed to launch application: {e}")
    
    def show_job_dialog(self):
        dialog = TimeSelectionDialog(self.partition_name, self)
        if dialog.exec_() == QDialog.Accepted:
            self.start_interactive_job(
                dialog.get_selected_time(),
                dialog.get_selected_cpus(),
                dialog.get_selected_memory(),
                dialog.get_selected_gpus()
            )
    
    def start_interactive_job(self, time_limit="4:00:00", cpus_per_task=8, memory=32, gpus=None):
        # Construct the srun command
        command = (f"srun -p {self.partition_name} -N 1 -A staff --cpus-per-task={cpus_per_task} "
                  f"--mem={memory}G --time={time_limit} --job-name=RED_Interactive_{self.partition_name} ")
        
        # Add GPU settings if requested
        if gpus:
            command += f"--gres=gpu:{gpus} "
        
        # Add terminal settings
        command += "--x11 --pty bash"
        
        # Launch mate-terminal with the command
        try:
            subprocess.Popen([
                "mate-terminal", 
                "--title", f"Interactive Job - {self.partition_name}",
                "-e", f"bash -c '{command}; echo \"Press Enter to close\"; read'"
            ])
            print(f"Started interactive job on partition {self.partition_name} with time limit {time_limit}")
        except Exception as e:
            print(f"Error starting terminal: {e}")
            # Fallback to system's default terminal if mate-terminal is not available
            try:
                # Try with gnome-terminal
                subprocess.Popen([
                    "gnome-terminal", 
                    "--title", f"Interactive Job - {self.partition_name}",
                    "--", "bash", "-c", f"{command}; echo \"Press Enter to close\"; read"
                ])
                print(f"Started interactive job on partition {self.partition_name} with gnome-terminal")
            except Exception as e2:
                print(f"Error starting gnome-terminal: {e2}")
                # Try with xterm as a last resort
                try:
                    subprocess.Popen([
                        "xterm", 
                        "-title", f"Interactive Job - {self.partition_name}",
                        "-e", f"bash -c '{command}; echo \"Press Enter to close\"; read'"
                    ])
                    print(f"Started interactive job on partition {self.partition_name} with xterm")
                except Exception as e3:
                    print(f"Error starting xterm: {e3}")
                    print("Could not start any terminal. Please check if a terminal emulator is installed.")
    
    def mouseDoubleClickEvent(self, event):
        """Handle double-click event to open job history window."""
        if event.button() == Qt.LeftButton:
            self.show_job_history()
        super().mouseDoubleClickEvent(event)
    
    def show_job_history(self):
        """Open a window showing job history for this partition."""
        # Find the main window
        main_window = self.window()
        if not isinstance(main_window, MainWindow):
            # Try to find the main window in the parent hierarchy
            parent = self.parent()
            while parent:
                if isinstance(parent, MainWindow):
                    main_window = parent
                    break
                parent = parent.parent()
        
        # Create the job history window
        history_window = JobHistoryWindow(self.partition_name)
        history_window.show()
        
        # Register the window with the main window if found
        if isinstance(main_window, MainWindow):
            window_key = f"job_history_{self.partition_name}"
            main_window.child_windows[window_key] = history_window
        
        # Store reference to prevent garbage collection
        self._history_window = history_window

    def submit_batch_job(self, script_path):
        """Submit a batch job to SLURM using sbatch."""
        try:
            # Construct the sbatch command with the partition
            command = ["sbatch", "-p", self.partition_name, script_path]
            
            # Run the sbatch command
            result = subprocess.run(command, capture_output=True, text=True)
            
            if result.returncode == 0:
                # Extract job ID from sbatch output (typically "Submitted batch job 12345")
                job_id_match = re.search(r"Submitted batch job (\d+)", result.stdout)
                if job_id_match:
                    job_id = job_id_match.group(1)
                    print(f"Successfully submitted job {job_id} to partition {self.partition_name}")
                    
                    # Show a success message to the user
                    self.show_job_submitted_message(script_path, job_id)
                else:
                    print(f"Job submitted to partition {self.partition_name}, but couldn't extract job ID")
                    print(f"Output: {result.stdout}")
            else:
                # Show error message
                error_msg = result.stderr.strip() if result.stderr else "Unknown error"
                print(f"Error submitting job to partition {self.partition_name}: {error_msg}")
                
                # Show an error message to the user
                self.show_job_error_message(script_path, error_msg)
        
        except Exception as e:
            print(f"Exception when submitting job: {e}")
            # Show an error message to the user
            self.show_job_error_message(script_path, str(e))
    
    def submit_batch_job_direct(self, script_path):
        """Submit a batch job directly to SLURM using sbatch."""
        try:
            # Construct the sbatch command with the partition
            command = ["sbatch", "-p", self.partition_name, script_path]
            
            # Run the sbatch command
            result = subprocess.run(command, capture_output=True, text=True)
            
            if result.returncode == 0:
                # Extract job ID from sbatch output (typically "Submitted batch job 12345")
                job_id_match = re.search(r"Submitted batch job (\d+)", result.stdout)
                if job_id_match:
                    job_id = job_id_match.group(1)
                    print(f"Successfully submitted job {job_id} to partition {self.partition_name}")
                    
                    # Show a success message to the user
                    script_name = os.path.basename(script_path)
                    msg_box = QMessageBox()
                    msg_box.setIcon(QMessageBox.Information)
                    msg_box.setWindowTitle("Job Submitted")
                    msg_box.setText(f"Job submitted successfully")
                    msg_box.setInformativeText(f"Script: {script_name}\nJob ID: {job_id}\nPartition: {self.partition_name}")
                    msg_box.exec_()
                else:
                    print(f"Job submitted to partition {self.partition_name}, but couldn't extract job ID")
                    print(f"Output: {result.stdout}")
            else:
                # Show error message
                error_msg = result.stderr.strip() if result.stderr else "Unknown error"
                print(f"Error submitting job to partition {self.partition_name}: {error_msg}")
                
                # Show an error message to the user
                script_name = os.path.basename(script_path)
                msg_box = QMessageBox()
                msg_box.setIcon(QMessageBox.Critical)
                msg_box.setWindowTitle("Job Submission Error")
                msg_box.setText(f"Error submitting job")
                msg_box.setInformativeText(f"Script: {script_name}\nPartition: {self.partition_name}")
                msg_box.setDetailedText(error_msg)
                msg_box.exec_()
        
        except Exception as e:
            print(f"Exception when submitting job: {e}")
            # Show an error message to the user
            script_name = os.path.basename(script_path)
            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Critical)
            msg_box.setWindowTitle("Job Submission Error")
            msg_box.setText(f"Error submitting job")
            msg_box.setInformativeText(f"Script: {script_name}\nPartition: {self.partition_name}")
            msg_box.setDetailedText(str(e))
            msg_box.exec_()

class BatchJobDialog(QDialog):
    def __init__(self, partition_name, script_path, parent=None):
        super().__init__(parent)
        self.partition_name = partition_name
        self.script_path = script_path
        self.setWindowTitle(f"Configure Batch Job - {partition_name}")
        self.setMinimumWidth(500)
        
        # Get partition information
        self.max_hours = self.get_max_walltime(partition_name)
        self.max_cpus = self.get_max_cpus_per_node(partition_name)
        self.max_memory = self.get_max_memory_per_node(partition_name)
        self.max_nodes = self.get_max_nodes(partition_name)
        
        # Get available projects
        self.available_projects = self.get_available_projects()
        
        # Determine granularity based on max walltime
        self.use_minutes = self.max_hours <= 4
        
        # Create layout
        layout = QVBoxLayout(self)
        
        # Add script info
        script_name = os.path.basename(script_path)
        info_label = QLabel(f"Configure job for script: <b>{script_name}</b> on partition <b>{partition_name}</b>")
        info_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(info_label)
        
        # Add time selection widgets
        time_group = QGroupBox("Time Limit")
        time_layout = QVBoxLayout(time_group)
        
        if self.use_minutes:
            # For short walltimes (≤ 4 hours), use minutes with 15-minute granularity
            slider_layout = QHBoxLayout()
            time_label = QLabel("Walltime:")
            self.time_slider = QSlider(Qt.Horizontal)
            self.time_slider.setMinimum(15)  # 15 minutes minimum
            self.time_slider.setMaximum(self.max_hours * 60)  # Convert hours to minutes
            self.time_slider.setValue(60)  # Default to 1 hour
            self.time_slider.setTickPosition(QSlider.TicksBelow)
            self.time_slider.setTickInterval(15)  # 15-minute intervals
            self.time_slider.setSingleStep(15)  # 15-minute steps
            
            slider_layout.addWidget(time_label)
            slider_layout.addWidget(self.time_slider)
            time_layout.addLayout(slider_layout)
            
            # Create a custom spinbox for hours and minutes
            spinbox_layout = QHBoxLayout()
            
            self.hours_spinbox = QSpinBox()
            self.hours_spinbox.setMinimum(0)
            self.hours_spinbox.setMaximum(self.max_hours)
            self.hours_spinbox.setValue(1)  # Default to 1 hour
            
            self.minutes_spinbox = QSpinBox()
            self.minutes_spinbox.setMinimum(0)
            self.minutes_spinbox.setMaximum(45)  # 0, 15, 30, 45 minutes
            self.minutes_spinbox.setValue(0)  # Default to 0 minutes
            self.minutes_spinbox.setSingleStep(15)  # 15-minute steps
            
            spinbox_layout.addWidget(self.hours_spinbox)
            spinbox_layout.addWidget(QLabel("hours"))
            spinbox_layout.addWidget(self.minutes_spinbox)
            spinbox_layout.addWidget(QLabel("minutes"))
            spinbox_layout.addStretch()
            time_layout.addLayout(spinbox_layout)
            
            # Connect slider and spinboxes
            self.time_slider.valueChanged.connect(self.slider_to_spinboxes)
            self.hours_spinbox.valueChanged.connect(self.spinboxes_to_slider)
            self.minutes_spinbox.valueChanged.connect(self.spinboxes_to_slider)
            
            # Add max time info with minutes
            max_time_text = f"Maximum allowed walltime: {self.max_hours} hour"
            if self.max_hours != 1:
                max_time_text += "s"
            max_time_label = QLabel(max_time_text)
            time_layout.addWidget(max_time_label)
        else:
            # For longer walltimes (> 4 hours), use hours with 1-hour granularity
            slider_layout = QHBoxLayout()
            time_label = QLabel("Walltime (hours):")
            self.time_slider = QSlider(Qt.Horizontal)
            self.time_slider.setMinimum(1)
            self.time_slider.setMaximum(self.max_hours)
            self.time_slider.setValue(4)  # Default to 4 hours
            self.time_slider.setTickPosition(QSlider.TicksBelow)
            self.time_slider.setTickInterval(max(1, self.max_hours // 10))
            
            slider_layout.addWidget(time_label)
            slider_layout.addWidget(self.time_slider)
            time_layout.addLayout(slider_layout)
            
            spinbox_layout = QHBoxLayout()
            self.hours_spinbox = QSpinBox()
            self.hours_spinbox.setMinimum(1)
            self.hours_spinbox.setMaximum(self.max_hours)
            self.hours_spinbox.setValue(4)  # Default to 4 hours
            
            spinbox_layout.addWidget(self.hours_spinbox)
            spinbox_layout.addWidget(QLabel("hours"))
            spinbox_layout.addStretch()
            time_layout.addLayout(spinbox_layout)
            
            # Connect slider and spinbox
            self.time_slider.valueChanged.connect(self.hours_spinbox.setValue)
            self.hours_spinbox.valueChanged.connect(self.time_slider.setValue)
            
            # Add max time info
            max_time_label = QLabel(f"Maximum allowed walltime: {self.max_hours} hours")
            time_layout.addWidget(max_time_label)
        
        layout.addWidget(time_group)
        
        # Add node selection widgets
        node_group = QGroupBox("Node Configuration")
        node_layout = QVBoxLayout(node_group)
        
        # Nodes slider
        nodes_slider_layout = QHBoxLayout()
        nodes_label = QLabel("Number of Nodes:")
        self.nodes_slider = QSlider(Qt.Horizontal)
        self.nodes_slider.setMinimum(1)
        self.nodes_slider.setMaximum(self.max_nodes)
        self.nodes_slider.setValue(1)  # Default to 1 node
        self.nodes_slider.setTickPosition(QSlider.TicksBelow)
        self.nodes_slider.setTickInterval(max(1, self.max_nodes // 10))
        
        nodes_slider_layout.addWidget(nodes_label)
        nodes_slider_layout.addWidget(self.nodes_slider)
        node_layout.addLayout(nodes_slider_layout)
        
        # Nodes spinbox
        nodes_spinbox_layout = QHBoxLayout()
        self.nodes_spinbox = QSpinBox()
        self.nodes_spinbox.setMinimum(1)
        self.nodes_spinbox.setMaximum(self.max_nodes)
        self.nodes_spinbox.setValue(1)  # Default to 1 node
        
        nodes_spinbox_layout.addWidget(self.nodes_spinbox)
        nodes_spinbox_layout.addWidget(QLabel("nodes"))
        nodes_spinbox_layout.addStretch()
        node_layout.addLayout(nodes_spinbox_layout)
        
        # Connect nodes slider and spinbox
        self.nodes_slider.valueChanged.connect(self.nodes_spinbox.setValue)
        self.nodes_spinbox.valueChanged.connect(self.nodes_slider.setValue)
        
        # Add max nodes info
        max_nodes_label = QLabel(f"Maximum nodes in partition: {self.max_nodes}")
        node_layout.addWidget(max_nodes_label)
        
        layout.addWidget(node_group)
        
        # Add CPU selection widgets
        cpu_group = QGroupBox("CPU Resources")
        cpu_layout = QVBoxLayout(cpu_group)
        
        # CPU slider
        cpu_slider_layout = QHBoxLayout()
        cpu_label = QLabel("CPUs per task:")
        self.cpu_slider = QSlider(Qt.Horizontal)
        self.cpu_slider.setMinimum(1)
        self.cpu_slider.setMaximum(self.max_cpus)
        self.cpu_slider.setValue(8)  # Default to 8 CPUs
        self.cpu_slider.setTickPosition(QSlider.TicksBelow)
        self.cpu_slider.setTickInterval(max(1, self.max_cpus // 10))
        
        cpu_slider_layout.addWidget(cpu_label)
        cpu_slider_layout.addWidget(self.cpu_slider)
        cpu_layout.addLayout(cpu_slider_layout)
        
        # CPU spinbox
        cpu_spinbox_layout = QHBoxLayout()
        self.cpu_spinbox = QSpinBox()
        self.cpu_spinbox.setMinimum(1)
        self.cpu_spinbox.setMaximum(self.max_cpus)
        self.cpu_spinbox.setValue(8)  # Default to 8 CPUs
        
        cpu_spinbox_layout.addWidget(self.cpu_spinbox)
        cpu_spinbox_layout.addWidget(QLabel("CPUs"))
        cpu_spinbox_layout.addStretch()
        cpu_layout.addLayout(cpu_spinbox_layout)
        
        # Connect CPU slider and spinbox
        self.cpu_slider.valueChanged.connect(self.cpu_spinbox.setValue)
        self.cpu_spinbox.valueChanged.connect(self.cpu_slider.setValue)
        
        # Add max CPU info
        max_cpu_label = QLabel(f"Maximum CPUs per node: {self.max_cpus}")
        cpu_layout.addWidget(max_cpu_label)
        
        layout.addWidget(cpu_group)
        
        # Add Memory selection widgets
        memory_group = QGroupBox("Memory Resources")
        memory_layout = QVBoxLayout(memory_group)
        
        # Memory slider
        memory_slider_layout = QHBoxLayout()
        memory_label = QLabel("Memory:")
        self.memory_slider = QSlider(Qt.Horizontal)
        self.memory_slider.setMinimum(1)
        self.memory_slider.setMaximum(self.max_memory)
        self.memory_slider.setValue(32)  # Default to 32 GB
        self.memory_slider.setTickPosition(QSlider.TicksBelow)
        self.memory_slider.setTickInterval(max(1, self.max_memory // 10))
        
        memory_slider_layout.addWidget(memory_label)
        memory_slider_layout.addWidget(self.memory_slider)
        memory_layout.addLayout(memory_slider_layout)
        
        # Memory spinbox
        memory_spinbox_layout = QHBoxLayout()
        self.memory_spinbox = QSpinBox()
        self.memory_spinbox.setMinimum(1)
        self.memory_spinbox.setMaximum(self.max_memory)
        self.memory_spinbox.setValue(32)  # Default to 32 GB
        
        memory_spinbox_layout.addWidget(self.memory_spinbox)
        memory_spinbox_layout.addWidget(QLabel("GB"))
        memory_spinbox_layout.addStretch()
        memory_layout.addLayout(memory_spinbox_layout)
        
        # Connect Memory slider and spinbox
        self.memory_slider.valueChanged.connect(self.memory_spinbox.setValue)
        self.memory_spinbox.valueChanged.connect(self.memory_slider.setValue)
        
        # Add max memory info
        max_memory_label = QLabel(f"Maximum memory per node: {self.max_memory} GB")
        memory_layout.addWidget(max_memory_label)
        
        layout.addWidget(memory_group)
        
        # Add Project selection
        project_group = QGroupBox("Project Allocation")
        project_layout = QVBoxLayout(project_group)
        
        project_label = QLabel("Select project allocation:")
        project_layout.addWidget(project_label)
        
        self.project_combo = QComboBox()
        self.project_combo.addItems(self.available_projects)
        if self.available_projects:
            self.project_combo.setCurrentIndex(0)
        project_layout.addWidget(self.project_combo)
        
        layout.addWidget(project_group)
        
        # Add buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
    
    def slider_to_spinboxes(self, value):
        # Convert slider value (in minutes) to hours and minutes
        hours = value // 60
        minutes = value % 60
        # Round minutes to nearest 15
        minutes = round(minutes / 15) * 15
        if minutes == 60:
            hours += 1
            minutes = 0
            
        # Update spinboxes without triggering their signals
        self.hours_spinbox.blockSignals(True)
        self.minutes_spinbox.blockSignals(True)
        self.hours_spinbox.setValue(hours)
        self.minutes_spinbox.setValue(minutes)
        self.hours_spinbox.blockSignals(False)
        self.minutes_spinbox.blockSignals(False)
    
    def spinboxes_to_slider(self):
        # Convert hours and minutes to slider value (in minutes)
        if self.use_minutes:
            total_minutes = self.hours_spinbox.value() * 60 + self.minutes_spinbox.value()
            # Update slider without triggering its signal
            self.time_slider.blockSignals(True)
            self.time_slider.setValue(total_minutes)
            self.time_slider.blockSignals(False)
    
    def get_max_walltime(self, partition_name):
        # Try to get the actual max walltime from SLURM
        try:
            result = subprocess.run(
                ['sinfo', '-p', partition_name, '--format=%l', '-h'],
                capture_output=True, text=True
            )
            time_limit = result.stdout.strip()
            
            # Parse the time limit (format could be "1-00:00:00" for 1 day, "2:00:00" for 2 hours, etc.)
            if time_limit == "infinite" or time_limit == "":
                return 72  # Default to 72 hours if infinite or not specified
            
            hours = 0
            if "-" in time_limit:  # Format: days-hours:minutes:seconds
                days, time_part = time_limit.split("-")
                hours += int(days) * 24
                time_parts = time_part.split(":")
                if len(time_parts) >= 1:
                    hours += int(time_parts[0])
            else:  # Format: hours:minutes:seconds
                time_parts = time_limit.split(":")
                if len(time_parts) >= 1:
                    hours += int(time_parts[0])
            
            return max(1, hours)  # Ensure at least 1 hour
        except Exception as e:
            print(f"Error getting max walltime: {e}")
            return 24  # Default to 24 hours if there's an error
    
    def get_max_cpus_per_node(self, partition_name):
        # Try to get the max CPUs per node from SLURM
        try:
            # Get CPU count for nodes in this partition
            result = subprocess.run(
                ['sinfo', '-p', partition_name, '--format=%c', '-h'],
                capture_output=True, text=True
            )
            cpu_count = result.stdout.strip()
            
            # Parse the CPU count
            try:
                return max(1, int(cpu_count))  # Ensure at least 1 CPU
            except ValueError:
                # If we can't parse the CPU count, try another approach
                # Get node list for the partition
                result = subprocess.run(
                    ['sinfo', '-p', partition_name, '--format=%N', '-h'],
                    capture_output=True, text=True
                )
                node_list = result.stdout.strip().split(',')[0]  # Take the first node
                
                # Get CPU count for this node
                if node_list:
                    result = subprocess.run(
                        ['scontrol', 'show', 'node', node_list, '-o'],
                        capture_output=True, text=True
                    )
                    node_info = result.stdout.strip()
                    
                    # Extract CPU count from node info
                    import re
                    cpu_match = re.search(r'CPUTot=(\d+)', node_info)
                    if cpu_match:
                        return max(1, int(cpu_match.group(1)))
            
            # If all else fails, return a reasonable default
            return 32
        except Exception as e:
            print(f"Error getting max CPUs per node: {e}")
            return 32  # Default to 32 CPUs if there's an error
    
    def get_max_memory_per_node(self, partition_name):
        # Try to get the max memory per node from SLURM
        try:
            # Get node list for the partition
            result = subprocess.run(
                ['sinfo', '-p', partition_name, '--format=%N', '-h'],
                capture_output=True, text=True
            )
            node_list = result.stdout.strip().split(',')[0]  # Take the first node
            
            # If we have a node, get its memory
            if node_list:
                result = subprocess.run(
                    ['scontrol', 'show', 'node', node_list, '-o'],
                    capture_output=True, text=True
                )
                node_info = result.stdout.strip()
                
                # Extract memory from node info
                import re
                # Look for RealMemory which is in MB
                memory_match = re.search(r'RealMemory=(\d+)', node_info)
                if memory_match:
                    # Convert MB to GB and round up
                    memory_mb = int(memory_match.group(1))
                    memory_gb = (memory_mb + 1023) // 1024  # Round up to nearest GB
                    return max(1, memory_gb)
                
                # Alternative: look for Memory which might be in format like "32000M"
                memory_match = re.search(r'Memory=(\d+)([MG])', node_info)
                if memory_match:
                    memory_val = int(memory_match.group(1))
                    memory_unit = memory_match.group(2)
                    if memory_unit == 'M':
                        memory_gb = (memory_val + 1023) // 1024  # Convert MB to GB and round up
                    else:  # 'G'
                        memory_gb = memory_val
                    return max(1, memory_gb)
            
            # If we couldn't get memory info, try another approach
            # Get memory info from sinfo
            result = subprocess.run(
                ['sinfo', '-p', partition_name, '--format=%m', '-h'],
                capture_output=True, text=True
            )
            memory_info = result.stdout.strip()
            
            # Try to parse memory info (could be in format like "32000M" or "32G")
            if memory_info:
                memory_match = re.search(r'(\d+)([MG])?', memory_info)
                if memory_match:
                    memory_val = int(memory_match.group(1))
                    memory_unit = memory_match.group(2) if memory_match.group(2) else 'M'
                    if memory_unit == 'M':
                        memory_gb = (memory_val + 1023) // 1024  # Convert MB to GB and round up
                    else:  # 'G'
                        memory_gb = memory_val
                    return max(1, memory_gb)
            
            # If all else fails, return a reasonable default
            return 128
        except Exception as e:
            print(f"Error getting max memory per node: {e}")
            return 128  # Default to 128 GB if there's an error
    
    def get_max_nodes(self, partition_name):
        """Get the maximum number of nodes available in the partition."""
        try:
            # Get node count for the partition
            result = subprocess.run(
                ['sinfo', '-p', partition_name, '--format=%D', '-h'],
                capture_output=True, text=True
            )
            node_count = result.stdout.strip()
            
            # Parse the node count
            try:
                return max(1, int(node_count))  # Ensure at least 1 node
            except ValueError:
                pass
            
            # If we can't parse the node count, try another approach
            # Count the number of nodes in the partition
            result = subprocess.run(
                ['sinfo', '-p', partition_name, '--format=%N', '-h'],
                capture_output=True, text=True
            )
            node_list = result.stdout.strip()
            
            # Count nodes (they might be comma-separated or in a range like node[1-10])
            if node_list:
                # Split by comma if multiple node groups
                node_groups = node_list.split(',')
                total_nodes = 0
                
                for group in node_groups:
                    # Check if it's a range
                    range_match = re.search(r'\[(\d+)-(\d+)\]', group)
                    if range_match:
                        start = int(range_match.group(1))
                        end = int(range_match.group(2))
                        total_nodes += (end - start + 1)
                    else:
                        # Single node
                        total_nodes += 1
                
                return max(1, total_nodes)
            
            # If all else fails, return a reasonable default
            return 10
        except Exception as e:
            print(f"Error getting max nodes: {e}")
            return 10  # Default to 10 nodes if there's an error
    
    def get_available_projects(self):
        """Get the list of available project allocations for the current user."""
        try:
            # Get current username
            username = os.environ.get('USER') or os.environ.get('USERNAME')
            if not username:
                try:
                    import pwd
                    username = pwd.getpwuid(os.getuid()).pw_name
                except (ImportError, AttributeError):
                    print("Could not determine username")
                    return ["staff"]  # Default to staff if we can't get username
            
            # Run sacctmgr to get user's associations
            result = subprocess.run(
                ['sacctmgr', 'show', 'associations', 'user=' + username, '--noheader', '--parsable2'],
                capture_output=True, text=True
            )
            
            # Parse the output to extract account/project names
            projects = []
            for line in result.stdout.strip().split('\n'):
                if line:
                    fields = line.split('|')
                    if len(fields) > 1:
                        account = fields[1]  # Account/project is typically the second field
                        if account and account not in projects:
                            projects.append(account)
            
            # If no projects found, add a default
            if not projects:
                projects = ["staff"]
            
            return projects
            
        except Exception as e:
            print(f"Error getting available projects: {e}")
            return ["staff"]  # Default to staff if there's an error
    
    def get_selected_time(self):
        if self.use_minutes:
            hours = self.hours_spinbox.value()
            minutes = self.minutes_spinbox.value()
            return f"{hours}:{minutes:02d}:00"  # Format as HH:MM:00
        else:
            hours = self.hours_spinbox.value()
            return f"{hours}:00:00"  # Format as HH:00:00
    
    def get_selected_cpus(self):
        return self.cpu_spinbox.value()
    
    def get_selected_memory(self):
        return self.memory_spinbox.value()
    
    def get_selected_nodes(self):
        return self.nodes_spinbox.value()
    
    def get_selected_project(self):
        return self.project_combo.currentText()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SLURM Partition Viewer")
        
        # Create settings object
        self.settings = QSettings("SLURM", "PartitionViewer")
        
        # Restore window geometry from settings
        self.restoreGeometry(self.settings.value("windowGeometry", b""))
        
        # If no saved geometry, use default
        if not self.size().isValid():
            self.setGeometry(100, 100, 800, 600)
        
        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Create container widget for the grid
        self.container = QWidget()
        layout.addWidget(self.container)
        
        # Create grid layout for icons
        self.grid_layout = QGridLayout(self.container)
        self.grid_layout.setSpacing(20)
        self.grid_layout.setContentsMargins(20, 20, 20, 20)
        
        # Add help button
        help_button = QPushButton(self)
        help_button.setFixedSize(32, 32)
        help_button.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                border-radius: 16px;
                color: white;
                font-weight: bold;
                font-size: 16px;
                border: none;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
        """)
        help_button.setText("?")
        help_button.clicked.connect(self.show_help)
        help_button.setToolTip("Click for help documentation")
        
        # Add user button
        user_button = QPushButton(self)
        user_button.setFixedSize(32, 32)
        user_button.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
            }
            QPushButton:hover {
                background-color: rgba(0, 0, 0, 0.1);
                border-radius: 16px;
            }
        """)
        # Set the user icon
        user_icon = QIcon("user.png")
        user_button.setIcon(user_icon)
        user_button.setIconSize(QSize(32, 32))
        user_button.setToolTip("User Profile")
        user_button.clicked.connect(self.show_user_stats)  # Add click handler
        
        # Position the help button at the lower right
        help_button.move(self.width() - 52, self.height() - 52)  # 20px from right, 20px from bottom + button height
        
        # Position the user button at the top right
        user_button.move(self.width() - 42, 10)  # 10px from right, 10px from top
        
        # Dictionary to store partition icons
        self.partition_icons = {}
        
        # Dictionary to store child windows
        self.child_windows = {}
        
        # Get SLURM partitions
        self.load_partitions()
        
        # Set up timer for polling job status
        self.job_status_timer = QTimer(self)
        self.job_status_timer.timeout.connect(self.update_job_statuses)
        self.job_status_timer.start(10000)  # Poll every 10 seconds
        
        # Initial job status update
        QTimer.singleShot(1000, self.update_job_statuses)
        
        # Store button references for resize handling
        self.help_button = help_button
        self.user_button = user_button
    
    def resizeEvent(self, event):
        """Handle window resize to keep buttons in position."""
        super().resizeEvent(event)
        # Update help button position to stay in lower right corner
        self.help_button.move(self.width() - 52, self.height() - 52)
        # Update user button position to stay in top right corner
        self.user_button.move(self.width() - 42, 10)
    
    def show_help(self):
        """Open help documentation in Firefox."""
        try:
            subprocess.Popen(['firefox', 'https://servicenow.iu.edu/kb?id=kb_article_view&sysparm_article=KB0023298'])
        except Exception as e:
            print(f"Error opening help documentation: {e}")
            QMessageBox.warning(self, "Error", "Could not open help documentation. Please check if Firefox is installed.")
    
    def closeEvent(self, event):
        # Save window geometry before closing
        self.settings.setValue("windowGeometry", self.saveGeometry())
        
        # Close all child windows
        self.close_all_child_windows()
        
        super().closeEvent(event)
    
    def close_all_child_windows(self):
        """Close all child windows (job history and file viewers)."""
        # Close all job history windows
        for window in self.findChildren(JobHistoryWindow):
            # Close any file viewers opened from this job history window
            if hasattr(window, 'file_viewers'):
                for viewer in window.file_viewers.values():
                    if viewer.isVisible():
                        viewer.close()
            window.close()
        
        # Close any other child windows
        for window in self.child_windows.values():
            if window.isVisible():
                window.close()
    
    def load_partitions(self):
        try:
            # Run sinfo command to get partition information with node counts
            result = subprocess.run(['sinfo', '-h', '-o', '%P,%D'], 
                                 capture_output=True, text=True)
            partition_data = result.stdout.strip().split('\n')
            
            # Create and add icons for each partition
            for i, data in enumerate(partition_data):
                if data:  # Skip empty lines
                    parts = data.split(',')
                    partition_name = parts[0]
                    
                    # Parse node count
                    try:
                        node_count = int(parts[1]) if len(parts) > 1 else 0
                    except ValueError:
                        node_count = 0
                    
                    icon = PartitionIcon(partition_name, node_count)
                    row = i // 4  # 4 icons per row
                    col = i % 4
                    self.grid_layout.addWidget(icon, row, col)
                    
                    # Store the icon for later reference
                    self.partition_icons[partition_name] = icon
                    
        except subprocess.CalledProcessError as e:
            print(f"Error running sinfo command: {e}")
            # Add some dummy partitions for testing when SLURM is not available
            dummy_partitions = [
                ("compute", 32), 
                ("gpu", 8), 
                ("bigmem", 4), 
                ("debug", 2), 
                ("interactive", 16)
            ]
            for i, (partition, nodes) in enumerate(dummy_partitions):
                icon = PartitionIcon(partition, nodes)
                row = i // 4
                col = i % 4
                self.grid_layout.addWidget(icon, row, col)
                
                # Store the icon for later reference
                self.partition_icons[partition] = icon
        except Exception as e:
            print(f"Error: {e}")
    
    def update_job_statuses(self):
        """Poll SLURM to check if the user has jobs in each partition."""
        try:
            # Get current username
            username = os.environ.get('USER') or os.environ.get('USERNAME')
            if not username:
                # Try to get username using pwd module on Unix-like systems
                try:
                    import pwd
                    username = pwd.getpwuid(os.getuid()).pw_name
                except (ImportError, AttributeError):
                    print("Could not determine username")
                    return
            
            # Run squeue command to get user's jobs
            result = subprocess.run(
                ['squeue', '-u', username, '-h', '-o', '%P'],
                capture_output=True, text=True
            )
            
            # Get list of partitions where the user has jobs
            active_partitions = set(result.stdout.strip().split('\n'))
            if '' in active_partitions:  # Remove empty string if present
                active_partitions.remove('')
            
            # Update each partition icon
            for display_name, icon in self.partition_icons.items():
                # Use the clean partition name (without asterisk)
                partition_name = icon.partition_name
                has_jobs = partition_name in active_partitions
                icon.update_job_status(has_jobs)
            
        except Exception as e:
            print(f"Error updating job statuses: {e}")
            # For testing in non-SLURM environments, randomly show job badges
            if not self.partition_icons:
                return
                
            import random
            for icon in self.partition_icons.values():
                # 20% chance of having a job in this partition
                has_jobs = random.random() < 0.2
                icon.update_job_status(has_jobs)
    
    def show_user_stats(self):
        """Show the user statistics window."""
        stats_window = UserStatsWindow(self)
        stats_window.exec_()

class UserStatsWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("User SLURM Statistics")
        self.setMinimumWidth(500)
        
        # Create layout
        layout = QVBoxLayout(self)
        
        # Add header
        header_label = QLabel("Your SLURM Usage Statistics (Last 30 Days)")
        header_label.setAlignment(Qt.AlignCenter)
        font = header_label.font()
        font.setBold(True)
        header_label.setFont(font)
        layout.addWidget(header_label)
        
        # Create stats text area
        self.stats_text = QTextEdit()
        self.stats_text.setReadOnly(True)
        layout.addWidget(self.stats_text)
        
        # Add OK button
        button_box = QDialogButtonBox(QDialogButtonBox.Ok)
        button_box.accepted.connect(self.accept)
        layout.addWidget(button_box)
        
        # Load and display stats
        self.load_stats()
    
    def load_stats(self):
        try:
            # Get current username
            username = os.environ.get('USER') or os.environ.get('USERNAME')
            if not username:
                try:
                    import pwd
                    username = pwd.getpwuid(os.getuid()).pw_name
                except (ImportError, AttributeError):
                    self.stats_text.setText("Error: Could not determine username")
                    return
            
            # Calculate date 30 days ago
            thirty_days_ago = datetime.datetime.now() - datetime.timedelta(days=30)
            start_date = thirty_days_ago.strftime("%Y-%m-%d")
            
            # Run sacct command to get detailed job history including account information
            result = subprocess.run([
                'sacct',
                '-u', username,
                '-S', start_date,
                '--format=JobID,Partition,State,Start,End,Elapsed,AllocCPUS,ReqMem,MaxRSS,Account',
                '-P',  # Parsable output
                '--noheader'  # No header in output
            ], capture_output=True, text=True)
            
            # Process the output
            jobs = []
            total_cpu_hours = 0
            total_jobs = 0
            completed_jobs = 0
            failed_jobs = 0
            gpu_jobs = 0
            partition_usage = {}
            account_cpu_hours = {}  # Track CPU hours by account
            
            for line in result.stdout.strip().split('\n'):
                if line and not line.isspace():
                    fields = line.split('|')
                    if not fields[0].endswith('.batch') and not fields[0].endswith('.extern'):
                        # Count jobs by state
                        state = fields[2].upper()
                        if state == 'COMPLETED':
                            completed_jobs += 1
                        elif state in ['FAILED', 'TIMEOUT', 'CANCELLED', 'NODE_FAIL']:
                            failed_jobs += 1
                        
                        # Track partition usage
                        partition = fields[1]
                        partition_usage[partition] = partition_usage.get(partition, 0) + 1
                        
                        # Get account name (last field)
                        account = fields[9] if len(fields) > 9 else 'unknown'
                        
                        # Calculate CPU hours if job is completed
                        if state == 'COMPLETED' and fields[5]:  # Elapsed time field
                            try:
                                # Parse elapsed time (format: [DD-]HH:MM:SS)
                                elapsed = fields[5]
                                hours = 0
                                if '-' in elapsed:
                                    days, time_part = elapsed.split('-')
                                    hours += int(days) * 24
                                    elapsed = time_part
                                
                                time_parts = elapsed.split(':')
                                if len(time_parts) >= 3:
                                    hours += int(time_parts[0])
                                    hours += int(time_parts[1]) / 60
                                
                                # Multiply by allocated CPUs
                                if fields[6]:  # AllocCPUS field
                                    cpu_hours = hours * int(fields[6])
                                    total_cpu_hours += cpu_hours
                                    # Add to account-specific CPU hours
                                    account_cpu_hours[account] = account_cpu_hours.get(account, 0) + cpu_hours
                            except ValueError:
                                pass
                        
                        # Check if it's a GPU job (based on partition name)
                        if 'gpu' in partition.lower():
                            gpu_jobs += 1
                        
                        total_jobs += 1
            
            # Format the statistics
            stats_text = f"""User: {username}
Period: {start_date} to Present

Total Jobs: {total_jobs}
├─ Completed: {completed_jobs}
└─ Failed/Cancelled: {failed_jobs}

Total CPU Hours: {total_cpu_hours:.1f}
GPU Jobs: {gpu_jobs}

Partition Usage:"""
            
            for partition, count in sorted(partition_usage.items()):
                percentage = (count / total_jobs) * 100 if total_jobs > 0 else 0
                stats_text += f"\n├─ {partition}: {count} jobs ({percentage:.1f}%)"
            
            # Add CPU hours by account
            stats_text += "\n\nCPU Hours by Account:"
            for account, cpu_hours in sorted(account_cpu_hours.items()):
                percentage = (cpu_hours / total_cpu_hours) * 100 if total_cpu_hours > 0 else 0
                stats_text += f"\n├─ {account}: {cpu_hours:.1f} hours ({percentage:.1f}%)"
            
            # Display the statistics
            self.stats_text.setText(stats_text)
            
        except Exception as e:
            self.stats_text.setText(f"Error loading statistics: {str(e)}")

def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main() 