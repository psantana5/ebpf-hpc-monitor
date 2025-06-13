# eBPF HPC Monitor Docker Image
# This Dockerfile creates a containerized environment for the eBPF HPC Monitor
# Note: Requires privileged mode and host access for eBPF functionality

FROM ubuntu:22.04

# Metadata
LABEL maintainer="pausantanapi2@gmail.com"
LABEL description="eBPF-based HPC process monitoring tool"
LABEL version="1.0.0"

# Avoid interactive prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    # Core system tools
    curl \
    wget \
    git \
    vim \
    htop \
    # Python and development tools
    python3 \
    python3-pip \
    python3-dev \
    python3-venv \
    # Build tools
    build-essential \
    cmake \
    clang \
    llvm \
    # Kernel and eBPF dependencies
    linux-headers-generic \
    libbpf-dev \
    # BCC dependencies
    libbcc-dev \
    python3-bcc \
    bcc-tools \
    # Additional utilities
    procps \
    psmisc \
    lsof \
    strace \
    # Cleanup
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Create application directory
WORKDIR /app

# Create non-root user for development (monitor will still need root for eBPF)
RUN useradd -m -s /bin/bash monitor && \
    usermod -aG sudo monitor

# Copy requirements first for better Docker layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Install the package in development mode
RUN pip3 install -e .

# Create necessary directories
RUN mkdir -p /app/logs /app/output /app/data/monitoring_sessions

# Set proper permissions
RUN chown -R monitor:monitor /app

# Create entrypoint script
RUN cat > /app/entrypoint.sh << 'EOF'
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
    python3 -c "from bcc import BPF; print('BCC import: OK')" 2>/dev/null || {
        echo "Error: BCC not properly installed or accessible"
        exit 1
    }
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
EOF

# Make entrypoint executable
RUN chmod +x /app/entrypoint.sh

# Create a simple health check script
RUN cat > /app/healthcheck.sh << 'EOF'
#!/bin/bash
# Simple health check for the container

# Check if Python can import required modules
python3 -c "import sys; sys.path.insert(0, '/app/scripts'); from ebpf_probes import EBPFProbeManager" 2>/dev/null || exit 1

# Check if BCC is working
python3 -c "from bcc import BPF" 2>/dev/null || exit 1

echo "Health check passed"
exit 0
EOF

RUN chmod +x /app/healthcheck.sh

# Set up health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD /app/healthcheck.sh

# Expose port for Prometheus metrics (if enabled)
EXPOSE 8000

# Set working directory
WORKDIR /app

# Use the entrypoint script
ENTRYPOINT ["/app/entrypoint.sh"]

# Default command (can be overridden)
CMD []

# Add some helpful labels for container management
LABEL org.opencontainers.image.title="eBPF HPC Monitor"
LABEL org.opencontainers.image.description="Monitor HPC job efficiency using eBPF"
LABEL org.opencontainers.image.url="https://github.com/yourusername/ebpf-hpc-monitor"
LABEL org.opencontainers.image.documentation="https://github.com/yourusername/ebpf-hpc-monitor/blob/main/README.md"
LABEL org.opencontainers.image.source="https://github.com/yourusername/ebpf-hpc-monitor"
LABEL org.opencontainers.image.licenses="MIT"

# Environment variables for configuration
ENV HPC_MONITOR_CONFIG_PATH=/app/config/monitor_config.yaml
ENV HPC_MONITOR_LOG_LEVEL=INFO
ENV HPC_MONITOR_OUTPUT_DIR=/app/output

# Create volume mount points
VOLUME ["/app/output", "/app/logs", "/app/config"]

# Final setup as monitor user for non-privileged operations
# Note: eBPF operations will still require root privileges
USER root

# Add some useful aliases and environment setup
RUN echo 'alias ll="ls -la"' >> /root/.bashrc && \
    echo 'alias monitor="python3 /app/scripts/hpc_monitor.py"' >> /root/.bashrc && \
    echo 'alias dashboard="python3 /app/examples/realtime_dashboard.py"' >> /root/.bashrc && \
    echo 'export PATH="/app/scripts:$PATH"' >> /root/.bashrc

# Add completion and helpful functions
RUN cat >> /root/.bashrc << 'EOF'

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

EOF

echo "Docker image build complete!"
echo "Run with: docker run --privileged --pid=host --net=host -v /sys/kernel/debug:/sys/kernel/debug:rw -v /lib/modules:/lib/modules:ro ebpf-hpc-monitor"