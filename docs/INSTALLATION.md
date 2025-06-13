# Installation Guide

## Prerequisites

### System Requirements

- **Operating System**: Linux (Ubuntu 18.04+, CentOS 7+, or similar)
- **Kernel Version**: 4.1+ (eBPF support required)
- **Architecture**: x86_64
- **Memory**: Minimum 4GB RAM (8GB+ recommended for HPC environments)
- **Storage**: 1GB free space for installation and logs

### Required Privileges

- **Root access** or sudo privileges (required for eBPF operations)
- **CAP_SYS_ADMIN** capability for eBPF program loading
- **CAP_SYS_PTRACE** capability for process monitoring

### Software Dependencies

#### Core Dependencies

```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install -y \
    python3 \
    python3-pip \
    python3-dev \
    build-essential \
    linux-headers-$(uname -r) \
    libbpf-dev \
    clang \
    llvm

# CentOS/RHEL
sudo yum install -y \
    python3 \
    python3-pip \
    python3-devel \
    gcc \
    kernel-devel \
    kernel-headers \
    clang \
    llvm
```

#### BCC (BPF Compiler Collection)

**Ubuntu/Debian:**
```bash
# Add the official BCC repository
echo "deb [trusted=yes] https://repo.iovisor.org/apt/$(lsb_release -cs) $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/iovisor.list
sudo apt-get update
sudo apt-get install -y bcc-tools libbcc-examples linux-headers-$(uname -r)
```

**CentOS/RHEL:**
```bash
# Install from EPEL
sudo yum install -y epel-release
sudo yum install -y bcc-tools bcc-devel
```

**From Source (if packages not available):**
```bash
git clone https://github.com/iovisor/bcc.git
cd bcc
mkdir build && cd build
cmake ..
make
sudo make install
cd src/python/
make
sudo make install
```

## Installation Methods

### Method 1: Direct Installation (Recommended)

1. **Clone the repository:**
   ```bash
   git clone https://github.com/psantana5/ebpf-hpc-monitor.git
   cd ebpf-hpc-monitor
   ```

2. **Install Python dependencies:**
   ```bash
   pip3 install -r requirements.txt
   ```

3. **Install the package:**
   ```bash
   sudo pip3 install -e .
   ```

4. **Verify installation:**
   ```bash
   sudo python3 -c "from scripts.ebpf_probes import EBPFProbeManager; print('eBPF support: OK')"
   ```

### Method 2: Virtual Environment Installation

1. **Create virtual environment:**
   ```bash
   python3 -m venv hpc-monitor-env
   source hpc-monitor-env/bin/activate
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   pip install -e .
   ```

3. **Note**: You'll still need to run with sudo for eBPF operations:
   ```bash
   sudo /path/to/hpc-monitor-env/bin/python scripts/hpc_monitor.py
   ```

### Method 3: Docker Installation (Experimental)

1. **Build Docker image:**
   ```bash
   docker build -t ebpf-hpc-monitor .
   ```

2. **Run with required privileges:**
   ```bash
   docker run --privileged --pid=host --net=host \
     -v /sys/kernel/debug:/sys/kernel/debug:rw \
     -v /lib/modules:/lib/modules:ro \
     -v /usr/src:/usr/src:ro \
     ebpf-hpc-monitor
   ```

## Slurm Integration Setup

### If Slurm is Available

1. **Verify Slurm installation:**
   ```bash
   squeue --version
   sacct --version
   ```

2. **Configure Slurm access:**
   ```bash
   # Ensure the monitoring user has access to Slurm commands
   sudo usermod -a -G slurm monitoring_user
   ```

3. **Test Slurm integration:**
   ```bash
   python3 -c "from scripts.slurm_integration import SlurmIntegration; s=SlurmIntegration(); print('Slurm available:', s.check_slurm_availability())"
   ```

### If Slurm is Not Available

The monitor can work in fallback mode using process inspection:

1. **Enable fallback mode in configuration:**
   ```yaml
   # config/monitor_config.yaml
   slurm:
     enabled: true
     fallback_mode: true
   ```

2. **Test fallback mode:**
   ```bash
   python3 scripts/hpc_monitor.py --user $(whoami) --duration 30
   ```

## Configuration

### Basic Configuration

1. **Copy the default configuration:**
   ```bash
   cp config/monitor_config.yaml config/my_config.yaml
   ```

2. **Edit configuration as needed:**
   ```bash
   nano config/my_config.yaml
   ```

3. **Key settings to review:**
   - eBPF buffer sizes
   - Slurm command paths
   - Output formats
   - Logging levels

### Advanced Configuration

