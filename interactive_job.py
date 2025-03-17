#!/usr/bin/env python3
"""
Interactive job dialog and functionality for SLURM Partition Viewer
"""
import subprocess
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, 
                             QLabel, QSpinBox, QComboBox, QPushButton, 
                             QSlider, QLineEdit, QGroupBox, QDialogButtonBox)
from PyQt5.QtCore import Qt
import os

# Import settings
import settings

class InteractiveJobDialog(QDialog):
    """Dialog for setting up an interactive SLURM job"""
    
    def __init__(self, partition_name, parent=None):
        super().__init__(parent)
        
        self.partition_name = partition_name
        
        # Set dialog properties
        self.setWindowTitle(f"Interactive Job - {partition_name}")
        self.setMinimumWidth(400)
        
        # Create the form layout
        layout = QVBoxLayout(self)
        form_layout = QFormLayout()
        
        # Time limit section
        time_group = QGroupBox("Time Limit")
        time_layout = QVBoxLayout(time_group)
        
        # Create time slider and labels
        slider_layout = QHBoxLayout()
        self.time_slider = QSlider(Qt.Horizontal)
        self.time_slider.setMinimum(1)  # 1 minute
        max_walltime_minutes = self.get_max_walltime(partition_name)
        self.time_slider.setMaximum(max_walltime_minutes)
        
        # Parse default time limit from settings (format "HH:MM:00")
        default_time_parts = settings.DEFAULT_TIME_LIMIT.split(":")
        if len(default_time_parts) >= 2:
            default_minutes = (int(default_time_parts[0]) * 60) + int(default_time_parts[1])
        else:
            default_minutes = 60  # Fallback to 1 hour if format is unexpected
        
        # Use default time if within partition limits, otherwise use half of max time
        if default_minutes > max_walltime_minutes:
            default_minutes = max(1, max_walltime_minutes // 2)  # At least 1 minute
        
        self.time_slider.setValue(default_minutes)
        
        # Add min/max labels
        min_label = QLabel("1m")
        max_label = QLabel(f"{max_walltime_minutes//60}h")
        
        slider_layout.addWidget(min_label)
        slider_layout.addWidget(self.time_slider)
        slider_layout.addWidget(max_label)
        time_layout.addLayout(slider_layout)
        
        # Create spinboxes for hours and minutes
        time_spinbox_layout = QHBoxLayout()
        time_spinbox_layout.setSpacing(2)  # Reduce overall spacing
        
        # Create hours label and spinbox in a tight group
        hours_layout = QHBoxLayout()
        hours_layout.setSpacing(0)  # Zero spacing between label and spinbox
        hours_layout.setContentsMargins(0, 0, 0, 0)  # Remove all margins
        hours_label = QLabel("Hours:")
        hours_label.setContentsMargins(0, 0, 0, 0)  # Remove label margins
        hours_layout.addWidget(hours_label)
        
        self.hours_spinbox = QSpinBox()
        self.hours_spinbox.setRange(0, max_walltime_minutes // 60)
        self.hours_spinbox.setValue(default_minutes // 60)  # Set hours from default_minutes
        self.hours_spinbox.setContentsMargins(0, 0, 0, 0)  # Remove spinbox margins
        hours_layout.addWidget(self.hours_spinbox)
        
        # Create minutes label and spinbox in a tight group
        minutes_layout = QHBoxLayout()
        minutes_layout.setSpacing(0)  # Zero spacing between label and spinbox
        minutes_label = QLabel("Minutes:")
        minutes_layout.addWidget(minutes_label)
        
        self.minutes_spinbox = QSpinBox()
        self.minutes_spinbox.setRange(0, 59)
        self.minutes_spinbox.setValue(default_minutes % 60)  # Set minutes from default_minutes
        minutes_layout.addWidget(self.minutes_spinbox)
        
        # Add spacing between hours and minutes groups
        time_spinbox_layout.addLayout(hours_layout)
        
        time_spinbox_layout.addLayout(minutes_layout)
        time_layout.addLayout(time_spinbox_layout)
        
        # Add a stretching spacer between hours and minutes to push them apart
        time_spinbox_layout.addStretch(1)

        # Connect time slider and spinboxes
        self.time_slider.valueChanged.connect(self.slider_to_spinboxes)
        self.hours_spinbox.valueChanged.connect(self.spinboxes_to_slider)
        self.minutes_spinbox.valueChanged.connect(self.spinboxes_to_slider)
        
        layout.addWidget(time_group)
        
        # CPU section (elevated to top level)
        cpu_group = QGroupBox("CPUs")
        cpu_layout = QVBoxLayout(cpu_group)
        
        # CPU slider
        cpu_slider_layout = QHBoxLayout()
        self.cpu_slider = QSlider(Qt.Horizontal)
        max_cpus = self.get_max_cpus_per_node(partition_name)
        self.cpu_slider.setMinimum(1)
        self.cpu_slider.setMaximum(max_cpus)
        self.cpu_slider.setValue(settings.DEFAULT_CPUS)
        
        # CPU slider labels
        cpu_min_label = QLabel("1")
        cpu_max_label = QLabel(f"{max_cpus}")
        
        cpu_slider_layout.addWidget(cpu_min_label)
        cpu_slider_layout.addWidget(self.cpu_slider)
        cpu_slider_layout.addWidget(cpu_max_label)
        cpu_layout.addLayout(cpu_slider_layout)
        
        # CPU spinbox
        cpu_spinbox_layout = QHBoxLayout()
        self.cpus_spinbox = QSpinBox()
        self.cpus_spinbox.setRange(1, max_cpus)
        self.cpus_spinbox.setValue(settings.DEFAULT_CPUS)
        
        cpu_spinbox_layout.addStretch()
        cpu_spinbox_layout.addWidget(QLabel("CPUs:"))
        cpu_spinbox_layout.addWidget(self.cpus_spinbox)
        cpu_spinbox_layout.addStretch()
        cpu_layout.addLayout(cpu_spinbox_layout)
        
        # Connect CPU slider and spinbox
        self.cpu_slider.valueChanged.connect(self.cpu_slider_to_spinbox)
        self.cpus_spinbox.valueChanged.connect(self.cpu_spinbox_to_slider)
        
        layout.addWidget(cpu_group)
        
        # Memory section (elevated to top level)
        memory_group = QGroupBox("Memory")
        memory_layout = QVBoxLayout(memory_group)
        
        # Memory slider
        memory_slider_layout = QHBoxLayout()
        self.memory_slider = QSlider(Qt.Horizontal)
        max_memory = self.get_max_memory_per_node(partition_name)
        self.memory_slider.setMinimum(1)
        self.memory_slider.setMaximum(max_memory)
        self.memory_slider.setValue(settings.DEFAULT_MEMORY)
        
        # Memory slider labels
        memory_min_label = QLabel("1 GB")
        memory_max_label = QLabel(f"{max_memory} GB")
        
        memory_slider_layout.addWidget(memory_min_label)
        memory_slider_layout.addWidget(self.memory_slider)
        memory_slider_layout.addWidget(memory_max_label)
        memory_layout.addLayout(memory_slider_layout)
        
        # Memory spinbox
        memory_spinbox_layout = QHBoxLayout()
        self.memory_spinbox = QSpinBox()
        self.memory_spinbox.setRange(1, max_memory)
        self.memory_spinbox.setValue(settings.DEFAULT_MEMORY)
        self.memory_spinbox.setSuffix(" GB")
        
        memory_spinbox_layout.addStretch()
        memory_spinbox_layout.addWidget(QLabel("Memory:"))
        memory_spinbox_layout.addWidget(self.memory_spinbox)
        memory_spinbox_layout.addStretch()
        memory_layout.addLayout(memory_spinbox_layout)
        
        # Connect memory slider and spinbox
        self.memory_slider.valueChanged.connect(self.memory_slider_to_spinbox)
        self.memory_spinbox.valueChanged.connect(self.memory_spinbox_to_slider)
        
        layout.addWidget(memory_group)
        
        # GPU section (elevated to top level, if available)
        gpu_info = self.get_gpu_info(partition_name)
        if gpu_info:
            max_gpus = sum(count for _, count in gpu_info)
            if max_gpus > 0:
                gpu_group = QGroupBox("GPUs")
                gpu_layout = QVBoxLayout(gpu_group)
                
                # GPU slider
                gpu_slider_layout = QHBoxLayout()
                self.gpu_slider = QSlider(Qt.Horizontal)
                self.gpu_slider.setMinimum(1)
                self.gpu_slider.setMaximum(max_gpus)
                self.gpu_slider.setValue(1)
                
                # GPU slider labels
                gpu_min_label = QLabel("1")
                gpu_max_label = QLabel(f"{max_gpus}")
                
                gpu_slider_layout.addWidget(gpu_min_label)
                gpu_slider_layout.addWidget(self.gpu_slider)
                gpu_slider_layout.addWidget(gpu_max_label)
                gpu_layout.addLayout(gpu_slider_layout)
                
                # GPU spinbox
                gpu_spinbox_layout = QHBoxLayout()
                self.gpus_spinbox = QSpinBox()
                self.gpus_spinbox.setRange(1, max_gpus)
                self.gpus_spinbox.setValue(1)
                
                # Show GPU types in the label
                gpu_types = []
                for gpu_type, count in gpu_info:
                    gpu_types.append(f"{gpu_type}")
                
                gpu_type_text = ", ".join(gpu_types)
                
                gpu_spinbox_layout.addStretch()
                gpu_spinbox_layout.addWidget(QLabel(f"GPUs ({gpu_type_text}):"))
                gpu_spinbox_layout.addWidget(self.gpus_spinbox)
                gpu_spinbox_layout.addStretch()
                gpu_layout.addLayout(gpu_spinbox_layout)
                
                # Connect GPU slider and spinbox
                self.gpu_slider.valueChanged.connect(self.gpu_slider_to_spinbox)
                self.gpus_spinbox.valueChanged.connect(self.gpu_spinbox_to_slider)
                
                layout.addWidget(gpu_group)
            else:
                self.gpus_spinbox = None
                self.gpu_slider = None
        else:
            self.gpus_spinbox = None
            self.gpu_slider = None
        
        # Project selection
        account_group = QGroupBox("Account")
        account_layout = QFormLayout(account_group)
        
        self.project_combo = QComboBox()
        projects = self.get_available_projects()
        self.project_combo.addItems(projects)
        
        # Set background color for selected items
        self.project_combo.setStyleSheet("""
            QComboBox::item:selected {
                background-color: #2980b9; 
                color: white;
            }
        """)
        
        # Set default project if it's in the list
        default_index = self.project_combo.findText(settings.DEFAULT_PROJECT)
        if default_index >= 0:
            self.project_combo.setCurrentIndex(default_index)
            
        account_layout.addRow("Project:", self.project_combo)
        
        layout.addWidget(account_group)
        
        # Dialog buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
    
    def slider_to_spinboxes(self, value):
        """Convert slider value (in minutes) to hours and minutes"""
        hours = value // 60
        minutes = value % 60
        
        # Block signals to prevent recursion
        self.hours_spinbox.blockSignals(True)
        self.minutes_spinbox.blockSignals(True)
        
        self.hours_spinbox.setValue(hours)
        self.minutes_spinbox.setValue(minutes)
        
        self.hours_spinbox.blockSignals(False)
        self.minutes_spinbox.blockSignals(False)
    
    def spinboxes_to_slider(self):
        """Convert hours and minutes to slider value (in minutes)"""
        hours = self.hours_spinbox.value()
        minutes = self.minutes_spinbox.value()
        
        # Block signals to prevent recursion
        self.time_slider.blockSignals(True)
        
        self.time_slider.setValue(hours * 60 + minutes)
        
        self.time_slider.blockSignals(False)
    
    def get_max_walltime(self, partition_name):
        """Get the max walltime for a partition in minutes"""
        try:
            result = subprocess.run(
                ["sinfo", "-p", partition_name, "--noheader", "--format=%l"],
                capture_output=True,
                text=True,
                check=True
            )
            
            max_time = result.stdout.strip()
            
            # Parse the time format (e.g., "1-00:00:00" for 1 day)
            if max_time == "infinite":
                return 60 * 24 * 7  # Default to 7 days for infinite
            
            # Handle different time formats
            if "-" in max_time:  # Format: days-hours:minutes:seconds
                days, time_part = max_time.split("-")
                hours, minutes, seconds = time_part.split(":")
                return (int(days) * 24 * 60) + (int(hours) * 60) + int(minutes)
            else:  # Format: hours:minutes:seconds
                parts = max_time.split(":")
                if len(parts) == 3:
                    hours, minutes, seconds = parts
                    return (int(hours) * 60) + int(minutes)
                else:
                    return 60 * 4  # Default to 4 hours
        except Exception as e:
            print(f"Error getting max walltime: {e}")
            return 60 * 4  # Default to 4 hours
    
    def get_max_cpus_per_node(self, partition_name):
        """Get the max CPUs per node for a partition"""
        try:
            result = subprocess.run(
                ["sinfo", "-p", partition_name, "--noheader", "--format=%c"],
                capture_output=True,
                text=True,
                check=True
            )
            
            max_cpus = result.stdout.strip()
            try:
                return int(max_cpus)
            except ValueError:
                return 16  # Default to 16 CPUs
        except Exception as e:
            print(f"Error getting max CPUs: {e}")
            return 16  # Default to 16 CPUs
    
    def get_max_memory_per_node(self, partition_name):
        """Get the max memory per node for a partition in GB"""
        try:
            result = subprocess.run(
                ["sinfo", "-p", partition_name, "--noheader", "--format=%m"],
                capture_output=True,
                text=True,
                check=True
            )
            
            max_mem = result.stdout.strip()
            try:
                # Convert to GB and round up
                mem_mb = int(max_mem)
                return max(1, mem_mb // 1024)
            except ValueError:
                return 32  # Default to 32 GB
        except Exception as e:
            print(f"Error getting max memory: {e}")
            return 32  # Default to 32 GB
    
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
                    print(f"Error parsing GPU info: {e}")
            
            return None
            
        except Exception as e:
            print(f"Error getting GPU info: {e}")
            return None
    
    def get_available_projects(self):
        """Get available Slurm accounts/projects for the current user"""
        try:
            # Get current username from environment
            username = os.environ.get('USER', os.environ.get('USERNAME', ''))
            
            # Run sacctmgr to get user's accounts
            result = subprocess.run(
                ["sacctmgr", "show", "associations", f"user={username}", "--noheader", "format=account"],
                capture_output=True,
                text=True,
                check=True
            )
            
            # Process the output to get account names
            accounts = []
            for line in result.stdout.strip().split('\n'):
                account = line.strip()
                if account and account not in accounts:
                    accounts.append(account)
            
            # Sort accounts alphabetically for easier finding
            accounts.sort()
            
            if accounts:
                return accounts
            else:
                # If no accounts found, return a default
                return [settings.DEFAULT_PROJECT]
                
        except Exception as e:
            print(f"Error getting available projects: {e}")
            return [settings.DEFAULT_PROJECT]  # Default to the project from settings
    
    def get_selected_time(self):
        """Get the selected time limit in HH:MM:00 format"""
        hours = self.hours_spinbox.value()
        minutes = self.minutes_spinbox.value()
        
        return f"{hours}:{minutes:02d}:00"
    
    def get_selected_cpus(self):
        """Get the selected number of CPUs"""
        return self.cpus_spinbox.value()
    
    def get_selected_memory(self):
        """Get the selected memory in GB"""
        return self.memory_spinbox.value()
    
    def get_selected_gpus(self):
        """Get the selected number of GPUs"""
        if self.gpus_spinbox:
            return self.gpus_spinbox.value()
        return None
    
    def get_selected_project(self):
        """Get the selected project"""
        return self.project_combo.currentText()
    
    def cpu_slider_to_spinbox(self, value):
        """Update CPU spinbox from slider value"""
        self.cpus_spinbox.blockSignals(True)
        self.cpus_spinbox.setValue(value)
        self.cpus_spinbox.blockSignals(False)
    
    def cpu_spinbox_to_slider(self):
        """Update CPU slider from spinbox value"""
        self.cpu_slider.blockSignals(True)
        self.cpu_slider.setValue(self.cpus_spinbox.value())
        self.cpu_slider.blockSignals(False)
    
    def memory_slider_to_spinbox(self, value):
        """Update memory spinbox from slider value"""
        self.memory_spinbox.blockSignals(True)
        self.memory_spinbox.setValue(value)
        self.memory_spinbox.blockSignals(False)
    
    def memory_spinbox_to_slider(self):
        """Update memory slider from spinbox value"""
        self.memory_slider.blockSignals(True)
        self.memory_slider.setValue(self.memory_spinbox.value())
        self.memory_slider.blockSignals(False)
        
    def gpu_slider_to_spinbox(self, value):
        """Update GPU spinbox from slider value"""
        if self.gpus_spinbox:
            self.gpus_spinbox.blockSignals(True)
            self.gpus_spinbox.setValue(value)
            self.gpus_spinbox.blockSignals(False)
    
    def gpu_spinbox_to_slider(self):
        """Update GPU slider from spinbox value"""
        if self.gpu_slider:
            self.gpu_slider.blockSignals(True)
            self.gpu_slider.setValue(self.gpus_spinbox.value())
            self.gpu_slider.blockSignals(False)

def start_interactive_job(partition_name, time_limit=settings.DEFAULT_TIME_LIMIT, 
                          cpus_per_task=settings.DEFAULT_CPUS, 
                          memory=settings.DEFAULT_MEMORY, 
                          gpus=None, 
                          project=settings.DEFAULT_PROJECT):
    """Start an interactive job with the specified parameters"""
    # Construct the srun command
    command = (f"srun -p {partition_name} -N 1 -A {project} --cpus-per-task={cpus_per_task} "
              f"--mem={memory}G --time={time_limit} --job-name=Interactive_{partition_name} ")
    
    # Add GPU settings if requested
    if gpus:
        command += f"--gres=gpu:{gpus} "
    
    # Add terminal settings
    command += "--x11 --pty bash"
    
    # Launch terminal with the command
    try:
        subprocess.Popen([
            settings.TERMINAL_COMMAND, 
            settings.TERMINAL_TITLE_ARG, f"Interactive Job - {partition_name}",
            settings.TERMINAL_EXEC_ARG, settings.TERMINAL_EXEC_WRAPPER.format(command)
        ])
        print(f"Started interactive job on partition {partition_name} with time limit {time_limit}")
        return True
    except Exception as e:
        print(f"Error starting interactive job: {e}")
        return False 