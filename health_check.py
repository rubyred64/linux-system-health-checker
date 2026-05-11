import argparse
import json
import os
import platform
import shutil
import subprocess
import time
from datetime import datetime


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPORTS_DIR = os.path.join(SCRIPT_DIR, "system-reports")


DEFAULT_DISK_WARNING = 80.0
DEFAULT_RAM_WARNING = 85.0
DEFAULT_GPU_TEMP_WARNING = 80.0


def bytes_to_gb_value(num_bytes):
    return num_bytes / (1024 ** 3)


def bytes_to_gb_string(num_bytes):
    return f"{bytes_to_gb_value(num_bytes):.2f} GB"


def mb_to_gb_value(num_mb):
    return num_mb / 1024


def clean_unavailable_value(value_text):
    return str(value_text).strip().replace("[", "").replace("]", "")


def is_unavailable(value_text):
    value = clean_unavailable_value(value_text).strip().upper()
    return value in ["N/A", "NA", "NONE", "UNKNOWN", ""]


def parse_float(value_text):
    value = clean_unavailable_value(value_text)

    if is_unavailable(value):
        return None

    try:
        return float(value)
    except ValueError:
        return None


def format_percent(value):
    if value is None:
        return "Unavailable"

    return f"{value:.1f}%"


def format_temperature(value):
    if value is None:
        return "Unavailable"

    return f"{value:.0f} C"


def format_watts(value):
    if value is None:
        return "Unavailable"

    return f"{value:.2f} W"


def format_gb(value):
    if value is None:
        return "Unavailable"

    return f"{value:.2f} GB"


def get_warning_label(value, threshold):
    if value is None:
        return ""

    if value >= threshold:
        return " WARNING"

    return ""


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
        return None

    time.sleep(0.5)

    second = read_cpu_times()

    if second is None:
        return None

    first_total, first_idle = first
    second_total, second_idle = second

    total_difference = second_total - first_total
    idle_difference = second_idle - first_idle

    if total_difference == 0:
        return None

    usage = (1 - (idle_difference / total_difference)) * 100

    return round(usage, 1)


def get_system_data():
    return {
        "os": platform.system(),
        "platform": platform.platform(),
        "machine": platform.machine()
    }


def get_cpu_data():
    load_average = None

    try:
        one_minute, five_minutes, fifteen_minutes = os.getloadavg()
        load_average = {
            "one_minute": round(one_minute, 2),
            "five_minutes": round(five_minutes, 2),
            "fifteen_minutes": round(fifteen_minutes, 2)
        }
    except Exception:
        pass

    cpu_count = os.cpu_count()

    return {
        "model": get_cpu_model(),
        "logical_cpus": cpu_count,
        "usage_percent": get_cpu_usage_percent(),
        "load_average": load_average
    }


def get_disk_data():
    total, used, free = shutil.disk_usage("/")
    percent_used = (used / total) * 100

    return {
        "total_gb": round(bytes_to_gb_value(total), 2),
        "used_gb": round(bytes_to_gb_value(used), 2),
        "free_gb": round(bytes_to_gb_value(free), 2),
        "usage_percent": round(percent_used, 1)
    }


def parse_meminfo_value(line):
    parts = line.split()

    if len(parts) < 2:
        return None

    kb = int(parts[1])
    bytes_value = kb * 1024

    return bytes_value


def get_memory_data():
    meminfo = read_file("/proc/meminfo")

    if meminfo is None:
        return {
            "available": False,
            "raw_output": run_command(["free", "-h"])
        }

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
        return {
            "available": False,
            "raw_output": run_command(["free", "-h"])
        }

    if available is None:
        available = free

    used = total - available
    percent_used = (used / total) * 100

    return {
        "available": True,
        "total_gb": round(bytes_to_gb_value(total), 2),
        "used_gb": round(bytes_to_gb_value(used), 2),
        "available_gb": round(bytes_to_gb_value(available), 2),
        "usage_percent": round(percent_used, 1)
    }


def get_uptime_data():
    return {
        "uptime": run_command(["uptime", "-p"])
    }


def get_ip_data():
    return {
        "ip_addresses": run_command(["hostname", "-I"])
    }


def get_top_processes_data():
    processes = run_command_shell("ps -eo pid,user,%cpu,%mem,comm --sort=-%mem | head -n 6")

    return {
        "raw_output": processes
    }


