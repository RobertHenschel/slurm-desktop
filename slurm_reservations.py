#!/usr/bin/env python3
"""
SLURM Reservations Viewer

This script displays upcoming SLURM reservations in a user-friendly format.
It uses the 'scontrol show reservation' command to fetch reservation data
and presents it in a sorted list by start time.
"""

import subprocess
import datetime
import re
import sys
import argparse
from PyQt5.QtWidgets import (QApplication, QMainWindow, QTableWidget, QTableWidgetItem,
                            QVBoxLayout, QHBoxLayout, QWidget, QPushButton, QLabel,
                            QHeaderView, QComboBox, QCheckBox, QMessageBox)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QIcon, QColor

class ReservationViewer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SLURM Reservations Viewer")
        self.setMinimumSize(800, 600)
        
        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # Create header with controls
        header_layout = QHBoxLayout()
        
        # Add title label
        title_label = QLabel("<h2>Upcoming SLURM Reservations</h2>")
        header_layout.addWidget(title_label)
        
        header_layout.addStretch()
        
        # Add filter controls
        self.filter_label = QLabel("Filter by Partition:")
        header_layout.addWidget(self.filter_label)
        
        self.partition_filter = QComboBox()
        self.partition_filter.addItem("All Partitions")
        header_layout.addWidget(self.partition_filter)
        
        # Add checkbox for showing past reservations
        self.show_past = QCheckBox("Show Past Reservations")
        header_layout.addWidget(self.show_past)
        
        # Add refresh button
        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.clicked.connect(self.refresh_reservations)
        header_layout.addWidget(self.refresh_button)
        
        main_layout.addLayout(header_layout)
        
        # Create table for reservations
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "Reservation Name", 
            "Start Time", 
            "End Time", 
            "Duration", 
            "Nodes", 
            "Partitions",
            "Users/Accounts"
        ])
        
        # Set table properties
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeToContents)
        self.table.setAlternatingRowColors(True)
        self.table.setSortingEnabled(True)
        
        main_layout.addWidget(self.table)
        
        # Add status bar with last update time
        self.status_layout = QHBoxLayout()
        self.status_label = QLabel("Last updated: Never")
        self.status_layout.addWidget(self.status_label)
        
        # Add auto-refresh controls
        self.status_layout.addStretch()
        self.auto_refresh_label = QLabel("Auto-refresh:")
        self.status_layout.addWidget(self.auto_refresh_label)
        
        self.auto_refresh = QComboBox()
        self.auto_refresh.addItems(["Off", "1 minute", "5 minutes", "15 minutes", "30 minutes"])
        self.auto_refresh.currentIndexChanged.connect(self.set_auto_refresh)
        self.status_layout.addWidget(self.auto_refresh)
        
        main_layout.addLayout(self.status_layout)
        
        # Initialize timer for auto-refresh
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh_reservations)
        
        # Load initial data
        self.refresh_reservations()
    
    def set_auto_refresh(self, index):
        # Stop existing timer
        self.timer.stop()
        
        # Set new timer interval based on selection
        if index == 0:  # Off
            return
        elif index == 1:  # 1 minute
            self.timer.start(60 * 1000)
        elif index == 2:  # 5 minutes
            self.timer.start(5 * 60 * 1000)
        elif index == 3:  # 15 minutes
            self.timer.start(15 * 60 * 1000)
        elif index == 4:  # 30 minutes
            self.timer.start(30 * 60 * 1000)
    
    def refresh_reservations(self):
        try:
            # Get all partitions for the filter dropdown
            self.update_partition_list()
            
            # Get reservation data
            reservations = self.get_reservations()
            
            # Apply filters
            filtered_reservations = self.apply_filters(reservations)
            
            # Update the table
            self.populate_table(filtered_reservations)
            
            # Update status
            now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.status_label.setText(f"Last updated: {now}")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to get reservation data: {str(e)}")
    
    def update_partition_list(self):
        try:
            # Save current selection
            current_selection = self.partition_filter.currentText()
            
            # Clear and add "All Partitions" option
            self.partition_filter.clear()
            self.partition_filter.addItem("All Partitions")
            
            # Get partition list
            result = subprocess.run(["sinfo", "-h", "-o", "%P"], capture_output=True, text=True)
            
            if result.returncode == 0:
                partitions = sorted(list(set(result.stdout.strip().split('\n'))))
                self.partition_filter.addItems(partitions)
                
                # Restore previous selection if possible
                index = self.partition_filter.findText(current_selection)
                if index >= 0:
                    self.partition_filter.setCurrentIndex(index)
            
        except Exception as e:
            print(f"Error updating partition list: {e}")
    
    def get_reservations(self):
        """Get all SLURM reservations and parse them into a structured format"""
        result = subprocess.run(["scontrol", "show", "reservation", "-o"], capture_output=True, text=True)
        
        if result.returncode != 0:
            raise Exception(f"scontrol command failed: {result.stderr}")
        
        reservations = []
        
        # Split the output by reservation entries
        reservation_entries = result.stdout.strip().split('\n')
        
        for entry in reservation_entries:
            if not entry.strip():
                continue
                
            # Parse the reservation data
            reservation = {}
            
            # Extract reservation name
            name_match = re.search(r'ReservationName=(\S+)', entry)
            if name_match:
                reservation['name'] = name_match.group(1)
            
            # Extract start time
            start_match = re.search(r'StartTime=(\S+)', entry)
            if start_match:
                start_str = start_match.group(1)
                try:
                    # Parse SLURM date format
                    if start_str == "Unknown":
                        reservation['start_time'] = None
                    else:
                        # Handle SLURM's date format (YYYY-MM-DDTHH:MM:SS)
                        start_time = datetime.datetime.strptime(start_str, "%Y-%m-%dT%H:%M:%S")
                        reservation['start_time'] = start_time
                except ValueError:
                    reservation['start_time'] = None
            
            # Extract end time
            end_match = re.search(r'EndTime=(\S+)', entry)
            if end_match:
                end_str = end_match.group(1)
                try:
                    # Parse SLURM date format
                    if end_str == "Unknown":
                        reservation['end_time'] = None
                    else:
                        # Handle SLURM's date format (YYYY-MM-DDTHH:MM:SS)
                        end_time = datetime.datetime.strptime(end_str, "%Y-%m-%dT%H:%M:%S")
                        reservation['end_time'] = end_time
                except ValueError:
                    reservation['end_time'] = None
            
            # Extract duration
            if reservation.get('start_time') and reservation.get('end_time'):
                duration = reservation['end_time'] - reservation['start_time']
                reservation['duration'] = duration
            else:
                reservation['duration'] = None
            
            # Extract nodes
            nodes_match = re.search(r'Nodes=(\S+)', entry)
            if nodes_match:
                reservation['nodes'] = nodes_match.group(1)
            
            # Extract partitions
            partition_match = re.search(r'Partition=(\S+)', entry)
            if partition_match:
                reservation['partitions'] = partition_match.group(1)
            
            # Extract users
            users_match = re.search(r'Users=(\S+)', entry)
            if users_match and users_match.group(1) != "n/a":
                reservation['users'] = users_match.group(1)
            else:
                reservation['users'] = None
            
            # Extract accounts
            accounts_match = re.search(r'Accounts=(\S+)', entry)
            if accounts_match and accounts_match.group(1) != "n/a":
                reservation['accounts'] = accounts_match.group(1)
            else:
                reservation['accounts'] = None
            
            # Add to list
            reservations.append(reservation)
        
        return reservations
    
    def apply_filters(self, reservations):
        """Apply filters to the reservation list"""
        filtered = []
        
        # Get current filter settings
        selected_partition = self.partition_filter.currentText()
        show_past = self.show_past.isChecked()
        current_time = datetime.datetime.now()
        
        for res in reservations:
            # Filter by partition if not "All Partitions"
            if selected_partition != "All Partitions":
                if not res.get('partitions') or selected_partition not in res.get('partitions').split(','):
                    continue
            
            # Filter out past reservations if not showing them
            if not show_past and res.get('end_time') and res['end_time'] < current_time:
                continue
            
            filtered.append(res)
        
        # Sort by start time
        filtered.sort(key=lambda x: x.get('start_time') or datetime.datetime.max)
        
        return filtered
    
    def populate_table(self, reservations):
        """Fill the table with reservation data"""
        self.table.setSortingEnabled(False)
        self.table.setRowCount(0)
        
        current_time = datetime.datetime.now()
        
        for row, res in enumerate(reservations):
            self.table.insertRow(row)
            
            # Reservation Name
            name_item = QTableWidgetItem(res.get('name', 'Unknown'))
            self.table.setItem(row, 0, name_item)
            
            # Start Time
            start_time = res.get('start_time')
            if start_time:
                start_str = start_time.strftime("%Y-%m-%d %H:%M")
                start_item = QTableWidgetItem(start_str)
                # Sort by the actual datetime
                start_item.setData(Qt.UserRole, start_time.timestamp())
            else:
                start_item = QTableWidgetItem("Unknown")
            self.table.setItem(row, 1, start_item)
            
            # End Time
            end_time = res.get('end_time')
            if end_time:
                end_str = end_time.strftime("%Y-%m-%d %H:%M")
                end_item = QTableWidgetItem(end_str)
                # Sort by the actual datetime
                end_item.setData(Qt.UserRole, end_time.timestamp())
            else:
                end_item = QTableWidgetItem("Unknown")
            self.table.setItem(row, 2, end_item)
            
            # Duration
            duration = res.get('duration')
            if duration:
                # Format duration nicely
                days = duration.days
                hours, remainder = divmod(duration.seconds, 3600)
                minutes, _ = divmod(remainder, 60)
                
                if days > 0:
                    duration_str = f"{days}d {hours}h {minutes}m"
                else:
                    duration_str = f"{hours}h {minutes}m"
                
                duration_item = QTableWidgetItem(duration_str)
                # Sort by total seconds
                duration_item.setData(Qt.UserRole, duration.total_seconds())
            else:
                duration_item = QTableWidgetItem("Unknown")
            self.table.setItem(row, 3, duration_item)
            
            # Nodes
            nodes_item = QTableWidgetItem(res.get('nodes', 'Unknown'))
            self.table.setItem(row, 4, nodes_item)
            
            # Partitions
            partitions_item = QTableWidgetItem(res.get('partitions', 'Unknown'))
            self.table.setItem(row, 5, partitions_item)
            
            # Users/Accounts
            users = res.get('users', '')
            accounts = res.get('accounts', '')
            
            if users and accounts:
                users_accounts = f"Users: {users}\nAccounts: {accounts}"
            elif users:
                users_accounts = f"Users: {users}"
            elif accounts:
                users_accounts = f"Accounts: {accounts}"
            else:
                users_accounts = "None specified"
            
            users_accounts_item = QTableWidgetItem(users_accounts)
            self.table.setItem(row, 6, users_accounts_item)
            
            # Color coding based on reservation status
            if start_time and end_time:
                if current_time < start_time:
                    # Future reservation - light blue
                    color = QColor(220, 240, 255)
                elif current_time > end_time:
                    # Past reservation - light gray
                    color = QColor(240, 240, 240)
                else:
                    # Active reservation - light green
                    color = QColor(220, 255, 220)
                
                # Apply color to all cells in the row
                for col in range(self.table.columnCount()):
                    self.table.item(row, col).setBackground(color)
        
        self.table.setSortingEnabled(True)
        # Default sort by start time
        self.table.sortItems(1, Qt.AscendingOrder)

def main():
    app = QApplication(sys.argv)
    window = ReservationViewer()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main() 