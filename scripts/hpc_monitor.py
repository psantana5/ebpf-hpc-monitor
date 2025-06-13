#!/usr/bin/env python3
"""
eBPF HPC Monitor - Main monitoring script

This script provides comprehensive monitoring of HPC processes using eBPF,
with special integration for Slurm job management.

Author: Pau Santana
License: MIT
"""

import argparse
import json
import logging
import signal
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import click
import coloredlogs
from rich.console import Console
from rich.live import Live
from rich.table import Table
from rich.panel import Panel

# Local imports
from ebpf_probes import EBPFProbeManager
from slurm_integration import SlurmIntegration
from data_analyzer import JobAnalyzer, JobClassifier

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
coloredlogs.install(level='INFO', logger=logger)

console = Console()

class HPCMonitor:
    """
    Main HPC monitoring class that orchestrates eBPF probes,
    Slurm integration, and data analysis.
    """
    
    def __init__(self, config: Dict):
        self.config = config
        self.probe_manager = EBPFProbeManager(config.get('ebpf', {}))
        self.slurm = SlurmIntegration(config.get('slurm', {}))
        self.analyzer = JobAnalyzer()
        self.classifier = JobClassifier()
        self.running = False
        self.start_time = None
        self.monitored_jobs = {}
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully"""
        logger.info(f"Received signal {signum}, shutting down...")
        self.stop()
    
    def start_monitoring(self, 
                        job_id: Optional[str] = None,
                        user: Optional[str] = None,
                        duration: Optional[int] = None,
                        output_file: Optional[str] = None,
                        real_time: bool = False):
        """
        Start the monitoring process
        
        Args:
            job_id: Specific Slurm job ID to monitor
            user: Monitor jobs for specific user
            duration: Monitoring duration in seconds
            output_file: File to save results
            real_time: Show real-time dashboard
        """
        
        logger.info("Starting eBPF HPC Monitor...")
        self.start_time = datetime.now()
        self.running = True
        
        # Initialize eBPF probes
        try:
            self.probe_manager.load_probes()
            logger.info("eBPF probes loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load eBPF probes: {e}")
            return False
        
        # Get initial job list
        if job_id:
            jobs = self.slurm.get_job_info(job_id)
        elif user:
            jobs = self.slurm.get_user_jobs(user)
        else:
            jobs = self.slurm.get_running_jobs()
        
        logger.info(f"Monitoring {len(jobs)} jobs")
        
        # Start monitoring loop
        if real_time:
            self._real_time_monitoring(jobs, duration)
        else:
            self._batch_monitoring(jobs, duration)
        
        # Generate final report
        results = self._generate_report()
        
        if output_file:
            self._save_results(results, output_file)
        else:
            self._display_results(results)
        
        return True
    
    def _real_time_monitoring(self, jobs: List[Dict], duration: Optional[int]):
        """Real-time monitoring with live dashboard"""
        
        def generate_table():
            table = Table(title="eBPF HPC Monitor - Live Dashboard")
            table.add_column("Job ID", style="cyan")
            table.add_column("User", style="green")
            table.add_column("CPU %", style="yellow")
            table.add_column("I/O %", style="blue")
            table.add_column("Ctx Switches", style="magenta")
            table.add_column("Classification", style="red")
            
            for job_id, data in self.monitored_jobs.items():
                metrics = data.get('metrics', {})
                classification = self.classifier.classify_job(metrics)
                
                table.add_row(
                    str(job_id),
                    data.get('user', 'unknown'),
                    f"{metrics.get('cpu_percent', 0):.1f}",
                    f"{metrics.get('io_percent', 0):.1f}",
                    str(metrics.get('context_switches', 0)),
                    classification
                )
            
            return Panel(table, title="HPC Job Monitoring", border_style="blue")
        
        with Live(generate_table(), refresh_per_second=2) as live:
            start_time = time.time()
            
            while self.running:
                # Update monitoring data
                self._update_job_metrics(jobs)
                
                # Update display
                live.update(generate_table())
                
                # Check duration
                if duration and (time.time() - start_time) >= duration:
                    break
                
                time.sleep(1)
    
    def _batch_monitoring(self, jobs: List[Dict], duration: Optional[int]):
        """Batch monitoring without real-time display"""
        
        start_time = time.time()
        update_interval = 5  # Update every 5 seconds
        last_update = 0
        
        while self.running:
            current_time = time.time()
            
            # Update metrics periodically
            if current_time - last_update >= update_interval:
                self._update_job_metrics(jobs)
                last_update = current_time
                
                # Log progress
                elapsed = current_time - start_time
                logger.info(f"Monitoring... Elapsed: {elapsed:.1f}s, Jobs: {len(self.monitored_jobs)}")
            
            # Check duration
            if duration and (current_time - start_time) >= duration:
                break
            
            time.sleep(0.5)
    
    def _update_job_metrics(self, jobs: List[Dict]):
        """Update metrics for all monitored jobs"""
        
        # Get current probe data
        probe_data = self.probe_manager.get_current_data()
        
        for job in jobs:
            job_id = job['job_id']
            pids = self.slurm.get_job_pids(job_id)
            
            if not pids:
                continue
            
            # Aggregate metrics for all PIDs in the job
            job_metrics = self.analyzer.aggregate_pid_metrics(pids, probe_data)
            
            # Update job data
            if job_id not in self.monitored_jobs:
                self.monitored_jobs[job_id] = {
                    'job_info': job,
                    'start_time': datetime.now(),
                    'metrics': job_metrics
                }
            else:
                # Update existing metrics
                self.monitored_jobs[job_id]['metrics'] = self.analyzer.update_metrics(
                    self.monitored_jobs[job_id]['metrics'], 
                    job_metrics
                )
    
    def _generate_report(self) -> Dict:
        """Generate final monitoring report"""
        
        end_time = datetime.now()
        total_duration = (end_time - self.start_time).total_seconds()
        
        report = {
            'monitoring_session': {
                'start_time': self.start_time.isoformat(),
                'end_time': end_time.isoformat(),
                'duration_seconds': total_duration
            },
            'jobs': []
        }
        
        for job_id, data in self.monitored_jobs.items():
            job_info = data['job_info']
            metrics = data['metrics']
            
            # Classify the job
            classification = self.classifier.classify_job(metrics)
            recommendations = self.classifier.get_recommendations(metrics, classification)
            
            job_report = {
                'job_id': job_id,
                'user': job_info.get('user', 'unknown'),
                'job_name': job_info.get('name', 'unknown'),
                'partition': job_info.get('partition', 'unknown'),
                'nodes': job_info.get('nodes', []),
                'duration_seconds': (end_time - data['start_time']).total_seconds(),
                'metrics': metrics,
                'classification': classification,
                'recommendations': recommendations
            }
            
            report['jobs'].append(job_report)
        
        return report
    
    def _save_results(self, results: Dict, output_file: str):
        """Save results to file"""
        
        output_path = Path(output_file)
        
        if output_path.suffix.lower() == '.json':
            with open(output_path, 'w') as f:
                json.dump(results, f, indent=2, default=str)
        elif output_path.suffix.lower() == '.csv':
            # Convert to CSV format
            import pandas as pd
            
            # Flatten job data for CSV
            csv_data = []
            for job in results['jobs']:
                row = {
                    'job_id': job['job_id'],
                    'user': job['user'],
                    'duration': job['duration_seconds'],
                    'classification': job['classification'],
                    **job['metrics']
                }
                csv_data.append(row)
            
            df = pd.DataFrame(csv_data)
            df.to_csv(output_path, index=False)
        
        logger.info(f"Results saved to {output_path}")
    
    def _display_results(self, results: Dict):
        """Display results in terminal"""
        
        console.print("\n[bold blue]eBPF HPC Monitor - Final Report[/bold blue]")
        console.print(f"Session Duration: {results['monitoring_session']['duration_seconds']:.1f} seconds")
        console.print(f"Jobs Monitored: {len(results['jobs'])}\n")
        
        # Create summary table
        table = Table(title="Job Summary")
        table.add_column("Job ID", style="cyan")
        table.add_column("User", style="green")
        table.add_column("Duration (s)", style="yellow")
        table.add_column("CPU %", style="blue")
        table.add_column("I/O %", style="magenta")
        table.add_column("Classification", style="red")
        
        for job in results['jobs']:
            metrics = job['metrics']
            table.add_row(
                str(job['job_id']),
                job['user'],
                f"{job['duration_seconds']:.1f}",
                f"{metrics.get('cpu_percent', 0):.1f}",
                f"{metrics.get('io_percent', 0):.1f}",
                job['classification']
            )
        
        console.print(table)
        
        # Show detailed recommendations
        for job in results['jobs']:
            if job['recommendations']:
                console.print(f"\n[bold]Recommendations for Job {job['job_id']}:[/bold]")
                for rec in job['recommendations']:
                    console.print(f"  • {rec}")
    
    def stop(self):
        """Stop monitoring"""
        self.running = False
        if hasattr(self, 'probe_manager'):
            self.probe_manager.cleanup()
        logger.info("Monitoring stopped")


@click.command()
@click.option('--job-id', '-j', help='Specific Slurm job ID to monitor')
@click.option('--user', '-u', help='Monitor jobs for specific user')
@click.option('--duration', '-d', type=int, help='Monitoring duration in seconds')
@click.option('--output', '-o', help='Output file (JSON or CSV)')
@click.option('--config', '-c', default='config/monitor_config.yaml', help='Configuration file')
@click.option('--real-time', '-r', is_flag=True, help='Show real-time dashboard')
@click.option('--filter', '-f', help='Filter events (io, sched, net, all)')
@click.option('--verbose', '-v', is_flag=True, help='Verbose logging')
def main(job_id, user, duration, output, config, real_time, filter, verbose):
    """
    eBPF HPC Monitor - Monitor HPC jobs using eBPF
    
    This tool uses eBPF to monitor system calls, scheduling events,
    and other kernel events to analyze HPC job performance.
    """
    
    if verbose:
        coloredlogs.install(level='DEBUG', logger=logger)
    
    # Load configuration
    import yaml
    
    try:
        with open(config, 'r') as f:
            config_data = yaml.safe_load(f)
    except FileNotFoundError:
        logger.warning(f"Config file {config} not found, using defaults")
        config_data = {}
    
    # Apply filter if specified
    if filter:
        config_data.setdefault('ebpf', {})['filter'] = filter
    
    # Check for root privileges
    if os.geteuid() != 0:
        console.print("[red]Error: This tool requires root privileges to use eBPF[/red]")
        sys.exit(1)
    
    # Create and start monitor
    monitor = HPCMonitor(config_data)
    
    try:
        success = monitor.start_monitoring(
            job_id=job_id,
            user=user,
            duration=duration,
            output_file=output,
            real_time=real_time
        )
        
        if not success:
            sys.exit(1)
            
    except KeyboardInterrupt:
        logger.info("Monitoring interrupted by user")
    except Exception as e:
        logger.error(f"Monitoring failed: {e}")
        sys.exit(1)
    finally:
        monitor.stop()


if __name__ == '__main__':
    import os
    main()