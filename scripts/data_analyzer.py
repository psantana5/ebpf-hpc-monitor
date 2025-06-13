#!/usr/bin/env python3
"""
Data Analyzer and Job Classifier

This module analyzes eBPF monitoring data and classifies jobs based on
their behavior patterns (CPU-bound, I/O-bound, Idle-heavy).

Author: Pau Santana
License: MIT
"""

import logging
import statistics
import time
from collections import defaultdict
from typing import Dict, List, Set, Tuple, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

class JobAnalyzer:
    """
    Analyzes monitoring data to extract meaningful metrics
    """
    
    def __init__(self):
        self.syscall_names = self._load_syscall_names()
        self.io_syscalls = {0, 1, 2, 3, 4, 5, 8, 19, 20, 21, 22}  # read, write, open, close, etc.
        self.net_syscalls = {41, 42, 43, 44, 45, 46, 47, 48, 49, 50}  # socket, connect, send, recv, etc.
    
    def _load_syscall_names(self) -> Dict[int, str]:
        """Load syscall number to name mapping"""
        
        # Common x86_64 syscalls
        syscalls = {
            0: 'read', 1: 'write', 2: 'open', 3: 'close', 4: 'stat',
            5: 'fstat', 6: 'lstat', 7: 'poll', 8: 'lseek', 9: 'mmap',
            10: 'mprotect', 11: 'munmap', 12: 'brk', 13: 'rt_sigaction',
            14: 'rt_sigprocmask', 15: 'rt_sigreturn', 16: 'ioctl', 17: 'pread64',
            18: 'pwrite64', 19: 'readv', 20: 'writev', 21: 'access',
            22: 'pipe', 23: 'select', 24: 'sched_yield', 25: 'mremap',
            26: 'msync', 27: 'mincore', 28: 'madvise', 29: 'shmget',
            30: 'shmat', 31: 'shmctl', 32: 'dup', 33: 'dup2',
            34: 'pause', 35: 'nanosleep', 36: 'getitimer', 37: 'alarm',
            38: 'setitimer', 39: 'getpid', 40: 'sendfile', 41: 'socket',
            42: 'connect', 43: 'accept', 44: 'sendto', 45: 'recvfrom',
            46: 'sendmsg', 47: 'recvmsg', 48: 'shutdown', 49: 'bind',
            50: 'listen', 51: 'getsockname', 52: 'getpeername', 53: 'socketpair',
            54: 'setsockopt', 55: 'getsockopt', 56: 'clone', 57: 'fork',
            58: 'vfork', 59: 'execve', 60: 'exit', 61: 'wait4',
            62: 'kill', 63: 'uname', 64: 'semget', 65: 'semop',
            66: 'semctl', 67: 'shmdt', 68: 'msgget', 69: 'msgsnd',
            70: 'msgrcv', 71: 'msgctl', 72: 'fcntl', 73: 'flock',
            74: 'fsync', 75: 'fdatasync', 76: 'truncate', 77: 'ftruncate',
            78: 'getdents', 79: 'getcwd', 80: 'chdir', 81: 'fchdir',
            82: 'rename', 83: 'mkdir', 84: 'rmdir', 85: 'creat',
            86: 'link', 87: 'unlink', 88: 'symlink', 89: 'readlink',
            90: 'chmod', 91: 'fchmod', 92: 'chown', 93: 'fchown',
            94: 'lchown', 95: 'umask', 96: 'gettimeofday', 97: 'getrlimit',
            98: 'getrusage', 99: 'sysinfo', 100: 'times'
        }
        
        return syscalls
    
    def aggregate_pid_metrics(self, pids: Set[int], probe_data: Dict) -> Dict:
        """Aggregate metrics for a set of PIDs"""
        
        if not pids:
            return self._empty_metrics()
        
        # Extract data for the specified PIDs
        syscall_counts = probe_data.get('syscall_counts', {})
        sched_events = probe_data.get('sched_events', {})
        io_events = probe_data.get('io_events', {})
        net_events = probe_data.get('net_events', {})
        detailed_syscalls = probe_data.get('detailed_syscalls', {})
        
        # Aggregate syscall data
        total_syscalls = 0
        io_syscalls = 0
        net_syscalls = 0
        syscall_durations = []
        
        for pid in pids:
            if pid in syscall_counts:
                for syscall_id, count in syscall_counts[pid].items():
                    total_syscalls += count
                    
                    if syscall_id in self.io_syscalls:
                        io_syscalls += count
                    elif syscall_id in self.net_syscalls:
                        net_syscalls += count
            
            # Collect syscall durations
            if pid in detailed_syscalls:
                for event in detailed_syscalls[pid]:
                    syscall_durations.append(event['duration'])
        
        # Aggregate scheduling data
        context_switches = 0
        cpu_time_ns = 0
        wait_time_ns = 0
        
        for pid in pids:
            if pid in sched_events:
                events = sched_events[pid]
                context_switches += len(events)
                
                # Calculate CPU vs wait time from scheduling events
                cpu_periods, wait_periods = self._analyze_sched_events(events, pid)
                cpu_time_ns += sum(cpu_periods)
                wait_time_ns += sum(wait_periods)
        
        # Aggregate I/O data
        total_io_bytes = 0
        read_bytes = 0
        write_bytes = 0
        io_operations = 0
        
        for pid in pids:
            if pid in io_events:
                for event in io_events[pid]:
                    total_io_bytes += event['bytes']
                    io_operations += 1
                    
                    if event['is_read']:
                        read_bytes += event['bytes']
                    else:
                        write_bytes += event['bytes']
        
        # Aggregate network data
        total_net_bytes = 0
        send_bytes = 0
        recv_bytes = 0
        net_operations = 0
        
        for pid in pids:
            if pid in net_events:
                for event in net_events[pid]:
                    total_net_bytes += event['bytes']
                    net_operations += 1
                    
                    if event['is_send']:
                        send_bytes += event['bytes']
                    else:
                        recv_bytes += event['bytes']
        
        # Calculate percentages
        total_time_ns = cpu_time_ns + wait_time_ns
        
        if total_time_ns > 0:
            cpu_percent = (cpu_time_ns / total_time_ns) * 100
            wait_percent = (wait_time_ns / total_time_ns) * 100
        else:
            cpu_percent = 0
            wait_percent = 0
        
        # Calculate I/O percentage (rough estimate)
        if total_syscalls > 0:
            io_percent = (io_syscalls / total_syscalls) * 100
            net_percent = (net_syscalls / total_syscalls) * 100
        else:
            io_percent = 0
            net_percent = 0
        
        # Calculate average syscall duration
        avg_syscall_duration = statistics.mean(syscall_durations) if syscall_durations else 0
        
        return {
            'total_syscalls': total_syscalls,
            'io_syscalls': io_syscalls,
            'net_syscalls': net_syscalls,
            'context_switches': context_switches,
            'cpu_time_ns': cpu_time_ns,
            'wait_time_ns': wait_time_ns,
            'cpu_percent': cpu_percent,
            'wait_percent': wait_percent,
            'io_percent': io_percent,
            'net_percent': net_percent,
            'total_io_bytes': total_io_bytes,
            'read_bytes': read_bytes,
            'write_bytes': write_bytes,
            'io_operations': io_operations,
            'total_net_bytes': total_net_bytes,
            'send_bytes': send_bytes,
            'recv_bytes': recv_bytes,
            'net_operations': net_operations,
            'avg_syscall_duration': avg_syscall_duration,
            'monitored_pids': len(pids)
        }
    
    def _analyze_sched_events(self, events: List[Dict], target_pid: int) -> Tuple[List[int], List[int]]:
        """Analyze scheduling events to determine CPU vs wait time"""
        
        cpu_periods = []
        wait_periods = []
        
        if len(events) < 2:
            return cpu_periods, wait_periods
        
        # Sort events by timestamp
        sorted_events = sorted(events, key=lambda x: x['timestamp'])
        
        last_scheduled_in = None
        
        for event in sorted_events:
            if event['next_pid'] == target_pid:
                # Process was scheduled in
                last_scheduled_in = event['timestamp']
            elif event['prev_pid'] == target_pid and last_scheduled_in:
                # Process was scheduled out
                cpu_time = event['timestamp'] - last_scheduled_in
                cpu_periods.append(cpu_time)
                last_scheduled_in = None
        
        # Estimate wait times between CPU periods
        for i in range(len(cpu_periods) - 1):
            # This is a rough estimate - actual wait time calculation
            # would require more sophisticated analysis
            wait_periods.append(cpu_periods[i] // 2)  # Simplified estimate
        
        return cpu_periods, wait_periods
    
    def update_metrics(self, old_metrics: Dict, new_metrics: Dict) -> Dict:
        """Update existing metrics with new data"""
        
        updated = old_metrics.copy()
        
        # Accumulate counters
        for key in ['total_syscalls', 'io_syscalls', 'net_syscalls', 'context_switches',
                   'cpu_time_ns', 'wait_time_ns', 'total_io_bytes', 'read_bytes',
                   'write_bytes', 'io_operations', 'total_net_bytes', 'send_bytes',
                   'recv_bytes', 'net_operations']:
            updated[key] = old_metrics.get(key, 0) + new_metrics.get(key, 0)
        
        # Recalculate percentages
        total_time_ns = updated['cpu_time_ns'] + updated['wait_time_ns']
        if total_time_ns > 0:
            updated['cpu_percent'] = (updated['cpu_time_ns'] / total_time_ns) * 100
            updated['wait_percent'] = (updated['wait_time_ns'] / total_time_ns) * 100
        
        if updated['total_syscalls'] > 0:
            updated['io_percent'] = (updated['io_syscalls'] / updated['total_syscalls']) * 100
            updated['net_percent'] = (updated['net_syscalls'] / updated['total_syscalls']) * 100
        
        # Update average syscall duration (weighted average)
        old_avg = old_metrics.get('avg_syscall_duration', 0)
        new_avg = new_metrics.get('avg_syscall_duration', 0)
        old_count = old_metrics.get('total_syscalls', 0)
        new_count = new_metrics.get('total_syscalls', 0)
        
        if old_count + new_count > 0:
            updated['avg_syscall_duration'] = (
                (old_avg * old_count + new_avg * new_count) / (old_count + new_count)
            )
        
        return updated
    
    def _empty_metrics(self) -> Dict:
        """Return empty metrics structure"""
        
        return {
            'total_syscalls': 0,
            'io_syscalls': 0,
            'net_syscalls': 0,
            'context_switches': 0,
            'cpu_time_ns': 0,
            'wait_time_ns': 0,
            'cpu_percent': 0,
            'wait_percent': 0,
            'io_percent': 0,
            'net_percent': 0,
            'total_io_bytes': 0,
            'read_bytes': 0,
            'write_bytes': 0,
            'io_operations': 0,
            'total_net_bytes': 0,
            'send_bytes': 0,
            'recv_bytes': 0,
            'net_operations': 0,
            'avg_syscall_duration': 0,
            'monitored_pids': 0
        }
    
    def get_syscall_breakdown(self, probe_data: Dict, pids: Set[int]) -> Dict[str, int]:
        """Get breakdown of syscalls by name"""
        
        syscall_counts = probe_data.get('syscall_counts', {})
        breakdown = defaultdict(int)
        
        for pid in pids:
            if pid in syscall_counts:
                for syscall_id, count in syscall_counts[pid].items():
                    syscall_name = self.syscall_names.get(syscall_id, f'syscall_{syscall_id}')
                    breakdown[syscall_name] += count
        
        return dict(breakdown)


class JobClassifier:
    """
    Classifies jobs based on their behavior patterns
    """
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        
        # Classification thresholds
        self.cpu_bound_threshold = self.config.get('cpu_bound_threshold', 70.0)
        self.io_bound_threshold = self.config.get('io_bound_threshold', 30.0)
        self.idle_threshold = self.config.get('idle_threshold', 50.0)
        self.context_switch_threshold = self.config.get('context_switch_threshold', 1000)
    
    def classify_job(self, metrics: Dict) -> str:
        """Classify a job based on its metrics"""
        
        cpu_percent = metrics.get('cpu_percent', 0)
        io_percent = metrics.get('io_percent', 0)
        wait_percent = metrics.get('wait_percent', 0)
        context_switches = metrics.get('context_switches', 0)
        total_syscalls = metrics.get('total_syscalls', 0)
        
        # Handle edge cases
        if total_syscalls == 0:
            return 'Unknown'
        
        # Primary classification based on CPU usage
        if cpu_percent >= self.cpu_bound_threshold:
            # High CPU usage
            if io_percent < 10:
                return 'CPU-bound'
            else:
                return 'CPU-IO-mixed'
        
        elif io_percent >= self.io_bound_threshold:
            # High I/O activity
            if context_switches > self.context_switch_threshold:
                return 'IO-bound-intensive'
            else:
                return 'IO-bound'
        
        elif wait_percent >= self.idle_threshold:
            # High wait time
            if context_switches > self.context_switch_threshold:
                return 'Idle-heavy-switching'
            else:
                return 'Idle-heavy'
        
        else:
            # Mixed or balanced workload
            if context_switches > self.context_switch_threshold:
                return 'Mixed-intensive'
            else:
                return 'Balanced'
    
    def get_recommendations(self, metrics: Dict, classification: str) -> List[str]:
        """Get optimization recommendations based on classification"""
        
        recommendations = []
        
        cpu_percent = metrics.get('cpu_percent', 0)
        io_percent = metrics.get('io_percent', 0)
        context_switches = metrics.get('context_switches', 0)
        total_io_bytes = metrics.get('total_io_bytes', 0)
        net_operations = metrics.get('net_operations', 0)
        
        if classification == 'CPU-bound':
            recommendations.extend([
                "Job is CPU-intensive, consider using more CPU cores",
                "Optimize algorithms for better CPU utilization",
                "Consider CPU affinity settings for better cache locality"
            ])
            
            if context_switches > 5000:
                recommendations.append("High context switching detected, check for unnecessary thread creation")
        
        elif classification.startswith('IO-bound'):
            recommendations.extend([
                "Job is I/O intensive, consider faster storage or I/O optimization",
                "Use asynchronous I/O or buffering to improve performance",
                "Consider using SSDs or parallel file systems"
            ])
            
            if total_io_bytes > 1e9:  # > 1GB
                recommendations.append("Large I/O volume detected, consider data compression or caching")
        
        elif classification.startswith('Idle-heavy'):
            recommendations.extend([
                "Job has significant idle time, investigate bottlenecks",
                "Consider reducing resource allocation if consistently idle",
                "Check for synchronization issues or external dependencies"
            ])
        
        elif classification == 'Mixed-intensive':
            recommendations.extend([
                "Job has mixed workload with high activity",
                "Consider hybrid optimization strategies",
                "Monitor resource usage patterns for fine-tuning"
            ])
        
        # Network-specific recommendations
        if net_operations > 1000:
            recommendations.append("High network activity detected, consider network optimization")
        
        # Context switching recommendations
        if context_switches > 10000:
            recommendations.append("Very high context switching, investigate thread/process management")
        
        # Memory recommendations (if available)
        if 'memory_usage' in metrics and metrics['memory_usage'] > 0.8:
            recommendations.append("High memory usage detected, consider memory optimization")
        
        return recommendations
    
    def get_efficiency_score(self, metrics: Dict) -> float:
        """Calculate an efficiency score (0-100) for the job"""
        
        cpu_percent = metrics.get('cpu_percent', 0)
        io_percent = metrics.get('io_percent', 0)
        wait_percent = metrics.get('wait_percent', 0)
        context_switches = metrics.get('context_switches', 0)
        total_syscalls = metrics.get('total_syscalls', 0)
        
        if total_syscalls == 0:
            return 0.0
        
        # Base score from CPU utilization
        cpu_score = min(cpu_percent, 100) * 0.4
        
        # I/O efficiency (moderate I/O is good, too much or too little is bad)
        if io_percent < 5:
            io_score = io_percent * 4  # Scale up low I/O
        elif io_percent > 50:
            io_score = max(0, 50 - (io_percent - 50))  # Penalize excessive I/O
        else:
            io_score = 20  # Optimal I/O range
        
        io_score *= 0.3
        
        # Wait time penalty
        wait_penalty = min(wait_percent * 0.5, 30)
        
        # Context switching penalty
        if context_switches > 1000:
            cs_penalty = min((context_switches - 1000) / 1000 * 10, 20)
        else:
            cs_penalty = 0
        
        # Calculate final score
        efficiency_score = cpu_score + io_score - wait_penalty - cs_penalty
        
        return max(0, min(100, efficiency_score))
    
    def compare_jobs(self, job_metrics: List[Dict]) -> Dict:
        """Compare multiple jobs and provide insights"""
        
        if not job_metrics:
            return {}
        
        classifications = []
        efficiency_scores = []
        cpu_percentages = []
        io_percentages = []
        
        for metrics in job_metrics:
            classifications.append(self.classify_job(metrics))
            efficiency_scores.append(self.get_efficiency_score(metrics))
            cpu_percentages.append(metrics.get('cpu_percent', 0))
            io_percentages.append(metrics.get('io_percent', 0))
        
        # Calculate statistics
        avg_efficiency = statistics.mean(efficiency_scores)
        avg_cpu = statistics.mean(cpu_percentages)
        avg_io = statistics.mean(io_percentages)
        
        # Find best and worst performing jobs
        best_job_idx = efficiency_scores.index(max(efficiency_scores))
        worst_job_idx = efficiency_scores.index(min(efficiency_scores))
        
        # Classification distribution
        classification_counts = {}
        for cls in classifications:
            classification_counts[cls] = classification_counts.get(cls, 0) + 1
        
        return {
            'total_jobs': len(job_metrics),
            'average_efficiency': avg_efficiency,
            'average_cpu_percent': avg_cpu,
            'average_io_percent': avg_io,
            'best_job_index': best_job_idx,
            'worst_job_index': worst_job_idx,
            'best_efficiency': efficiency_scores[best_job_idx],
            'worst_efficiency': efficiency_scores[worst_job_idx],
            'classification_distribution': classification_counts,
            'efficiency_scores': efficiency_scores
        }


def main():
    """Main function for standalone usage"""
    
    import argparse
    import json
    
    parser = argparse.ArgumentParser(description='Analyze job monitoring data')
    parser.add_argument('--input', '-i', required=True, help='Input JSON file with monitoring data')
    parser.add_argument('--output', '-o', help='Output file for analysis results')
    parser.add_argument('--format', '-f', choices=['json', 'csv'], default='json', help='Output format')
    
    args = parser.parse_args()
    
    # Load monitoring data
    with open(args.input, 'r') as f:
        data = json.load(f)
    
    # Analyze jobs
    classifier = JobClassifier()
    job_metrics = [job['metrics'] for job in data.get('jobs', [])]
    
    if not job_metrics:
        print("No job metrics found in input data")
        return
    
    # Perform analysis
    comparison = classifier.compare_jobs(job_metrics)
    
    # Add individual job analysis
    for i, job in enumerate(data.get('jobs', [])):
        metrics = job['metrics']
        job['analysis'] = {
            'classification': classifier.classify_job(metrics),
            'efficiency_score': classifier.get_efficiency_score(metrics),
            'recommendations': classifier.get_recommendations(metrics, classifier.classify_job(metrics))
        }
    
    # Prepare output
    output_data = {
        'analysis_summary': comparison,
        'jobs': data.get('jobs', []),
        'analysis_timestamp': time.time()
    }
    
    # Save results
    if args.output:
        if args.format == 'json':
            with open(args.output, 'w') as f:
                json.dump(output_data, f, indent=2, default=str)
        elif args.format == 'csv':
            # Convert to CSV
            csv_data = []
            for job in output_data['jobs']:
                row = {
                    'job_id': job.get('job_id'),
                    'user': job.get('user'),
                    'classification': job['analysis']['classification'],
                    'efficiency_score': job['analysis']['efficiency_score'],
                    **job['metrics']
                }
                csv_data.append(row)
            
            df = pd.DataFrame(csv_data)
            df.to_csv(args.output, index=False)
        
        print(f"Analysis results saved to {args.output}")
    else:
        print(json.dumps(output_data, indent=2, default=str))


if __name__ == '__main__':
    main()