def get_gpu_data():
    if not command_exists("nvidia-smi"):
        return {
            "available": False,
            "message": "NVIDIA GPU data unavailable: nvidia-smi was not found."
        }

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
        return {
            "available": False,
            "message": output
        }

    gpus = []

    for gpu_line in output.splitlines():
        parts = [clean_unavailable_value(part) for part in gpu_line.split(",")]

        if len(parts) != 8:
            gpus.append({
                "parse_error": True,
                "raw_output": gpu_line
            })
            continue

        name = parts[0]
        temperature = parse_float(parts[1])
        gpu_utilization = parse_float(parts[2])
        memory_used_mb = parse_float(parts[3])
        memory_total_mb = parse_float(parts[4])
        fan_speed = parse_float(parts[5])
        power_draw = parse_float(parts[6])
        power_limit = parse_float(parts[7])

        memory_used_gb = None
        memory_total_gb = None

        if memory_used_mb is not None:
            memory_used_gb = round(mb_to_gb_value(memory_used_mb), 2)

        if memory_total_mb is not None:
            memory_total_gb = round(mb_to_gb_value(memory_total_mb), 2)

        gpus.append({
            "parse_error": False,
            "name": name,
            "temperature_c": temperature,
            "utilization_percent": gpu_utilization,
            "vram_used_gb": memory_used_gb,
            "vram_total_gb": memory_total_gb,
            "fan_speed_percent": fan_speed,
            "power_draw_watts": power_draw,
            "power_limit_watts": power_limit
        })

    return {
        "available": True,
        "gpus": gpus
    }


def get_sensor_data():
    if not command_exists("sensors"):
        return {
            "available": False,
            "message": "Sensor data unavailable: sensors command was not found. In WSL, CPU temperature and fan speed are often not exposed."
        }

    return {
        "available": True,
        "raw_output": run_command(["sensors"])
    }


def collect_report_data(args):
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    return {
        "generated_at": generated_at,
        "thresholds": {
            "disk_warning_percent": args.warn_disk,
            "ram_warning_percent": args.warn_ram,
            "gpu_temp_warning_c": args.warn_gpu_temp
        },
        "system": get_system_data(),
        "cpu": get_cpu_data(),
        "uptime": get_uptime_data(),
        "disk": get_disk_data(),
        "ram": get_memory_data(),
        "gpu": get_gpu_data(),
        "sensors": get_sensor_data(),
        "network": get_ip_data(),
        "top_processes": get_top_processes_data()
    }


def build_text_report(report_data):
    disk_warning = get_warning_label(
        report_data["disk"]["usage_percent"],
        report_data["thresholds"]["disk_warning_percent"]
    )

    ram_usage = None

    if report_data["ram"].get("available"):
        ram_usage = report_data["ram"]["usage_percent"]

    ram_warning = get_warning_label(
        ram_usage,
        report_data["thresholds"]["ram_warning_percent"]
    )

    cpu_load_average = report_data["cpu"]["load_average"]

    if cpu_load_average is None:
        load_average_text = "Unavailable"
    else:
        load_average_text = (
            f"{cpu_load_average['one_minute']:.2f}, "
            f"{cpu_load_average['five_minutes']:.2f}, "
            f"{cpu_load_average['fifteen_minutes']:.2f}"
        )

    lines = [
        "System Health Report",
        "====================",
        "",
        f"Generated At: {report_data['generated_at']}",
        "",
        "System Information",
        "------------------",
        f"OS: {report_data['system']['os']}",
        f"Platform: {report_data['system']['platform']}",
        f"Machine: {report_data['system']['machine']}",
        "",
        "CPU Information",
        "---------------",
        f"CPU Model: {report_data['cpu']['model']}",
        f"Logical CPUs: {report_data['cpu']['logical_cpus']}",
        f"CPU Usage Snapshot: {format_percent(report_data['cpu']['usage_percent'])}",
        f"Load Average 1/5/15 min: {load_average_text}",
        "",
        "Uptime",
        "------",
        report_data["uptime"]["uptime"],
        "",
        "Disk Usage",
        "----------",
        f"Total: {report_data['disk']['total_gb']:.2f} GB",
        f"Used: {report_data['disk']['used_gb']:.2f} GB",
        f"Free: {report_data['disk']['free_gb']:.2f} GB",
        f"Usage: {report_data['disk']['usage_percent']:.1f}%{disk_warning}",
        "",
    ]

    if report_data["ram"].get("available"):
        lines.extend([
            "RAM Usage",
            "---------",
            f"Total RAM: {report_data['ram']['total_gb']:.2f} GB",
            f"Used RAM: {report_data['ram']['used_gb']:.2f} GB",
            f"Available RAM: {report_data['ram']['available_gb']:.2f} GB",
            f"Usage: {report_data['ram']['usage_percent']:.1f}%{ram_warning}",
            "",
        ])
    else:
        lines.extend([
            "RAM Usage",
            "---------",
            report_data["ram"]["raw_output"],
            "",
        ])

    lines.extend(build_gpu_text_section(report_data))
    lines.extend(build_sensor_text_section(report_data))

    lines.extend([
        "IP Configuration",
        "----------------",
        report_data["network"]["ip_addresses"],
        "",
        "Top Processes by Memory",
        "-----------------------",
        report_data["top_processes"]["raw_output"],
        "",
    ])

    return "\n".join(lines)


