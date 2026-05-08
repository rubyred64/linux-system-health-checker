import os
import platform
import shutil
import subprocess
import time
from datetime import datetime


def bytes_to_gb(num_bytes):
    gb = num_bytes / (1024 ** 3)
    return f"{gb:.2f} GB"


def clean_unavailable_value(value_text):
    return value_text.strip().replace("[", "").replace("]", "")


def is_unavailable(value_text):
    value = clean_unavailable_value(value_text).strip().upper()
    return value in ["N/A", "NA", "NONE", "UNKNOWN", ""]


def mb_to_gb_string(num_mb_text):
    value = clean_unavailable_value(num_mb_text)

    if is_unavailable(value):
        return "Unavailable"

    try:
        num_mb = int(value)
        gb = num_mb / 1024
        return f"{gb:.2f} GB"
    except ValueError:
        return "Unavailable"


def format_percent(value_text):
    value = clean_unavailable_value(value_text)

    if is_unavailable(value):
        return "Unavailable"

    return f"{value}%"


def format_temperature(value_text):
    value = clean_unavailable_value(value_text)

    if is_unavailable(value):
        return "Unavailable"

    return f"{value} C"


def format_watts(value_text):
    value = clean_unavailable_value(value_text)

    if is_unavailable(value):
        return "Unavailable"

    return f"{value} W"


def run_command(command):
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True
        )

        output = result.stdout.strip()

        if output == "":
            return "No output returned"

        return output

    except FileNotFoundError:
        return f"Command not found: {command[0]}"

    except subprocess.CalledProcessError as error:
        error_text = error.stderr.strip()

        if error_text == "":
            error_text = "No error details returned"

        return f"Command failed: {' '.join(command)}\nError: {error_text}"

    except Exception as error:
        return f"Unexpected error while running command: {error}"


def run_command_shell(command):
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True,
            shell=True
        )

        output = result.stdout.strip()

        if output == "":
            return "No output returned"

        return output

    except subprocess.CalledProcessError as error:
        error_text = error.stderr.strip()

        if error_text == "":
            error_text = "No error details returned"

        return f"Command failed: {command}\nError: {error_text}"

    except Exception as error:
        return f"Unexpected error while running shell command: {error}"


def command_exists(command_name):
    result = subprocess.run(
        ["which", command_name],
        capture_output=True,
        text=True
    )

    return result.returncode == 0


def read_file(file_path):
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            return file.read()

    except FileNotFoundError:
        return None

    except Exception as error:
        return f"Error reading {file_path}: {error}"


def get_cpu_model():
    cpuinfo = read_file("/proc/cpuinfo")

    if cpuinfo is None:
        return "Unavailable"

    for line in cpuinfo.splitlines():
        if line.lower().startswith("model name"):
            parts = line.split(":", 1)

            if len(parts) == 2:
                return parts[1].strip()

    return platform.processor() or "Unavailable"


def get_cpu_core_info():
    cpu_count = os.cpu_count()

    if cpu_count is None:
        return "Unavailable"

    return str(cpu_count)


def read_cpu_times():
    stat = read_file("/proc/stat")

    if stat is None:
        return None

    first_line = stat.splitlines()[0]
    parts = first_line.split()

    if len(parts) < 5 or parts[0] != "cpu":
        return None

    values = []

    for value in parts[1:]:
        values.append(int(value))

    idle = values[3]

    if len(values) > 4:
        idle += values[4]

    total = sum(values)

    return total, idle


def get_cpu_usage_percent():
    first = read_cpu_times()

    if first is None:
        return "Unavailable"

    time.sleep(0.2)

    second = read_cpu_times()

    if second is None:
        return "Unavailable"

    first_total, first_idle = first
    second_total, second_idle = second

    total_difference = second_total - first_total
    idle_difference = second_idle - first_idle

    if total_difference == 0:
        return "Unavailable"

    usage = (1 - (idle_difference / total_difference)) * 100

    return f"{usage:.1f}%"


def get_system_info():
    lines = [
        "System Information",
        "------------------",
        f"OS: {platform.system()}",
        f"Platform: {platform.platform()}",
        f"Machine: {platform.machine()}",
    ]

    return "\n".join(lines)


def get_cpu_info():
    load_average = "Unavailable"

    try:
        one_minute, five_minutes, fifteen_minutes = os.getloadavg()
        load_average = f"{one_minute:.2f}, {five_minutes:.2f}, {fifteen_minutes:.2f}"
    except Exception:
        pass

    lines = [
        "CPU Information",
        "---------------",
        f"CPU Model: {get_cpu_model()}",
        f"Logical CPUs: {get_cpu_core_info()}",
        f"CPU Usage Snapshot: {get_cpu_usage_percent()}",
        f"Load Average 1/5/15 min: {load_average}",
    ]

    return "\n".join(lines)


def get_disk_usage():
    total, used, free = shutil.disk_usage("/")

    percent_used = (used / total) * 100

    lines = [
        "Disk Usage",
        "----------",
        f"Total: {bytes_to_gb(total)}",
        f"Used: {bytes_to_gb(used)}",
        f"Free: {bytes_to_gb(free)}",
        f"Usage: {percent_used:.1f}%",
    ]

    return "\n".join(lines)


def parse_meminfo_value(line):
    parts = line.split()

    if len(parts) < 2:
        return None

    kb = int(parts[1])
    bytes_value = kb * 1024

    return bytes_value


