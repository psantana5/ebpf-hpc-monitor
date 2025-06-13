# eBPF HPC Monitor helper functions
monitor_user() {
    if [ -z "$1" ]; then
        echo "Usage: monitor_user <username> [duration]"
        return 1
    fi
    local duration=${2:-60}
    python3 /app/scripts/hpc_monitor.py --user "$1" --duration "$duration"
}

monitor_job() {
    if [ -z "$1" ]; then
        echo "Usage: monitor_job <job_id> [duration]"
        return 1
    fi
    local duration=${2:-300}
    python3 /app/scripts/hpc_monitor.py --job-id "$1" --duration "$duration"
}

show_examples() {
    echo "Available monitoring examples:"
    echo "  monitor_user <username> [duration]  - Monitor user processes"
    echo "  monitor_job <job_id> [duration]     - Monitor specific job"
    echo "  python3 examples/basic_monitoring.py - Run basic examples"
    echo "  python3 examples/realtime_dashboard.py --user <username> - Interactive dashboard"
    echo "  python3 examples/job_profiling.py --job-id <id> - Detailed job profiling"
}