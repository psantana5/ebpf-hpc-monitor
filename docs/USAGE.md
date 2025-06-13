# Usage Guide

## Quick Start

### Basic Monitoring

```bash
# Monitor all processes for a specific user
sudo python3 scripts/hpc_monitor.py --user username --duration 60

# Monitor a specific Slurm job
sudo python3 scripts/hpc_monitor.py --job-id 12345 --duration 300

# Monitor with real-time display
sudo python3 scripts/hpc_monitor.py --user username --real-time --duration 120
```

### Output Examples

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
        "total_io_bytes": 2147483648
      },
      "classification": {
        "type": "CPU-bound",
        "efficiency_score": 82.3,
        "recommendations": [
          "Job is well-optimized for CPU usage",
          "Consider using more CPU cores if available"
        ]
      }
    }
  ]
}
```

## Command Line Interface

### Main Script: `hpc_monitor.py`

```bash
sudo python3 scripts/hpc_monitor.py [OPTIONS]
```

#### Required Arguments (one of):
- `--job-id JOB_ID`: Monitor specific Slurm job ID
- `--user USERNAME`: Monitor all processes for a user

#### Optional Arguments:
- `--duration SECONDS`: Monitoring duration (default: 60)
- `--output FILE`: Output file path (default: stdout)
- `--config FILE`: Configuration file path
- `--real-time`: Enable real-time display
- `--filter FILTER`: Process filter (cpu|io|network)
- `--verbose`: Enable verbose logging
- `--format FORMAT`: Output format (json|csv|yaml)

#### Examples:

```bash
# Monitor job 12345 for 5 minutes, save to file
sudo python3 scripts/hpc_monitor.py \
  --job-id 12345 \
  --duration 300 \
  --output /tmp/job_12345_analysis.json

# Monitor user 'researcher1' with real-time display
sudo python3 scripts/hpc_monitor.py \
  --user researcher1 \
  --real-time \
  --duration 120

# Monitor with custom configuration
sudo python3 scripts/hpc_monitor.py \
  --user researcher1 \
  --config config/my_config.yaml \
  --verbose

# Monitor only I/O-intensive processes
sudo python3 scripts/hpc_monitor.py \
  --user researcher1 \
  --filter io \
  --duration 180
```

## Example Scripts

### Basic Monitoring (`examples/basic_monitoring.py`)

```bash
# Run all basic examples
sudo python3 examples/basic_monitoring.py

# Monitor specific user
sudo python3 -c "
from examples.basic_monitoring import monitor_user_processes
monitor_user_processes('username', duration=60)
"
```

### Job Profiling (`examples/job_profiling.py`)

```bash
# Profile a specific job with detailed analysis
sudo python3 examples/job_profiling.py \
  --job-id 12345 \
  --duration 300 \
  --detailed

# Profile with custom configuration
sudo python3 examples/job_profiling.py \
  --job-id 12345 \
  --config config/my_config.yaml
```

### Multi-Job Comparison (`examples/multi_job_comparison.py`)

```bash
# Compare jobs from JSON files
python3 examples/multi_job_comparison.py \
  --files job1.json job2.json job3.json \
  --output-dir /tmp/comparison_results

# Compare all jobs for a user
python3 examples/multi_job_comparison.py \
  --user researcher1 \
  --output-dir /tmp/user_analysis
```

### Real-time Dashboard (`examples/realtime_dashboard.py`)

```bash
# Monitor specific jobs with interactive dashboard
sudo python3 examples/realtime_dashboard.py \
  --job-ids 12345,12346,12347 \
  --update-interval 2

# Monitor all jobs for a user
sudo python3 examples/realtime_dashboard.py \
  --user researcher1 \
  --update-interval 5
```

## Configuration

### Configuration File Structure

The monitor uses YAML configuration files. The main configuration file is `config/monitor_config.yaml`.

#### Key Sections:

```yaml
# eBPF probe configuration
ebpf:
  enabled: true
  probes:
    syscalls: true
    scheduling: true
    io_events: true
    network_events: true
  buffer_size: 256  # KB
  poll_timeout: 1000  # ms

# Slurm integration
slurm:
  enabled: true
  fallback_mode: true
  commands:
    squeue: "squeue"
    sacct: "sacct"
    sstat: "sstat"

