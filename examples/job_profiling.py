#!/usr/bin/env python3
"""
Job Profiling Example

This example demonstrates advanced job profiling capabilities,
including detailed analysis and performance optimization suggestions.

Author: Your Name
License: MIT
"""

import sys
import time
import json
import argparse
from pathlib import Path
from datetime import datetime, timedelta

# Add the scripts directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent / 'scripts'))

from hpc_monitor import HPCMonitor
from data_analyzer import JobAnalyzer, JobClassifier
from slurm_integration import SlurmIntegration

class JobProfiler:
    """
    Advanced job profiling with detailed analysis
    """
    
    def __init__(self, config=None):
        self.config = config or {}
        self.monitor = HPCMonitor(self.config)
        self.analyzer = JobAnalyzer()
        self.classifier = JobClassifier()
        self.slurm = SlurmIntegration(self.config.get('slurm', {}))
    
    def profile_job(self, job_id, duration=300, detailed=True):
        """
        Profile a specific Slurm job with detailed analysis
        
        Args:
            job_id: Slurm job ID to profile
            duration: Profiling duration in seconds
            detailed: Include detailed syscall and I/O analysis
        """
        
        print(f"Starting detailed profiling for job {job_id}")
        print(f"Duration: {duration} seconds")
        print(f"Detailed analysis: {detailed}")
        print("-" * 50)
        
        # Check if job exists and is running
        job_info = self.slurm.get_job_info(job_id)
        if not job_info:
            print(f"Job {job_id} not found or not running")
            return None
        
        job = job_info[0]
        print(f"Job Name: {job['name']}")
        print(f"User: {job['user']}")
        print(f"Partition: {job['partition']}")
        print(f"Nodes: {', '.join(job['nodes'])}")
        print(f"CPUs: {job['cpus']}")
        print()
        
        # Start profiling
        start_time = datetime.now()
        
        try:
            # Create output file
            output_file = f"job_{job_id}_profile_{int(time.time())}.json"
            
            success = self.monitor.start_monitoring(
                job_id=job_id,
                duration=duration,
                output_file=output_file,
                real_time=True
            )
            
            if not success:
                print("Profiling failed")
                return None
            
            # Load and analyze results
            with open(output_file, 'r') as f:
                results = json.load(f)
            
            # Perform detailed analysis
            analysis = self._analyze_job_profile(results, job_id, detailed)
            
            # Save detailed analysis
            analysis_file = f"job_{job_id}_analysis_{int(time.time())}.json"
            with open(analysis_file, 'w') as f:
                json.dump(analysis, f, indent=2, default=str)
            
            print(f"\nProfiling completed!")
            print(f"Raw data: {output_file}")
            print(f"Analysis: {analysis_file}")
            
            # Display summary
            self._display_profile_summary(analysis)
            
            return analysis
            
        except Exception as e:
            print(f"Error during profiling: {e}")
            return None
    
    def _analyze_job_profile(self, results, job_id, detailed=True):
        """
        Perform detailed analysis of job profiling results
        """
        
        job_data = None
        for job in results.get('jobs', []):
            if job['job_id'] == job_id:
                job_data = job
                break
        
        if not job_data:
            return {'error': 'Job data not found in results'}
        
        metrics = job_data['metrics']
        
        # Basic classification
        classification = self.classifier.classify_job(metrics)
        efficiency = self.classifier.get_efficiency_score(metrics)
        recommendations = self.classifier.get_recommendations(metrics, classification)
        
        analysis = {
            'job_info': {
                'job_id': job_id,
                'user': job_data['user'],
                'duration': job_data['duration_seconds'],
                'classification': classification,
                'efficiency_score': efficiency
            },
            'performance_metrics': self._calculate_performance_metrics(metrics),
            'resource_utilization': self._analyze_resource_utilization(metrics),
            'bottleneck_analysis': self._identify_bottlenecks(metrics),
            'optimization_suggestions': self._generate_optimization_suggestions(metrics, classification),
            'recommendations': recommendations,
            'raw_metrics': metrics
        }
        
        if detailed:
            analysis['detailed_analysis'] = self._detailed_analysis(metrics)
        
        return analysis
    
    def _calculate_performance_metrics(self, metrics):
        """
        Calculate advanced performance metrics
        """
        
        total_time = metrics.get('cpu_time_ns', 0) + metrics.get('wait_time_ns', 0)
        
        return {
            'cpu_efficiency': metrics.get('cpu_percent', 0),
            'io_intensity': metrics.get('io_percent', 0),
            'context_switch_rate': metrics.get('context_switches', 0) / max(total_time / 1e9, 1),
            'syscall_rate': metrics.get('total_syscalls', 0) / max(total_time / 1e9, 1),
            'avg_syscall_duration_us': metrics.get('avg_syscall_duration', 0) / 1000,
            'io_throughput_mbps': metrics.get('total_io_bytes', 0) / max(total_time / 1e9, 1) / 1e6,
            'net_throughput_mbps': metrics.get('total_net_bytes', 0) / max(total_time / 1e9, 1) / 1e6
        }
    
    def _analyze_resource_utilization(self, metrics):
        """
        Analyze resource utilization patterns
        """
        
        cpu_percent = metrics.get('cpu_percent', 0)
        io_percent = metrics.get('io_percent', 0)
        wait_percent = metrics.get('wait_percent', 0)
        
        # Calculate utilization efficiency
        total_active = cpu_percent + io_percent
        utilization_efficiency = total_active / 100.0 if total_active > 0 else 0
        
        return {
            'cpu_utilization': cpu_percent,
            'io_utilization': io_percent,
            'idle_time': wait_percent,
            'utilization_efficiency': utilization_efficiency * 100,
            'resource_balance': self._calculate_resource_balance(cpu_percent, io_percent),
            'waste_analysis': {
                'idle_waste': wait_percent,
                'context_switch_overhead': min(metrics.get('context_switches', 0) / 1000, 20),
                'syscall_overhead': min(metrics.get('total_syscalls', 0) / 10000, 15)
            }
        }
    
    def _calculate_resource_balance(self, cpu_percent, io_percent):
        """
        Calculate how balanced the resource usage is
        """
        
        if cpu_percent + io_percent == 0:
            return 0
        
        # Perfect balance would be equal CPU and I/O usage
        balance_ratio = min(cpu_percent, io_percent) / max(cpu_percent, io_percent)
        return balance_ratio * 100
    
    def _identify_bottlenecks(self, metrics):
        """
        Identify potential performance bottlenecks
        """
        
        bottlenecks = []
        
        # CPU bottleneck
        if metrics.get('cpu_percent', 0) > 90:
            bottlenecks.append({
                'type': 'CPU',
                'severity': 'High',
                'description': 'CPU utilization is very high',
                'impact': 'May limit overall job performance'
            })
        
        # I/O bottleneck
        if metrics.get('io_percent', 0) > 50:
            bottlenecks.append({
                'type': 'I/O',
                'severity': 'Medium' if metrics.get('io_percent', 0) < 70 else 'High',
                'description': 'High I/O activity detected',
                'impact': 'I/O operations may be limiting performance'
            })
        
        # Context switching bottleneck
        if metrics.get('context_switches', 0) > 10000:
            bottlenecks.append({
                'type': 'Context Switching',
                'severity': 'Medium',
                'description': 'Excessive context switching',
                'impact': 'High overhead from task switching'
            })
        
        # Memory bottleneck (if available)
        if 'memory_usage' in metrics and metrics['memory_usage'] > 0.9:
            bottlenecks.append({
                'type': 'Memory',
                'severity': 'High',
                'description': 'Memory usage is very high',
                'impact': 'May cause swapping and performance degradation'
            })
        
        # Idle bottleneck
        if metrics.get('wait_percent', 0) > 60:
            bottlenecks.append({
                'type': 'Idle/Wait',
                'severity': 'Medium',
                'description': 'Job spends significant time waiting',
                'impact': 'Resources are underutilized'
            })
        
        return bottlenecks
    
    def _generate_optimization_suggestions(self, metrics, classification):
        """
        Generate specific optimization suggestions
        """
        
        suggestions = []
        
        cpu_percent = metrics.get('cpu_percent', 0)
        io_percent = metrics.get('io_percent', 0)
        context_switches = metrics.get('context_switches', 0)
        
        # CPU optimization
        if classification == 'CPU-bound':
            suggestions.extend([
                {
                    'category': 'CPU Optimization',
                    'suggestion': 'Consider using more CPU cores or nodes',
                    'priority': 'High',
                    'implementation': 'Increase --cpus-per-task or --ntasks in Slurm'
                },
                {
                    'category': 'CPU Optimization',
                    'suggestion': 'Optimize algorithms for vectorization',
                    'priority': 'Medium',
                    'implementation': 'Use SIMD instructions, OpenMP, or vectorized libraries'
                }
            ])
        
        # I/O optimization
        if io_percent > 30:
            suggestions.extend([
                {
                    'category': 'I/O Optimization',
                    'suggestion': 'Use faster storage or parallel I/O',
                    'priority': 'High',
                    'implementation': 'Request SSD storage or use MPI-IO for parallel access'
                },
                {
                    'category': 'I/O Optimization',
                    'suggestion': 'Implement I/O buffering and batching',
                    'priority': 'Medium',
                    'implementation': 'Increase buffer sizes, batch small I/O operations'
                }
            ])
        
        # Memory optimization
        if context_switches > 5000:
            suggestions.append({
                'category': 'Memory/Threading',
                'suggestion': 'Reduce thread contention and context switching',
                'priority': 'Medium',
                'implementation': 'Optimize thread pool size, reduce lock contention'
            })
        
        # Resource allocation
        if metrics.get('wait_percent', 0) > 40:
            suggestions.append({
                'category': 'Resource Allocation',
                'suggestion': 'Reduce resource allocation to match actual usage',
                'priority': 'Low',
                'implementation': 'Decrease requested CPUs/memory to improve queue times'
            })
        
        return suggestions
    
    def _detailed_analysis(self, metrics):
        """
        Perform detailed analysis of specific metrics
        """
        
        return {
            'syscall_analysis': {
                'total_syscalls': metrics.get('total_syscalls', 0),
                'io_syscalls': metrics.get('io_syscalls', 0),
                'net_syscalls': metrics.get('net_syscalls', 0),
                'avg_duration_us': metrics.get('avg_syscall_duration', 0) / 1000,
                'syscall_efficiency': self._calculate_syscall_efficiency(metrics)
            },
            'scheduling_analysis': {
                'context_switches': metrics.get('context_switches', 0),
                'cpu_time_ms': metrics.get('cpu_time_ns', 0) / 1e6,
                'wait_time_ms': metrics.get('wait_time_ns', 0) / 1e6,
                'scheduling_efficiency': metrics.get('cpu_percent', 0)
            },
            'io_analysis': {
                'total_bytes': metrics.get('total_io_bytes', 0),
                'read_bytes': metrics.get('read_bytes', 0),
                'write_bytes': metrics.get('write_bytes', 0),
                'operations': metrics.get('io_operations', 0),
                'avg_operation_size': metrics.get('total_io_bytes', 0) / max(metrics.get('io_operations', 1), 1)
            },
            'network_analysis': {
                'total_bytes': metrics.get('total_net_bytes', 0),
                'send_bytes': metrics.get('send_bytes', 0),
                'recv_bytes': metrics.get('recv_bytes', 0),
                'operations': metrics.get('net_operations', 0)
            }
        }
    
    def _calculate_syscall_efficiency(self, metrics):
        """
        Calculate syscall efficiency score
        """
        
        total_syscalls = metrics.get('total_syscalls', 0)
        avg_duration = metrics.get('avg_syscall_duration', 0)
        
        if total_syscalls == 0:
            return 0
        
        # Lower average duration and reasonable syscall count = higher efficiency
        duration_score = max(0, 100 - (avg_duration / 1000))  # Penalize long syscalls
        frequency_score = min(100, total_syscalls / 100)  # Reasonable activity level
        
        return (duration_score + frequency_score) / 2
    
    def _display_profile_summary(self, analysis):
        """
        Display a summary of the profiling analysis
        """
        
        print("\n" + "=" * 60)
        print("JOB PROFILING SUMMARY")
        print("=" * 60)
        
        job_info = analysis['job_info']
        print(f"Job ID: {job_info['job_id']}")
        print(f"User: {job_info['user']}")
        print(f"Duration: {job_info['duration']:.1f} seconds")
        print(f"Classification: {job_info['classification']}")
        print(f"Efficiency Score: {job_info['efficiency_score']:.1f}/100")
        
        print("\nPERFORMANCE METRICS:")
        perf = analysis['performance_metrics']
        print(f"  CPU Efficiency: {perf['cpu_efficiency']:.1f}%")
        print(f"  I/O Intensity: {perf['io_intensity']:.1f}%")
        print(f"  Context Switch Rate: {perf['context_switch_rate']:.1f}/sec")
        print(f"  Syscall Rate: {perf['syscall_rate']:.1f}/sec")
        print(f"  I/O Throughput: {perf['io_throughput_mbps']:.2f} MB/s")
        
        print("\nRESOURCE UTILIZATION:")
        resource = analysis['resource_utilization']
        print(f"  CPU Utilization: {resource['cpu_utilization']:.1f}%")
        print(f"  I/O Utilization: {resource['io_utilization']:.1f}%")
        print(f"  Idle Time: {resource['idle_time']:.1f}%")
        print(f"  Utilization Efficiency: {resource['utilization_efficiency']:.1f}%")
        
        bottlenecks = analysis['bottleneck_analysis']
        if bottlenecks:
            print("\nIDENTIFIED BOTTLENECKS:")
            for bottleneck in bottlenecks:
                print(f"  • {bottleneck['type']} ({bottleneck['severity']}): {bottleneck['description']}")
        
        suggestions = analysis['optimization_suggestions']
        if suggestions:
            print("\nOPTIMIZATION SUGGESTIONS:")
            for suggestion in suggestions[:5]:  # Show top 5
                print(f"  • [{suggestion['priority']}] {suggestion['suggestion']}")
                print(f"    Implementation: {suggestion['implementation']}")
        
        print("\n" + "=" * 60)

def main():
    """
    Main function for job profiling
    """
    
    parser = argparse.ArgumentParser(description='Advanced Job Profiling Tool')
    parser.add_argument('--job-id', '-j', required=True, help='Slurm job ID to profile')
    parser.add_argument('--duration', '-d', type=int, default=300, help='Profiling duration in seconds')
    parser.add_argument('--detailed', action='store_true', help='Include detailed analysis')
    parser.add_argument('--config', '-c', help='Configuration file')
    
    args = parser.parse_args()
    
    # Load configuration
    config = {}
    if args.config:
        import yaml
        with open(args.config, 'r') as f:
            config = yaml.safe_load(f)
    
    # Check for root privileges
    import os
    if os.geteuid() != 0:
        print("Error: This tool requires root privileges to use eBPF")
        sys.exit(1)
    
    # Create profiler and run analysis
    profiler = JobProfiler(config)
    
    try:
        analysis = profiler.profile_job(
            job_id=args.job_id,
            duration=args.duration,
            detailed=args.detailed
        )
        
        if analysis:
            print("\nProfiling completed successfully!")
        else:
            print("\nProfiling failed!")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\nProfiling interrupted by user")
    except Exception as e:
        print(f"\nError during profiling: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()