def get_memory_usage():
    meminfo = read_file("/proc/meminfo")

    if meminfo is None:
        memory_info = run_command(["free", "-h"])

        lines = [
            "Memory Usage",
            "------------",
            memory_info,
        ]

        return "\n".join(lines)

    total = None
    available = None
    free = None

    for line in meminfo.splitlines():
        if line.startswith("MemTotal:"):
            total = parse_meminfo_value(line)
        elif line.startswith("MemAvailable:"):
            available = parse_meminfo_value(line)
        elif line.startswith("MemFree:"):
            free = parse_meminfo_value(line)

    if total is None:
        memory_info = run_command(["free", "-h"])

        lines = [
            "Memory Usage",
            "------------",
            memory_info,
        ]

        return "\n".join(lines)

    if available is None:
        available = free

    used = total - available
    percent_used = (used / total) * 100

    lines = [
        "RAM Usage",
        "---------",
        f"Total RAM: {bytes_to_gb(total)}",
        f"Used RAM: {bytes_to_gb(used)}",
        f"Available RAM: {bytes_to_gb(available)}",
        f"Usage: {percent_used:.1f}%",
    ]

    return "\n".join(lines)


def get_uptime():
    uptime = run_command(["uptime", "-p"])

    lines = [
        "Uptime",
        "------",
        uptime,
    ]

    return "\n".join(lines)


def get_ip_config():
    ip_info = run_command(["hostname", "-I"])

    lines = [
        "IP Configuration",
        "----------------",
        ip_info,
    ]

    return "\n".join(lines)


def get_top_processes():
    processes = run_command_shell("ps -eo pid,user,%cpu,%mem,comm --sort=-%mem | head -n 6")

    lines = [
        "Top Processes by Memory",
        "-----------------------",
        processes,
    ]

    return "\n".join(lines)


def get_gpu_info():
    if not command_exists("nvidia-smi"):
        lines = [
            "GPU Information",
            "---------------",
            "NVIDIA GPU data unavailable: nvidia-smi was not found.",
            "If this machine has an NVIDIA GPU, install/configure NVIDIA driver support for WSL.",
        ]

        return "\n".join(lines)

    query = (
        "name,"
        "temperature.gpu,"
        "utilization.gpu,"
        "memory.used,"
        "memory.total,"
        "fan.speed,"
        "power.draw,"
        "power.limit"
    )

    command = [
        "nvidia-smi",
        f"--query-gpu={query}",
        "--format=csv,noheader,nounits"
    ]

    output = run_command(command)

    if output.startswith("Command failed") or output.startswith("Unexpected error"):
        lines = [
            "GPU Information",
            "---------------",
            output,
        ]

        return "\n".join(lines)

    lines = [
        "GPU Information",
        "---------------",
    ]

    gpu_lines = output.splitlines()

    for index, gpu_line in enumerate(gpu_lines, start=1):
        parts = [clean_unavailable_value(part) for part in gpu_line.split(",")]

        if len(parts) != 8:
            lines.append(f"GPU {index}: Unable to parse nvidia-smi output: {gpu_line}")
            continue

        name = parts[0]
        temperature = parts[1]
        gpu_utilization = parts[2]
        memory_used = parts[3]
        memory_total = parts[4]
        fan_speed = parts[5]
        power_draw = parts[6]
        power_limit = parts[7]

        lines.append(f"GPU {index}: {name}")
        lines.append(f"Temperature: {format_temperature(temperature)}")
        lines.append(f"GPU Load: {format_percent(gpu_utilization)}")
        lines.append(f"VRAM Used: {mb_to_gb_string(memory_used)}")
        lines.append(f"VRAM Total: {mb_to_gb_string(memory_total)}")
        lines.append(f"Fan Speed: {format_percent(fan_speed)}")
        lines.append(f"Power Draw: {format_watts(power_draw)}")
        lines.append(f"Power Limit: {format_watts(power_limit)}")

        if index != len(gpu_lines):
            lines.append("")

    return "\n".join(lines)


def get_sensor_info():
    if not command_exists("sensors"):
        lines = [
            "Temperature and Fan Sensors",
            "---------------------------",
            "Sensor data unavailable: sensors command was not found.",
            "In native Linux this usually comes from lm-sensors.",
            "In WSL, CPU temperature and fan speed are often not exposed.",
        ]

        return "\n".join(lines)

    sensor_output = run_command(["sensors"])

    lines = [
        "Temperature and Fan Sensors",
        "---------------------------",
        sensor_output,
    ]

    return "\n".join(lines)


def build_report():
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    sections = [
        "System Health Report",
        "====================",
        "",
        f"Generated At: {generated_at}",
        "",
        get_system_info(),
        "",
        get_cpu_info(),
        "",
        get_uptime(),
        "",
        get_disk_usage(),
        "",
        get_memory_usage(),
        "",
        get_gpu_info(),
        "",
        get_sensor_info(),
        "",
        get_ip_config(),
        "",
        get_top_processes(),
        "",
    ]

    return "\n".join(sections)


def save_report(report):
    script_folder = os.path.dirname(os.path.abspath(__file__))
    reports_folder = os.path.join(script_folder, "system-reports")

    os.makedirs(reports_folder, exist_ok=True)

    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    filename = f"system_report_{timestamp}.txt"
    file_path = os.path.join(reports_folder, filename)

    with open(file_path, "w", encoding="utf-8") as file:
        file.write(report)

    return file_path


def main():
    report = build_report()
    file_path = save_report(report)

    print(report)
    print(f"Report saved to: {file_path}")


if __name__ == "__main__":
    main()