# Job classification thresholds
classification:
  cpu_bound_threshold: 70.0
  io_bound_threshold: 40.0
  idle_threshold: 60.0

# Output configuration
output:
  format: "json"  # json, csv, yaml
  include_raw_events: false
  compress_output: false
```

### Custom Configuration

1. **Copy the default configuration:**
   ```bash
   cp config/monitor_config.yaml config/my_config.yaml
   ```

2. **Edit as needed:**
   ```bash
   nano config/my_config.yaml
   ```

3. **Use with monitoring:**
   ```bash
   sudo python3 scripts/hpc_monitor.py \
     --config config/my_config.yaml \
     --user username
   ```

## Monitoring Scenarios

### Scenario 1: Job Performance Analysis

**Goal**: Analyze the performance characteristics of a specific job.

```bash
# Step 1: Monitor the job
sudo python3 scripts/hpc_monitor.py \
  --job-id 12345 \
  --duration 600 \
  --output job_12345_analysis.json

# Step 2: Analyze the results
python3 scripts/data_analyzer.py \
  --input job_12345_analysis.json \
  --output job_12345_report.csv

# Step 3: Generate detailed profile
sudo python3 examples/job_profiling.py \
  --job-id 12345 \
  --detailed
```

### Scenario 2: User Workload Characterization

**Goal**: Understand the workload patterns of a specific user.

```bash
# Step 1: Monitor user for extended period
sudo python3 scripts/hpc_monitor.py \
  --user researcher1 \
  --duration 3600 \
  --output user_workload.json

# Step 2: Compare multiple monitoring sessions
python3 examples/multi_job_comparison.py \
  --user researcher1 \
  --output-dir user_analysis
```

### Scenario 3: Real-time Monitoring

**Goal**: Monitor jobs in real-time for immediate insights.

```bash
# Option 1: Command-line real-time monitoring
sudo python3 scripts/hpc_monitor.py \
  --user researcher1 \
  --real-time \
  --duration 1800

# Option 2: Interactive dashboard
sudo python3 examples/realtime_dashboard.py \
  --user researcher1 \
  --update-interval 3
```

### Scenario 4: Batch Job Analysis

**Goal**: Analyze multiple completed jobs.

```bash
# Step 1: Collect data for multiple jobs
for job_id in 12345 12346 12347; do
  sudo python3 scripts/hpc_monitor.py \
    --job-id $job_id \
    --duration 300 \
    --output job_${job_id}.json
done

# Step 2: Compare all jobs
python3 examples/multi_job_comparison.py \
  --files job_*.json \
  --output-dir batch_analysis
```

## Output Formats

### JSON Output (Default)

```json
{
  "monitoring_session": {
    "start_time": "2024-01-15T10:30:00Z",
    "end_time": "2024-01-15T10:35:00Z",
    "duration_seconds": 300
  },
  "jobs": [
    {
      "job_id": "12345",
      "metrics": {
        "cpu_percent": 78.5,
        "io_percent": 15.2
      },
      "classification": {
        "type": "CPU-bound",
        "efficiency_score": 82.3
      }
    }
  ]
}
```

### CSV Output

```bash
# Generate CSV output
sudo python3 scripts/hpc_monitor.py \
  --user username \
  --format csv \
  --output results.csv
```

```csv
job_id,user,job_name,cpu_percent,io_percent,wait_percent,classification,efficiency_score
12345,researcher1,simulation,78.5,15.2,6.3,CPU-bound,82.3
12346,researcher1,analysis,25.4,60.1,14.5,I/O-bound,65.8
```

### YAML Output

```bash
# Generate YAML output
sudo python3 scripts/hpc_monitor.py \
  --user username \
  --format yaml \
  --output results.yaml
```

## Integration with External Systems

### Prometheus Integration

```python
# Enable Prometheus metrics export
# In config/monitor_config.yaml:
external_systems:
  prometheus:
    enabled: true
    port: 8000
    metrics_prefix: "hpc_monitor_"
```

```bash
# Start monitoring with Prometheus export
sudo python3 scripts/hpc_monitor.py \
  --user username \
  --config config/prometheus_config.yaml

# Metrics available at http://localhost:8000/metrics
curl http://localhost:8000/metrics
```

### InfluxDB Integration

```yaml
# In config/monitor_config.yaml:
external_systems:
  influxdb:
    enabled: true
    url: "http://localhost:8086"
    database: "hpc_monitoring"
    username: "monitor_user"
    password: "password"
