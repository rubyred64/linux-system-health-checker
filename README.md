Linux System Health Checker
===========================

A Python command-line tool that generates a system health report for a Linux/WSL environment.

The tool collects operating system details, CPU information, RAM usage, disk usage, NVIDIA GPU statistics, uptime, IP configuration, sensor availability, and top memory-consuming processes. Each run prints a report to the terminal and can save the report as either a text file or a JSON file.

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
- Reports GPU temperature, GPU load, VRAM usage, fan speed, power draw, and power limit when available
- Attempts to detect temperature and fan sensor data
- Displays local IP configuration
- Lists top processes sorted by memory usage
- Saves timestamped text reports by default
- Supports JSON report export
- Supports no-save mode for terminal-only output
- Supports warning thresholds for disk usage, RAM usage, and GPU temperature

Requirements
------------

- Python 3
- Linux or WSL2
- NVIDIA GPU support through nvidia-smi for GPU reporting

No external Python packages are required.

Project Structure
-----------------

    linux-system-health-checker/
    ├── health_check.py
    ├── README.md
    ├── .gitignore
    └── system-reports/
        └── example_report.txt

Usage
-----

Run the health checker with default settings:

    python3 health_check.py

This prints a text report to the terminal and saves a timestamped text report inside:

    system-reports/

Save the report as JSON instead of text:

    python3 health_check.py --json

This still prints the readable text report in the terminal, but saves the report data as a JSON file.

Run without saving a report file:

    python3 health_check.py --no-save

Change warning thresholds:

    python3 health_check.py --warn-disk 80 --warn-ram 85 --warn-gpu-temp 80

Available Options
-----------------

    --json

Saves the report as a JSON file instead of a text file.

    --no-save

Prints the report in the terminal without saving any report file.

    --warn-disk <number>

Sets the disk usage warning threshold as a percentage.

Default:

    80

    --warn-ram <number>

Sets the RAM usage warning threshold as a percentage.

Default:

    85

    --warn-gpu-temp <number>

Sets the GPU temperature warning threshold in Celsius.

Default:

    80

Generated Reports
-----------------

By default, generated reports are saved inside:

    system-reports/

Example text report filename:

    system_report_2026-05-08_114022.txt

Example JSON report filename:

    system_report_2026-05-08_114022.json

The repository includes:

    system-reports/example_report.txt

Generated timestamp reports are ignored by .gitignore so the repository does not fill up with repeated output files.

Notes
-----

This project was developed in WSL2.

Some hardware information may not be available from inside WSL. CPU temperature, CPU fan speed, motherboard fan speed, and some power limits may not be exposed to the Linux environment.

NVIDIA GPU information is available only when nvidia-smi is installed and working.

Warning thresholds are applied to the current snapshot report. This is not a live monitoring tool; it checks the system state at the moment the script is run.

Future Improvements
-------------------

- Add live monitoring mode
- Add optional repeated interval checks
- Add CSV export
- Add CPU temperature support for native Linux systems
- Add unit tests for helper functions
- Add configurable output folders