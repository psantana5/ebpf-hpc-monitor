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
    # Additional utilities
    procps \
    psmisc \
    lsof \
    strace \
    libcap2-bin \
    # Cleanup
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install BCC from pip (more reliable than apt packages)
RUN pip3 install bcc

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

# Copy entrypoint and healthcheck scripts
COPY entrypoint.sh /app/entrypoint.sh
COPY healthcheck.sh /app/healthcheck.sh

# Make scripts executable
RUN chmod +x /app/entrypoint.sh /app/healthcheck.sh

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
COPY bashrc_functions.sh /tmp/bashrc_functions.sh
RUN cat /tmp/bashrc_functions.sh >> /root/.bashrc && rm /tmp/bashrc_functions.sh

RUN echo "Docker image build complete!" && \
    echo "Run with: docker run --privileged --pid=host --net=host -v /sys/kernel/debug:/sys/kernel/debug:rw -v /lib/modules:/lib/modules:ro ebpf-hpc-monitor"