```

### Email Notifications

```yaml
# In config/monitor_config.yaml:
external_systems:
  email:
    enabled: true
    smtp_server: "smtp.example.com"
    smtp_port: 587
    username: "monitor@example.com"
    password: "password"
    recipients: ["admin@example.com"]
    triggers:
      low_efficiency: 30.0
      high_context_switches: 10000
```

## Performance Tuning

### For High-Activity Systems

```yaml
# Increase buffer sizes and limits
ebpf:
  buffer_size: 512  # KB
  max_events_per_second: 50000

performance:
  update_interval: 5.0
  batch_size: 1000
  limits:
    max_pids: 1000
    max_memory_mb: 1024
```

### For Resource-Constrained Systems

```yaml
# Reduce resource usage
ebpf:
  buffer_size: 64   # KB
  max_events_per_second: 1000

performance:
  update_interval: 10.0
  batch_size: 100
  limits:
    max_pids: 50
    max_memory_mb: 128
```

## Troubleshooting Common Issues

### Issue 1: High CPU Usage

**Symptoms**: Monitor itself uses high CPU

**Solutions**:
```bash
# Reduce monitoring frequency
sudo python3 scripts/hpc_monitor.py \
  --user username \
  --config config/low_impact_config.yaml

# Monitor fewer processes
sudo python3 scripts/hpc_monitor.py \
  --job-id 12345  # Instead of --user
```

### Issue 2: Memory Usage Growth

**Symptoms**: Memory usage increases over time

**Solutions**:
```yaml
# In config file, set limits:
performance:
  limits:
    max_events_in_memory: 10000
    cleanup_interval: 60  # seconds
```

### Issue 3: Missing Events

**Symptoms**: Some syscalls or events not captured

**Solutions**:
```yaml
# Increase buffer size
ebpf:
  buffer_size: 512  # KB
  max_events_per_second: 20000
```

### Issue 4: Slurm Integration Failures

**Symptoms**: Cannot get job information

**Solutions**:
```bash
# Test Slurm commands manually
squeue -u username
sacct -j 12345

# Enable fallback mode
# In config:
slurm:
  fallback_mode: true
```

## Best Practices

### 1. Monitoring Duration

- **Short jobs** (< 5 minutes): Monitor entire duration
- **Medium jobs** (5-60 minutes): Monitor 10-15 minutes
- **Long jobs** (> 1 hour): Monitor 15-30 minutes at different phases

### 2. Resource Management

```bash
# Monitor resource usage of the monitor itself
top -p $(pgrep -f hpc_monitor.py)

# Use nice to reduce priority if needed
sudo nice -n 10 python3 scripts/hpc_monitor.py --user username
```

### 3. Data Management

```bash
# Compress large output files
gzip large_monitoring_output.json

# Archive old monitoring data
mkdir -p archive/$(date +%Y-%m)
mv *.json archive/$(date +%Y-%m)/
```

### 4. Security Considerations

- Always run with minimal required privileges
- Regularly rotate log files
- Secure configuration files with sensitive information
- Monitor the monitor's resource usage

## Advanced Usage

### Custom eBPF Probes

You can extend the monitoring by adding custom eBPF probes:

```python
# In scripts/ebpf_probes.py, add custom probe:
custom_probe = """
int trace_custom_event(struct pt_regs *ctx) {
    // Your custom eBPF code here
    return 0;
}
"""
```

### Custom Classification Rules

```python
# In scripts/data_analyzer.py, modify JobClassifier:
def custom_classify_job(self, metrics):
    # Your custom classification logic
    if metrics['custom_metric'] > threshold:
        return 'Custom-Type'
    return 'Standard-Type'
```

### Integration with Job Schedulers

Beyond Slurm, you can integrate with other schedulers:

```python
# Create custom integration module
class PBSIntegration:
    def get_job_info(self, job_id):
        # PBS-specific implementation
        pass
```

## Getting Help

For additional help:

1. Check the [Installation Guide](INSTALLATION.md) for setup issues
2. Review the [Configuration Guide](CONFIGURATION.md) for advanced settings
3. Look at [example scripts](../examples/) for practical implementations
4. Check [GitHub Issues](https://github.com/yourusername/ebpf-hpc-monitor/issues) for known problems
5. Create a new issue with detailed information about your use case