#### eBPF Tuning
```yaml
ebpf:
  buffer_size: 256  # KB - increase for high-activity systems
  poll_timeout: 1000  # ms - adjust based on update frequency needs
  max_events_per_second: 10000  # Limit to prevent overload
```

#### Slurm Integration
```yaml
slurm:
  commands:
    squeue: "/usr/bin/squeue"  # Full path if not in PATH
    sacct: "/usr/bin/sacct"
    sstat: "/usr/bin/sstat"
  accounting_fields:
    - JobID
    - User
    - JobName
    - Partition
    - State
    - CPUTime
    - MaxRSS
```

## Verification

### Test eBPF Functionality

```bash
# Test 1: Check eBPF support
sudo python3 -c "
from bcc import BPF
print('BCC version:', BPF.kernel_struct_has_field('task_struct', 'pid'))
"

# Test 2: Load a simple eBPF program
sudo python3 scripts/ebpf_probes.py --test

# Test 3: Monitor current shell
sudo python3 scripts/hpc_monitor.py --user $(whoami) --duration 10
```

### Test Slurm Integration

```bash
# Test 1: Check Slurm availability
python3 -c "from scripts.slurm_integration import SlurmIntegration; print(SlurmIntegration().check_slurm_availability())"

# Test 2: List running jobs (if any)
python3 -c "from scripts.slurm_integration import SlurmIntegration; print(SlurmIntegration().get_running_jobs())"
```

### Run Basic Tests

```bash
# Run the test suite
python3 tests/test_basic_functionality.py

# Run example scripts
sudo python3 examples/basic_monitoring.py
```

## Troubleshooting

### Common Issues

#### 1. Permission Denied Errors
```bash
# Error: Operation not permitted
# Solution: Ensure running as root
sudo python3 scripts/hpc_monitor.py

# Or check capabilities
sudo setcap cap_sys_admin,cap_sys_ptrace+ep /usr/bin/python3
```

#### 2. BCC Import Errors
```bash
# Error: No module named 'bcc'
# Solution: Install BCC properly
sudo apt-get install python3-bcc  # Ubuntu
# or
sudo yum install python3-bcc      # CentOS
```

#### 3. Kernel Headers Missing
```bash
# Error: Could not find kernel headers
# Solution: Install kernel headers
sudo apt-get install linux-headers-$(uname -r)  # Ubuntu
sudo yum install kernel-devel kernel-headers    # CentOS
```

#### 4. eBPF Program Load Failures
```bash
# Check kernel eBPF support
zcat /proc/config.gz | grep BPF

# Should show:
# CONFIG_BPF=y
# CONFIG_BPF_SYSCALL=y
# CONFIG_BPF_JIT=y
```

#### 5. Slurm Command Not Found
```bash
# Add Slurm to PATH or specify full paths in config
export PATH=$PATH:/usr/local/slurm/bin

# Or edit config/monitor_config.yaml:
slurm:
  commands:
    squeue: "/usr/local/slurm/bin/squeue"
```

### Debug Mode

Enable debug logging for troubleshooting:

```bash
# Edit config file
logging:
  level: "DEBUG"
  
# Or use command line
sudo python3 scripts/hpc_monitor.py --verbose --debug
```

### Log Files

Check log files for detailed error information:

```bash
# Default log locations
tail -f /var/log/hpc_monitor.log
tail -f /var/log/hpc_monitor_errors.log

# Or custom locations from config
tail -f /path/to/your/logfile.log
```

## Performance Tuning

### For High-Activity Systems

```yaml
# Increase buffer sizes
ebpf:
  buffer_size: 512  # KB
  max_events_per_second: 50000

# Reduce update frequency
performance:
  update_interval: 5.0  # seconds
  batch_size: 1000
```

### For Resource-Constrained Systems

```yaml
# Reduce buffer sizes
ebpf:
  buffer_size: 64   # KB
  max_events_per_second: 1000

# Limit monitoring scope
performance:
  limits:
    max_pids: 100
    max_memory_mb: 256
```

## Next Steps

After successful installation:

1. **Read the [Usage Guide](USAGE.md)** for detailed usage instructions
2. **Review [Configuration Guide](CONFIGURATION.md)** for advanced settings
3. **Check [Examples](../examples/)** for practical use cases
4. **Set up monitoring** for your specific HPC workloads

## Getting Help

If you encounter issues:

1. Check the [Troubleshooting](#troubleshooting) section above
2. Review the [FAQ](FAQ.md)
3. Search existing [GitHub Issues](https://github.com/yourusername/ebpf-hpc-monitor/issues)
4. Create a new issue with:
   - System information (`uname -a`, `lsb_release -a`)
   - Error messages and logs
   - Steps to reproduce the problem