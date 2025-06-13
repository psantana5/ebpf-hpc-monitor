# eBPF HPC Monitor

An advanced monitoring system for HPC environments that uses eBPF to track process efficiency and integration with Slurm.

## Motivation

In High Performance Computing (HPC) environments, understanding job behavior and efficiency is crucial for resource optimization. This project provides a real-time monitoring tool that uses eBPF (extended Berkeley Packet Filter) to capture detailed performance metrics at the kernel level, enabling deep analysis of process behavior without significant overhead.

## Key Features

### eBPF Monitoring
- **Syscalls**: Tracking system calls (`read`, `write`, `send`, `recv`, etc.)
- **Scheduling**: Monitoring context switches and scheduling events
- **I/O**: Tracking input/output operations
- **Network**: Network traffic analysis and latencies

### Slurm Integration
- Automatic mapping of processes to Slurm jobs
- Job metadata extraction (user, partition, allocated resources)
- Support for multiple Slurm versions
- Fallback mode for non-Slurm environments

### Analysis and Classification
- **Automatic classification** of jobs (CPU-bound, I/O-bound, Idle-heavy)
- **Efficiency metrics** and optimization recommendations
- **Comparison** between jobs and users
- **Pattern detection** and anomalies

### Data Export
- Multiple formats: JSON, CSV, YAML
- Optional Prometheus integration
- Interactive dashboards
- Automated reports

## System Requirements

### Minimum Requirements
- **OS**: Linux (Ubuntu 18.04+, CentOS 7+, or similar)
- **Kernel**: 4.1+ (eBPF support required)
- **Python**: 3.7+
- **Privileges**: Root or CAP_SYS_ADMIN capabilities
- **Memory**: 4GB RAM (8GB+ recommended)

### Dependencies
- BCC (BPF Compiler Collection)
- Python packages: `bcc`, `psutil`, `pandas`, `numpy`, `click`, `rich`
- Optional: Slurm, Prometheus client

## Installation

### Quick Installation

```bash
# Clone the repository
git clone https://github.com/psantana5/ebpf-hpc-monitor.git
cd ebpf-hpc-monitor

# Install dependencies
pip3 install -r requirements.txt

# Install the package
sudo pip3 install -e .
```

### BCC Installation

**Ubuntu/Debian:**
```bash
sudo apt-get install bcc-tools libbcc-examples linux-headers-$(uname -r)
```

**CentOS/RHEL:**
```bash
sudo yum install bcc-tools bcc-devel
```

### Installation Verification

```bash
# Verify eBPF support
sudo python3 -c "from bcc import BPF; print('eBPF support: OK')"

# Verify Slurm integration (optional)
python3 -c "from scripts.slurm_integration import SlurmIntegration; print('Slurm available:', SlurmIntegration().check_slurm_availability())"
```

## Basic Usage

### User Monitoring

```bash
# Monitor all processes for a user
sudo python3 scripts/hpc_monitor.py --user username --duration 60

# With real-time visualization
sudo python3 scripts/hpc_monitor.py --user username --real-time --duration 120
```

### Specific Job Monitoring

```bash
# Monitor a specific Slurm job
sudo python3 scripts/hpc_monitor.py --job-id 12345 --duration 300

# Save results to file
sudo python3 scripts/hpc_monitor.py --job-id 12345 --output job_analysis.json
```

### Interactive Dashboard

```bash
# Launch real-time dashboard
sudo python3 examples/realtime_dashboard.py --user username

# Dashboard for multiple jobs
sudo python3 examples/realtime_dashboard.py --job-ids 12345,12346,12347
```

## Example Output

```json
{
  "monitoring_session": {
    "start_time": "2024-01-15T10:30:00Z",
    "end_time": "2024-01-15T10:35:00Z",
    "duration_seconds": 300,
    "monitored_pids": [1234, 5678, 9012]
  },
  "jobs": [
    {
      "job_id": "12345",
      "user": "researcher1",
      "job_name": "simulation_run",
      "partition": "compute",
      "metrics": {
        "cpu_percent": 78.5,
        "io_percent": 15.2,
        "wait_percent": 6.3,
        "total_syscalls": 45230,
        "context_switches": 2341,
        "total_io_bytes": 2147483648,
        "network_bytes_sent": 1048576,
        "network_bytes_recv": 2097152
      },
      "classification": {
        "type": "CPU-bound",
        "efficiency_score": 82.3,
        "recommendations": [
          "Job is well-optimized for CPU usage",
          "Consider using more CPU cores if available",
          "I/O usage is minimal, perfect for computational workloads"
        ]
      },
      "syscall_breakdown": {
        "read": 1250,
        "write": 890,
        "send": 45,
        "recv": 67
      }
    }
  ],
  "summary": {
    "total_jobs_monitored": 1,
    "average_efficiency": 82.3,
    "most_common_type": "CPU-bound",
    "total_monitoring_time": 300
  }
}
```

## Project Structure

```
ebpf-hpc-monitor/
├── README.md                    # This file
├── LICENSE                      # MIT License
├── requirements.txt             # Python dependencies
├── setup.py                     # Package configuration
├── config/
│   └── monitor_config.yaml      # Main configuration
├── scripts/
│   ├── hpc_monitor.py          # Main script
│   ├── ebpf_probes.py          # eBPF probe management
│   ├── slurm_integration.py    # Slurm integration
│   └── data_analyzer.py        # Data analysis
├── examples/
│   ├── basic_monitoring.py     # Basic examples
│   ├── job_profiling.py        # Job profiling
│   ├── multi_job_comparison.py # Job comparison
│   └── realtime_dashboard.py   # Interactive dashboard
├── data/
│   ├── sample_outputs/         # Sample data
│   └── test_data/              # Test data
├── docs/
│   ├── INSTALLATION.md         # Installation guide
│   └── USAGE.md                # Usage guide
└── tests/
    └── test_basic_functionality.py # Basic tests
```

## Advanced Configuration

### eBPF Configuration

```yaml
# config/monitor_config.yaml
ebpf:
  enabled: true
  probes:
    syscalls: true
    scheduling: true
    io_events: true
    network_events: true
  buffer_size: 256  # KB
  poll_timeout: 1000  # ms
```

### Prometheus Integration

```yaml
external_systems:
  prometheus:
    enabled: true
    port: 8000
    metrics_prefix: "hpc_monitor_"
```

### Custom Classification

```yaml
classification:
  cpu_bound_threshold: 70.0
  io_bound_threshold: 40.0
  idle_threshold: 60.0
  custom_rules:
    - name: "memory_intensive"
      condition: "memory_usage > 80"
```

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/new-feature`)
3. Commit your changes (`git commit -am 'Add new feature'`)
4. Push to the branch (`git push origin feature/new-feature`)
5. Create a Pull Request

### Development Guidelines

- Follow PEP 8 for Python code style
- Add tests for new functionality
- Update documentation as needed
- Ensure all tests pass

### Reporting Bugs

Please use GitHub Issues to report bugs, including:
- Operating system version
- Kernel version
- Python and BCC versions
- Steps to reproduce the issue
- Relevant error logs

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- **BCC Project**: For providing eBPF tools
- **Slurm**: For the workload management system
- **HPC Community**: For inspiration and feedback

## Contact

- **Author**: PAU SANTANA
- **Email**: pausantanapi2@gmail.com
- **GitHub**: [@psantana5](https://github.com/psantana5)
- **Project**: [ebpf-hpc-monitor](https://github.com/psantana5/ebpf-hpc-monitor)

---

**Note**: This project requires root privileges for eBPF operations. Use responsibly in production environments.