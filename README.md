# slurm-desktop
Linux desktop application to interface with SLURM

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
- Show a green "play" icon on top of the partition if the user has a job in the queue.
- Drag and Drop an *.sh file onto any partition to run it with sbatch.
  - If the file contains "#SBATCH" commands, it is just run, but the partition is overwritten by command line arguemnt.
  - If the file doesn't contain any "#SBATCH" commands, the user can specify them before the script is run.
- If MATE menu was parsed, show all applications from the menu in the context menu of every partition.
  - Selecting the app will run it in the partition.