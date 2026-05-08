Linux System Health Checker
===========================

A Python command-line tool for generating a system health report in a Linux/WSL environment.

The tool collects operating system details, CPU information, RAM usage, disk usage, NVIDIA GPU statistics, uptime, IP configuration, and top memory-consuming processes.
Each run prints a report to the terminal and saves a timestamped text report inside the system-reports folder.

Features
--------

- Reports operating system and platform information
- Detects CPU model from /proc/cpuinfo
- Shows logical CPU count
- Calculates a CPU usage snapshot from /proc/stat
- Displays 1, 5, and 15 minute load averages
- Reports disk usage for the root filesystem
- Reports RAM usage separately from GPU VRAM
- Uses nvidia-smi to collect NVIDIA GPU data when available
- Reports GPU temperature, GPU load, VRAM usage, and power draw
- Attempts to detect temperature and fan sensor data
- Displays local IP configuration
- Lists top processes sorted by memory usage
- Saves timestamped reports automatically


Requirements
------------

- Python 3
- Linux or WSL2
- NVIDIA GPU support through nvidia-smi for GPU reporting

The script uses only Python standard library modules:

- os
- platform
- shutil
- subprocess
- time
- datetime

No external Python packages are required.


Project Structure
-----------------

health-tracker/
├── health_check.py
├── README.md
└── system-reports/
    └── system_report_YYYY-MM-DD_HHMMSS.txt


Usage
-----

Run the script from the project folder:

    python3 health_check.py

The report will be printed in the terminal and saved automatically inside:

    system-reports/

Example report filename:

    system_report_2026-05-08_114022.txt


Notes
-----

This project was developed in WSL2.

Some hardware information may not be available from inside WSL.
CPU temperature, CPU fan speed, motherboard fan speed, and some power limits may not be exposed to the Linux environment.
NVIDIA GPU information is available only when nvidia-smi is installed and working.

Future Improvements
-------------------

- Add JSON export
- Add warning messages for high CPU, RAM, disk, or GPU usage
- Add command-line arguments
- Add a live monitoring mode
- Add native Linux support for CPU temperature and fan sensors
- Add tests for helper functions