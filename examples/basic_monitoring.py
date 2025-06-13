#!/usr/bin/env python3
"""
Basic Monitoring Example

This example demonstrates basic usage of the eBPF HPC Monitor
for monitoring system processes and Slurm jobs.

Author: Your Name
License: MIT
"""

import sys
import time
import json
from pathlib import Path

# Add the scripts directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent / 'scripts'))

from hpc_monitor import HPCMonitor
from ebpf_probes import EBPFProbeManager
from slurm_integration import SlurmIntegration
from data_analyzer import JobAnalyzer, JobClassifier

def basic_monitoring_example():
    """
    Basic monitoring example - monitor all running processes for 30 seconds
    """
    
    print("=== Basic Monitoring Example ===")
    print("This example will monitor all processes for 30 seconds")
    print("Note: Requires root privileges to run eBPF probes\n")
    
    # Basic configuration
    config = {
        'ebpf': {
            'filter': 'all',
            'poll_interval_ms': 100
        },
        'slurm': {
            'cache_timeout': 30,
            'enable_fallback': True
        }
    }
    
    try:
        # Create monitor instance
        monitor = HPCMonitor(config)
        
        print("Starting monitoring...")
        
        # Start monitoring for 30 seconds
        success = monitor.start_monitoring(
            duration=30,
            real_time=False
        )
        
        if success:
            print("\nMonitoring completed successfully!")
        else:
            print("\nMonitoring failed!")
            
    except KeyboardInterrupt:
        print("\nMonitoring interrupted by user")
    except Exception as e:
        print(f"\nError during monitoring: {e}")
        print("Make sure you're running as root and BCC is installed")

def monitor_specific_user_example():
    """
    Example: Monitor jobs for a specific user
    """
    
    print("\n=== User-Specific Monitoring Example ===")
    
    # Get current user
    import os
    username = os.getenv('USER', 'unknown')
    
    print(f"Monitoring jobs for user: {username}")
    
    config = {
        'ebpf': {'filter': 'all'},
        'slurm': {'enable_fallback': True}
    }
    
    try:
        monitor = HPCMonitor(config)
        
        # Monitor user's jobs for 20 seconds
        success = monitor.start_monitoring(
            user=username,
            duration=20,
            real_time=True  # Show real-time dashboard
        )
        
        if success:
            print(f"\nCompleted monitoring for user {username}")
            
    except Exception as e:
        print(f"Error: {e}")

def analyze_probe_data_example():
    """
    Example: Direct usage of eBPF probes and data analysis
    """
    
    print("\n=== Direct Probe Analysis Example ===")
    print("This example shows direct usage of eBPF probes")
    
    try:
        # Initialize components
        probe_manager = EBPFProbeManager({'filter': 'syscall'})
        analyzer = JobAnalyzer()
        classifier = JobClassifier()
        
        print("Loading eBPF probes...")
        probe_manager.load_probes()
        
        print("Collecting data for 10 seconds...")
        
        # Collect data for 10 seconds
        start_time = time.time()
        while time.time() - start_time < 10:
            probe_manager.poll_events(timeout_ms=100)
            time.sleep(0.1)
        
        # Get collected data
        probe_data = probe_manager.get_current_data()
        
        print("\nAnalyzing collected data...")
        
        # Get all monitored PIDs
        import psutil
        all_pids = {proc.pid for proc in psutil.process_iter()}
        
        # Analyze the data
        metrics = analyzer.aggregate_pid_metrics(all_pids, probe_data)
        
        # Classify the overall system behavior
        classification = classifier.classify_job(metrics)
        efficiency = classifier.get_efficiency_score(metrics)
        recommendations = classifier.get_recommendations(metrics, classification)
        
        # Display results
        print(f"\nSystem Classification: {classification}")
        print(f"Efficiency Score: {efficiency:.1f}/100")
        print(f"Total Syscalls: {metrics['total_syscalls']}")
        print(f"CPU Percentage: {metrics['cpu_percent']:.1f}%")
        print(f"I/O Percentage: {metrics['io_percent']:.1f}%")
        print(f"Context Switches: {metrics['context_switches']}")
        
        if recommendations:
            print("\nRecommendations:")
            for rec in recommendations:
                print(f"  • {rec}")
        
        # Get syscall breakdown
        syscall_breakdown = analyzer.get_syscall_breakdown(probe_data, all_pids)
        
        if syscall_breakdown:
            print("\nTop Syscalls:")
            sorted_syscalls = sorted(syscall_breakdown.items(), 
                                   key=lambda x: x[1], reverse=True)[:10]
            for syscall, count in sorted_syscalls:
                print(f"  {syscall}: {count}")
        
        # Cleanup
        probe_manager.cleanup()
        
    except Exception as e:
        print(f"Error in probe analysis: {e}")
        print("Make sure you're running as root")