def build_gpu_text_section(report_data):
    lines = [
        "GPU Information",
        "---------------"
    ]

    gpu_data = report_data["gpu"]

    if not gpu_data["available"]:
        lines.append(gpu_data["message"])
        lines.append("")
        return lines

    for index, gpu in enumerate(gpu_data["gpus"], start=1):
        if gpu.get("parse_error"):
            lines.append(f"GPU {index}: Unable to parse nvidia-smi output: {gpu['raw_output']}")
            lines.append("")
            continue

        gpu_temp_warning = get_warning_label(
            gpu["temperature_c"],
            report_data["thresholds"]["gpu_temp_warning_c"]
        )

        lines.append(f"GPU {index}: {gpu['name']}")
        lines.append(f"Temperature: {format_temperature(gpu['temperature_c'])}{gpu_temp_warning}")
        lines.append(f"GPU Load: {format_percent(gpu['utilization_percent'])}")
        lines.append(f"VRAM Used: {format_gb(gpu['vram_used_gb'])}")
        lines.append(f"VRAM Total: {format_gb(gpu['vram_total_gb'])}")
        lines.append(f"Fan Speed: {format_percent(gpu['fan_speed_percent'])}")
        lines.append(f"Power Draw: {format_watts(gpu['power_draw_watts'])}")
        lines.append(f"Power Limit: {format_watts(gpu['power_limit_watts'])}")

        if index != len(gpu_data["gpus"]):
            lines.append("")

    lines.append("")

    return lines


def build_sensor_text_section(report_data):
    lines = [
        "Temperature and Fan Sensors",
        "---------------------------"
    ]

    sensor_data = report_data["sensors"]

    if not sensor_data["available"]:
        lines.append(sensor_data["message"])
        lines.append("")
        return lines

    lines.append(sensor_data["raw_output"])
    lines.append("")

    return lines


def save_text_report(text_report, timestamp):
    os.makedirs(REPORTS_DIR, exist_ok=True)

    filename = f"system_report_{timestamp}.txt"
    file_path = os.path.join(REPORTS_DIR, filename)

    with open(file_path, "w", encoding="utf-8") as file:
        file.write(text_report)

    return file_path


def save_json_report(report_data, timestamp):
    os.makedirs(REPORTS_DIR, exist_ok=True)

    filename = f"system_report_{timestamp}.json"
    file_path = os.path.join(REPORTS_DIR, filename)

    with open(file_path, "w", encoding="utf-8") as file:
        json.dump(report_data, file, indent=2)

    return file_path


def get_report_timestamp():
    return datetime.now().strftime("%Y-%m-%d_%H%M%S")


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Generate a Linux/WSL system health report."
    )

    parser.add_argument(
        "--json",
        action="store_true",
        help="Save a JSON version of the report in addition to the text report."
    )

    parser.add_argument(
        "--no-save",
        action="store_true",
        help="Print the report without saving any report files."
    )

    parser.add_argument(
        "--warn-disk",
        type=float,
        default=DEFAULT_DISK_WARNING,
        help="Disk usage warning threshold percentage. Default: 80."
    )

    parser.add_argument(
        "--warn-ram",
        type=float,
        default=DEFAULT_RAM_WARNING,
        help="RAM usage warning threshold percentage. Default: 85."
    )

    parser.add_argument(
        "--warn-gpu-temp",
        type=float,
        default=DEFAULT_GPU_TEMP_WARNING,
        help="GPU temperature warning threshold in Celsius. Default: 80."
    )

    return parser.parse_args()


def main():
    args = parse_arguments()
    report_data = collect_report_data(args)
    text_report = build_text_report(report_data)
    timestamp = get_report_timestamp()

    print(text_report)

    if args.no_save:
        print("Report not saved because --no-save was used.")
        return

    if args.json:
        json_path = save_json_report(report_data, timestamp)
        print(f"Report saved to: {json_path}")
    else:
        text_path = save_text_report(text_report, timestamp)
        print(f"Report saved to: {text_path}")


if __name__ == "__main__":
    main()