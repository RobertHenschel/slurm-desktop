# Simple SLURM Viewer
A lightweight PyQt5 application to display SLURM partitions in a grid.

<img width="400" alt="image" src="https://github.com/user-attachments/assets/5a1e51dd-b34d-4cb0-8b2f-30aa601b7a39" />
<img width="400" alt="image" src="https://github.com/user-attachments/assets/6769c51f-d0c2-4d32-8210-2560d45c8a57" />

## Features
- Displays all available SLURM partitions in a grid layout
- Shows partition name and node count for each partition
- Sorts partitions alphabetically
- Responsive design with a scrollable grid
- Error handling for environments without SLURM
- Application icon
- Detect and highlight default partition
- Detect and show GPU partitions
- Right click on a partition to start an interactive job (Only works if `mate-terminal` is available - [Issue](https://github.com/RobertHenschel/slurm-desktop/issues/4))

## Requirements
- Python 3.6+
- PyQt5
- SLURM commands available in PATH

## Installation
1. Ensure you have Python 3.6 or newer installed
2. Install PyQt5:
   ```
   pip install PyQt5
   ```
3. Download `simple_slurm_viewer.py`, `settings.py`, `interactive_job.py` and icon file `queue.png` or clone this whole repo with `git clone https://github.com/RobertHenschel/slurm-desktop.git`

## Usage
```
python3 simple_slurm_viewer.py
```
The application will open a window displaying all available SLURM partitions in a grid layout.

# SLURM Partition Viewer
This application was developed for IU's Research Desktop and will likely NOT work anywhere else. This is Linux desktop application to interface with SLURM. Currently this is mostly a proof of concept, and really only works on IU's Research Desktop environment. Please reach out if you would like to use this on your HPCDesktop system.

<img src="https://github.com/user-attachments/assets/41f8bed9-133b-4e2a-b2cc-5e9d26cb29f9" alt="My image" width="500" />
<img src="https://github.com/user-attachments/assets/130006ff-5a5f-4ce7-ac14-cc1e50c3a356" alt="My image" width="200" />

# menu_parser.py
- This is not general purpose. It currently only works on IU's RED system.

# Features
- Show SLURM partitions, and number of nodes in a window.
- Link to a URL for help, show "Help" icon in main window.
- Show user SLURM stats in a separate window, via "User" icon in main window.
- Run an interactive job in any partition, via context menu on every partition.
- Show users jobs per partition, via double clicking the partition.
- Show users currently in queue jobs per partition, also via double clicking the partition.
  - Allow to cancel a running/pending job via the context menu on the job row in the table.
  - Show stdout and stderr output of a running job, via context menu on the job row in the table.
- Show a green "play" icon on top of the partition if the user has a running job in the queue.
- Show a yellow "pause" icon on top of the partition if the user has a pending/waiting job in the queue.
- Drag and Drop an *.sh file onto any partition to run it with sbatch.
  - If the file contains "#SBATCH" commands, it is just run, but the partition is overwritten by command line arguemnt.
  - If the file doesn't contain any "#SBATCH" commands, the user can specify them before the script is run.
- If MATE menu was parsed, show all applications from the menu in the context menu of every partition.
  - Selecting the app will run it in the partition.
- Show upcoming maintenance reservation in status bar of main window.
- A user can and needs to pick an "account" for every job that is run.
- When running in a partition that has GPUs, it is enforced that you request at least one GPU.
