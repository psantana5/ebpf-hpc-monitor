#!/bin/bash
set -e

# Function to check if running with required privileges
check_privileges() {
    if [ "$(id -u)" != "0" ]; then
        echo "Warning: Not running as root. eBPF functionality may be limited."
        echo "Run with: docker run --privileged ..."
    fi
    
    # Check for required capabilities
    if ! capsh --print | grep -q "cap_sys_admin"; then
        echo "Warning: CAP_SYS_ADMIN capability not available"
    fi
}

# Function to check eBPF support
check_ebpf_support() {
    echo "Checking eBPF support..."
    
    # Check if /sys/kernel/debug is mounted
    if [ ! -d "/sys/kernel/debug/tracing" ]; then
        echo "Warning: /sys/kernel/debug/tracing not available"
        echo "Mount with: -v /sys/kernel/debug:/sys/kernel/debug:rw"
    fi
    
    # Check if kernel modules are available
    if [ ! -d "/lib/modules/$(uname -r)" ]; then
        echo "Warning: Kernel modules not available"
        echo "Mount with: -v /lib/modules:/lib/modules:ro"
    fi
    
    # Test BCC import
    echo "Testing BCC installation..."
    if python3 -c "from bcc import BPF; print('BCC import: OK')" 2>/dev/null; then
        echo "BCC is properly installed and accessible"
    else
        echo "Warning: BCC import failed. Checking installation..."
        python3 -c "import bcc; print(f'BCC version: {bcc.__version__}')" 2>/dev/null || {
            echo "Error: BCC package not found. Please check installation."
            echo "Continuing anyway - some features may not work."
        }
    fi
}

# Function to setup Slurm integration
setup_slurm() {
    # Check if Slurm commands are available in the host
    if command -v squeue >/dev/null 2>&1; then
        echo "Slurm commands detected"
    else
        echo "Slurm not detected - will use fallback mode"
    fi
}

# Main execution
echo "=== eBPF HPC Monitor Container ==="
echo "Starting container initialization..."

check_privileges
check_ebpf_support
setup_slurm

echo "Container ready!"
echo ""
echo "Usage examples:"
echo "  # Monitor user processes:"
echo "  python3 scripts/hpc_monitor.py --user username --duration 60"
echo ""
echo "  # Monitor specific job:"
echo "  python3 scripts/hpc_monitor.py --job-id 12345 --duration 300"
echo ""
echo "  # Run interactive dashboard:"
echo "  python3 examples/realtime_dashboard.py --user username"
echo ""

# Execute the command passed to docker run, or start interactive shell
if [ "$#" -eq 0 ]; then
    echo "Starting interactive shell..."
    exec /bin/bash
else
    echo "Executing: $@"
    exec "$@"
fi