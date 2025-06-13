#!/usr/bin/env python3
"""
Real-time Monitoring Dashboard

This example demonstrates real-time monitoring with an interactive
terminal-based dashboard using the rich library.

Author: Pau Santana
License: MIT
"""

import sys
import time
import json
import threading
from pathlib import Path
from datetime import datetime, timedelta
from collections import deque, defaultdict
from typing import Dict, List, Any, Optional

# Add the scripts directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent / 'scripts'))

try:
    from rich.console import Console
    from rich.layout import Layout
    from rich.panel import Panel
    from rich.table import Table
    from rich.progress import Progress, SpinnerColumn, TextColumn
    from rich.live import Live
    from rich.text import Text
    from rich.align import Align
    from rich.columns import Columns
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    print("Warning: rich library not available. Install with: pip install rich")

from ebpf_probes import EBPFProbeManager
from slurm_integration import SlurmIntegration
from data_analyzer import JobAnalyzer, JobClassifier

class RealTimeMonitor:
    """
    Real-time monitoring with interactive dashboard
    """
    
    def __init__(self, config=None):
        self.config = config or {}
        self.console = Console() if RICH_AVAILABLE else None
        
        # Initialize components
        self.probe_manager = EBPFProbeManager(self.config.get('ebpf', {}))
        self.slurm = SlurmIntegration(self.config.get('slurm', {}))
        self.analyzer = JobAnalyzer()
        self.classifier = JobClassifier()
        
        # Monitoring state
        self.monitoring = False
        self.monitored_jobs = {}
        self.job_metrics = defaultdict(lambda: deque(maxlen=100))  # Keep last 100 data points
        self.system_metrics = deque(maxlen=50)
        
        # Update intervals
        self.update_interval = 2.0  # seconds
        self.last_update = time.time()
        
        # Threading
        self.monitor_thread = None
        self.stop_event = threading.Event()
    
    def start_monitoring(self, job_ids: Optional[List[str]] = None, user: Optional[str] = None):
        """
        Start real-time monitoring
        
        Args:
            job_ids: Specific job IDs to monitor
            user: Monitor all jobs for a specific user
        """
        
        if not RICH_AVAILABLE:
            print("Rich library not available. Using simple text output.")
            return self._start_simple_monitoring(job_ids, user)
        
        print("Starting real-time monitoring dashboard...")
        
        # Initialize eBPF probes
        if not self.probe_manager.load_probes():
            print("Failed to load eBPF probes")
            return False
        
        # Determine jobs to monitor
        if job_ids:
            for job_id in job_ids:
                job_info = self.slurm.get_job_info(job_id)
                if job_info:
                    self.monitored_jobs[job_id] = job_info[0]
        elif user:
            jobs = self.slurm.get_user_jobs(user)
            for job in jobs:
                if job.get('state') == 'RUNNING':
                    self.monitored_jobs[job['job_id']] = job
        else:
            # Monitor all running jobs
            jobs = self.slurm.get_running_jobs()
            for job in jobs[:10]:  # Limit to 10 jobs for performance
                self.monitored_jobs[job['job_id']] = job
        
        if not self.monitored_jobs:
            print("No jobs found to monitor")
            return False
        
        print(f"Monitoring {len(self.monitored_jobs)} jobs")
        
        # Start monitoring thread
        self.monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitoring_loop)
        self.monitor_thread.start()
        
        # Start dashboard
        try:
            self._run_dashboard()
        except KeyboardInterrupt:
            pass
        finally:
            self.stop_monitoring()
        
        return True
    
    def stop_monitoring(self):
        """
        Stop monitoring
        """
        
        self.monitoring = False
        self.stop_event.set()
        
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=5)
        
        self.probe_manager.cleanup()
        print("\nMonitoring stopped")
    
    def _monitoring_loop(self):
        """
        Main monitoring loop running in background thread
        """
        
        while self.monitoring and not self.stop_event.is_set():
            try:
                # Collect metrics for each monitored job
                for job_id, job_info in self.monitored_jobs.items():
                    pids = self.slurm.get_job_pids(job_id)
                    if pids:
                        # Add PIDs to monitoring
                        for pid in pids:
                            self.probe_manager.add_pid(pid)
                        
                        # Collect current metrics
                        events = self.probe_manager.poll_events(timeout=100)
                        metrics = self.analyzer.aggregate_metrics(events, pids)
                        
                        # Store metrics with timestamp
                        timestamp = datetime.now()
                        self.job_metrics[job_id].append({
                            'timestamp': timestamp,
                            'metrics': metrics,
                            'pids': pids
                        })
                
                # Collect system-wide metrics
                system_events = self.probe_manager.poll_events(timeout=100)
                system_metrics = self.analyzer.aggregate_metrics(system_events)
                self.system_metrics.append({
                    'timestamp': datetime.now(),
                    'metrics': system_metrics
                })
                
                time.sleep(self.update_interval)
                
            except Exception as e:
                if self.monitoring:
                    print(f"Error in monitoring loop: {e}")
                time.sleep(1)
    
    def _run_dashboard(self):
        """
        Run the interactive dashboard
        """
        
        layout = Layout()
        
        # Create layout structure
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="main"),
            Layout(name="footer", size=3)
        )
        
        layout["main"].split_row(
            Layout(name="jobs", ratio=2),
            Layout(name="details", ratio=1)
        )
        
        layout["jobs"].split_column(
            Layout(name="job_list"),
            Layout(name="system_stats", size=8)
        )
        
        with Live(layout, refresh_per_second=2, screen=True) as live:
            while self.monitoring:
                try:
                    # Update header
                    layout["header"].update(
                        Panel(
                            Align.center(
                                Text(f"eBPF HPC Monitor - Real-time Dashboard\n"
                                    f"Monitoring {len(self.monitored_jobs)} jobs | "
                                    f"Updated: {datetime.now().strftime('%H:%M:%S')}",
                                    style="bold blue")
                            ),
                            style="blue"
                        )
                    )
                    
                    # Update job list
                    layout["job_list"].update(self._create_job_table())
                    
                    # Update system stats
                    layout["system_stats"].update(self._create_system_panel())
                    
                    # Update details (show details for first job)
                    if self.monitored_jobs:
                        first_job_id = list(self.monitored_jobs.keys())[0]
                        layout["details"].update(self._create_job_details(first_job_id))
                    
                    # Update footer
                    layout["footer"].update(
                        Panel(
                            Align.center(
                                Text("Press Ctrl+C to stop monitoring", style="dim")
                            ),
                            style="dim"
                        )
                    )
                    
                    time.sleep(0.5)
                    
                except Exception as e:
                    self.console.print(f"Dashboard error: {e}", style="red")
                    time.sleep(1)
    
    def _create_job_table(self) -> Panel:
        """
        Create a table showing all monitored jobs
        """
        
        table = Table(title="Monitored Jobs", show_header=True, header_style="bold magenta")
        table.add_column("Job ID", style="cyan", width=10)
        table.add_column("User", style="green", width=12)
        table.add_column("Name", style="yellow", width=15)
        table.add_column("CPU %", justify="right", width=8)
        table.add_column("I/O %", justify="right", width=8)
        table.add_column("Classification", width=12)
        table.add_column("Efficiency", justify="right", width=10)
        table.add_column("PIDs", justify="right", width=6)
        
        for job_id, job_info in self.monitored_jobs.items():
            # Get latest metrics
            if job_id in self.job_metrics and self.job_metrics[job_id]:
                latest = self.job_metrics[job_id][-1]
                metrics = latest['metrics']
                pids = latest['pids']
                
                cpu_percent = metrics.get('cpu_percent', 0)
                io_percent = metrics.get('io_percent', 0)
                
                # Classify job
                classification = self.classifier.classify_job(metrics)
                efficiency = self.classifier.get_efficiency_score(metrics)
                
                # Color coding for efficiency
                if efficiency >= 70:
                    eff_style = "green"
                elif efficiency >= 40:
                    eff_style = "yellow"
                else:
                    eff_style = "red"
                
                table.add_row(
                    job_id,
                    job_info.get('user', 'unknown'),
                    job_info.get('name', 'unknown')[:15],
                    f"{cpu_percent:.1f}",
                    f"{io_percent:.1f}",
                    classification,
                    f"[{eff_style}]{efficiency:.1f}[/{eff_style}]",
                    str(len(pids))
                )
            else:
                table.add_row(
                    job_id,
                    job_info.get('user', 'unknown'),
                    job_info.get('name', 'unknown')[:15],
                    "--", "--", "--", "--", "--"
                )
        
        return Panel(table, title="Job Overview", border_style="blue")
    
    def _create_system_panel(self) -> Panel:
        """
        Create system-wide statistics panel
        """
        
        if not self.system_metrics:
            return Panel("No system data available", title="System Statistics")
        
        latest = self.system_metrics[-1]
        metrics = latest['metrics']
        
        # Create mini charts using text
        cpu_history = [m['metrics'].get('cpu_percent', 0) for m in list(self.system_metrics)[-20:]]
        io_history = [m['metrics'].get('io_percent', 0) for m in list(self.system_metrics)[-20:]]
        
        cpu_chart = self._create_mini_chart(cpu_history, "CPU")
        io_chart = self._create_mini_chart(io_history, "I/O")
        
        content = f"""
[bold]Current System Metrics:[/bold]

Total Syscalls: {metrics.get('total_syscalls', 0):,}
Context Switches: {metrics.get('context_switches', 0):,}
I/O Operations: {metrics.get('io_operations', 0):,}
Network Operations: {metrics.get('net_operations', 0):,}

{cpu_chart}
{io_chart}
"""
        
        return Panel(content, title="System Statistics", border_style="green")
    
    def _create_job_details(self, job_id: str) -> Panel:
        """
        Create detailed view for a specific job
        """
        
        if job_id not in self.job_metrics or not self.job_metrics[job_id]:
            return Panel("No data available", title=f"Job {job_id} Details")
        
        latest = self.job_metrics[job_id][-1]
        metrics = latest['metrics']
        job_info = self.monitored_jobs[job_id]
        
        # Calculate trends
        if len(self.job_metrics[job_id]) > 1:
            prev_metrics = self.job_metrics[job_id][-2]['metrics']
            cpu_trend = metrics.get('cpu_percent', 0) - prev_metrics.get('cpu_percent', 0)
            io_trend = metrics.get('io_percent', 0) - prev_metrics.get('io_percent', 0)
        else:
            cpu_trend = 0
            io_trend = 0
        
        # Format trends
        cpu_trend_str = f"({cpu_trend:+.1f})" if cpu_trend != 0 else ""
        io_trend_str = f"({io_trend:+.1f})" if io_trend != 0 else ""
        
        classification = self.classifier.classify_job(metrics)
        efficiency = self.classifier.get_efficiency_score(metrics)
        
        content = f"""
[bold]Job Information:[/bold]
User: {job_info.get('user', 'unknown')}
Name: {job_info.get('name', 'unknown')}
Partition: {job_info.get('partition', 'unknown')}
Nodes: {', '.join(job_info.get('nodes', []))}

[bold]Current Metrics:[/bold]
CPU Usage: {metrics.get('cpu_percent', 0):.1f}% {cpu_trend_str}
I/O Usage: {metrics.get('io_percent', 0):.1f}% {io_trend_str}
Wait Time: {metrics.get('wait_percent', 0):.1f}%

[bold]Classification:[/bold]
Type: {classification}
Efficiency: {efficiency:.1f}%

[bold]Activity:[/bold]
Syscalls: {metrics.get('total_syscalls', 0):,}
Context Switches: {metrics.get('context_switches', 0):,}
I/O Bytes: {self._format_bytes(metrics.get('total_io_bytes', 0))}
Net Bytes: {self._format_bytes(metrics.get('total_net_bytes', 0))}

[bold]PIDs:[/bold] {len(latest['pids'])}
"""
        
        return Panel(content, title=f"Job {job_id} Details", border_style="yellow")
    
    def _create_mini_chart(self, values: List[float], label: str) -> str:
        """
        Create a simple text-based mini chart
        """
        
        if not values:
            return f"{label}: No data"
        
        # Normalize values to 0-8 range for display
        max_val = max(values) if max(values) > 0 else 1
        normalized = [int(v / max_val * 8) for v in values]
        
        # Create bar chart using Unicode blocks
        bars = ["▁▂▃▄▅▆▇█"[min(n, 7)] for n in normalized]
        chart = "".join(bars)
        
        current = values[-1] if values else 0
        return f"{label}: {current:5.1f}% {''.join(bars[-15:])}"
    
    def _format_bytes(self, bytes_val: int) -> str:
        """
        Format bytes in human readable format
        """
        
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_val < 1024.0:
                return f"{bytes_val:.1f} {unit}"
            bytes_val /= 1024.0
        return f"{bytes_val:.1f} PB"
    
    def _start_simple_monitoring(self, job_ids: Optional[List[str]] = None, user: Optional[str] = None):
        """
        Simple text-based monitoring when rich is not available
        """
        
        print("Starting simple monitoring (install 'rich' for better interface)...")
        
        # Initialize eBPF probes
        if not self.probe_manager.load_probes():
            print("Failed to load eBPF probes")
            return False
        
        # Determine jobs to monitor
        if job_ids:
            for job_id in job_ids:
                job_info = self.slurm.get_job_info(job_id)
                if job_info:
                    self.monitored_jobs[job_id] = job_info[0]
        elif user:
            jobs = self.slurm.get_user_jobs(user)
            for job in jobs:
                if job.get('state') == 'RUNNING':
                    self.monitored_jobs[job['job_id']] = job
        
        if not self.monitored_jobs:
            print("No jobs found to monitor")
            return False
        
        print(f"Monitoring {len(self.monitored_jobs)} jobs")
        print("Press Ctrl+C to stop...\n")
        
        try:
            while True:
                print(f"\n{'='*80}")
                print(f"Update: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"{'='*80}")
                
                for job_id, job_info in self.monitored_jobs.items():
                    pids = self.slurm.get_job_pids(job_id)
                    if pids:
                        # Add PIDs to monitoring
                        for pid in pids:
                            self.probe_manager.add_pid(pid)
                        
                        # Collect metrics
                        events = self.probe_manager.poll_events(timeout=1000)
                        metrics = self.analyzer.aggregate_metrics(events, pids)
                        
                        # Classify job
                        classification = self.classifier.classify_job(metrics)
                        efficiency = self.classifier.get_efficiency_score(metrics)
                        
                        print(f"Job {job_id} ({job_info.get('user', 'unknown')})")
                        print(f"  Name: {job_info.get('name', 'unknown')}")
                        print(f"  CPU: {metrics.get('cpu_percent', 0):.1f}% | "
                              f"I/O: {metrics.get('io_percent', 0):.1f}% | "
                              f"Wait: {metrics.get('wait_percent', 0):.1f}%")
                        print(f"  Classification: {classification} | Efficiency: {efficiency:.1f}%")
                        print(f"  Syscalls: {metrics.get('total_syscalls', 0):,} | "
                              f"Context Switches: {metrics.get('context_switches', 0):,}")
                        print(f"  PIDs: {len(pids)}")
                        print()
                
                time.sleep(self.update_interval)
                
        except KeyboardInterrupt:
            pass
        
        return True

def main():
    """
    Main function for real-time monitoring
    """
    
    import argparse
    
    parser = argparse.ArgumentParser(description='Real-time HPC Job Monitoring Dashboard')
    parser.add_argument('--job-ids', '-j', nargs='+', help='Specific job IDs to monitor')
    parser.add_argument('--user', '-u', help='Monitor all jobs for a specific user')
    parser.add_argument('--config', '-c', help='Configuration file')
    parser.add_argument('--update-interval', '-i', type=float, default=2.0, 
                       help='Update interval in seconds')
    
    args = parser.parse_args()
    
    # Check for root privileges
    import os
    if os.geteuid() != 0:
        print("Error: This tool requires root privileges to use eBPF")
        sys.exit(1)
    
    # Load configuration
    config = {}
    if args.config:
        import yaml
        with open(args.config, 'r') as f:
            config = yaml.safe_load(f)
    
    # Create monitor
    monitor = RealTimeMonitor(config)
    monitor.update_interval = args.update_interval
    
    try:
        success = monitor.start_monitoring(
            job_ids=args.job_ids,
            user=args.user
        )
        
        if not success:
            print("Failed to start monitoring")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\nMonitoring interrupted by user")
    except Exception as e:
        print(f"\nError during monitoring: {e}")
        sys.exit(1)
    finally:
        monitor.stop_monitoring()

if __name__ == '__main__':
    main()