def save_monitoring_data_example():
    """
    Example: Save monitoring data to files
    """
    
    print("\n=== Save Data Example ===")
    print("This example saves monitoring data to JSON and CSV files")
    
    config = {
        'ebpf': {'filter': 'all'},
        'slurm': {'enable_fallback': True}
    }
    
    try:
        monitor = HPCMonitor(config)
        
        # Create output directory
        output_dir = Path('monitoring_output')
        output_dir.mkdir(exist_ok=True)
        
        # Monitor and save to JSON
        json_file = output_dir / f'monitoring_data_{int(time.time())}.json'
        
        print(f"Monitoring for 15 seconds, saving to {json_file}")
        
        success = monitor.start_monitoring(
            duration=15,
            output_file=str(json_file)
        )
        
        if success and json_file.exists():
            print(f"\nData saved to {json_file}")
            
            # Load and display summary
            with open(json_file, 'r') as f:
                data = json.load(f)
            
            print(f"\nSummary:")
            print(f"  Jobs monitored: {len(data.get('jobs', []))}")
            print(f"  Session duration: {data['monitoring_session']['duration_seconds']:.1f}s")
            
            # Show job classifications
            for job in data.get('jobs', []):
                classifier = JobClassifier()
                classification = classifier.classify_job(job['metrics'])
                print(f"  Job {job['job_id']}: {classification}")
        
    except Exception as e:
        print(f"Error: {e}")

def compare_jobs_example():
    """
    Example: Compare multiple jobs
    """
    
    print("\n=== Job Comparison Example ===")
    
    # Simulate some job metrics for comparison
    job_metrics = [
        {
            'cpu_percent': 85.0,
            'io_percent': 5.0,
            'wait_percent': 10.0,
            'context_switches': 500,
            'total_syscalls': 10000
        },
        {
            'cpu_percent': 20.0,
            'io_percent': 60.0,
            'wait_percent': 20.0,
            'context_switches': 2000,
            'total_syscalls': 15000
        },
        {
            'cpu_percent': 10.0,
            'io_percent': 5.0,
            'wait_percent': 85.0,
            'context_switches': 100,
            'total_syscalls': 1000
        }
    ]
    
    classifier = JobClassifier()
    
    print("Analyzing simulated job data...")
    
    # Classify each job
    for i, metrics in enumerate(job_metrics):
        classification = classifier.classify_job(metrics)
        efficiency = classifier.get_efficiency_score(metrics)
        
        print(f"\nJob {i+1}:")
        print(f"  Classification: {classification}")
        print(f"  Efficiency: {efficiency:.1f}/100")
        print(f"  CPU: {metrics['cpu_percent']:.1f}%")
        print(f"  I/O: {metrics['io_percent']:.1f}%")
        print(f"  Wait: {metrics['wait_percent']:.1f}%")
    
    # Compare all jobs
    comparison = classifier.compare_jobs(job_metrics)
    
    print(f"\nComparison Summary:")
    print(f"  Average efficiency: {comparison['average_efficiency']:.1f}")
    print(f"  Best job: Job {comparison['best_job_index'] + 1} ({comparison['best_efficiency']:.1f})")
    print(f"  Worst job: Job {comparison['worst_job_index'] + 1} ({comparison['worst_efficiency']:.1f})")
    print(f"  Classification distribution: {comparison['classification_distribution']}")

def main():
    """
    Main function to run all examples
    """
    
    print("eBPF HPC Monitor - Basic Examples")
    print("=" * 50)
    
    # Check if running as root
    import os
    if os.geteuid() != 0:
        print("WARNING: Most examples require root privileges to use eBPF")
        print("Some examples may fail or show limited data\n")
    
    try:
        # Run examples that don't require eBPF first
        compare_jobs_example()
        
        # Ask user which examples to run
        print("\n" + "="*50)
        print("Available examples (require root for eBPF):")
        print("1. Basic monitoring (30s)")
        print("2. User-specific monitoring (20s)")
        print("3. Direct probe analysis (10s)")
        print("4. Save monitoring data (15s)")
        print("5. Run all eBPF examples")
        print("0. Exit")
        
        choice = input("\nSelect example to run (0-5): ").strip()
        
        if choice == '1':
            basic_monitoring_example()
        elif choice == '2':
            monitor_specific_user_example()
        elif choice == '3':
            analyze_probe_data_example()
        elif choice == '4':
            save_monitoring_data_example()
        elif choice == '5':
            basic_monitoring_example()
            monitor_specific_user_example()
            analyze_probe_data_example()
            save_monitoring_data_example()
        elif choice == '0':
            print("Exiting...")
        else:
            print("Invalid choice")
    
    except KeyboardInterrupt:
        print("\nExamples interrupted by user")
    except Exception as e:
        print(f"\nError running examples: {e}")
    
    print("\nExamples completed!")

if __name__ == '__main__':
    main()