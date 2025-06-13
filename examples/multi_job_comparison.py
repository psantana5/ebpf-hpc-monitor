#!/usr/bin/env python3
"""
Multi-Job Comparison Example

This example demonstrates how to compare multiple jobs
to identify patterns and optimization opportunities.

Author: Your Name
License: MIT
"""

import sys
import json
import argparse
from pathlib import Path
from datetime import datetime
import matplotlib.pyplot as plt
import pandas as pd
from typing import List, Dict, Any

# Add the scripts directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent / 'scripts'))

from data_analyzer import JobAnalyzer, JobClassifier
from slurm_integration import SlurmIntegration

class JobComparator:
    """
    Compare multiple jobs to identify patterns and optimization opportunities
    """
    
    def __init__(self, config=None):
        self.config = config or {}
        self.analyzer = JobAnalyzer()
        self.classifier = JobClassifier()
        self.slurm = SlurmIntegration(self.config.get('slurm', {}))
    
    def compare_jobs_from_files(self, job_files: List[str], output_dir: str = "."):
        """
        Compare jobs from multiple JSON result files
        
        Args:
            job_files: List of JSON files containing job monitoring results
            output_dir: Directory to save comparison results
        """
        
        jobs_data = []
        
        # Load all job data
        for file_path in job_files:
            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)
                    
                # Extract jobs from the file
                if 'jobs' in data:
                    for job in data['jobs']:
                        job['source_file'] = file_path
                        jobs_data.append(job)
                else:
                    # Assume single job format
                    data['source_file'] = file_path
                    jobs_data.append(data)
                    
            except Exception as e:
                print(f"Error loading {file_path}: {e}")
                continue
        
        if not jobs_data:
            print("No valid job data found")
            return None
        
        print(f"Loaded {len(jobs_data)} jobs for comparison")
        
        # Perform comparison
        comparison = self._compare_jobs(jobs_data)
        
        # Save results
        output_file = Path(output_dir) / f"job_comparison_{int(datetime.now().timestamp())}.json"
        with open(output_file, 'w') as f:
            json.dump(comparison, f, indent=2, default=str)
        
        # Generate visualizations
        self._generate_comparison_plots(comparison, output_dir)
        
        # Display summary
        self._display_comparison_summary(comparison)
        
        print(f"\nComparison results saved to: {output_file}")
        return comparison
    
    def compare_user_jobs(self, user: str, days: int = 7, output_dir: str = "."):
        """
        Compare recent jobs for a specific user
        
        Args:
            user: Username to analyze
            days: Number of days to look back
            output_dir: Directory to save results
        """
        
        print(f"Analyzing jobs for user '{user}' from the last {days} days")
        
        # Get job history from Slurm
        try:
            jobs = self.slurm.get_user_jobs(user, days=days)
            if not jobs:
                print(f"No jobs found for user {user}")
                return None
            
            print(f"Found {len(jobs)} jobs for analysis")
            
            # For this example, we'll simulate job data since we don't have actual monitoring data
            # In a real scenario, you would load the monitoring data for each job
            jobs_data = self._simulate_job_data(jobs)
            
            # Perform comparison
            comparison = self._compare_jobs(jobs_data)
            
            # Save and display results
            output_file = Path(output_dir) / f"user_{user}_comparison_{int(datetime.now().timestamp())}.json"
            with open(output_file, 'w') as f:
                json.dump(comparison, f, indent=2, default=str)
            
            self._generate_comparison_plots(comparison, output_dir, prefix=f"user_{user}_")
            self._display_comparison_summary(comparison)
            
            print(f"\nUser comparison results saved to: {output_file}")
            return comparison
            
        except Exception as e:
            print(f"Error analyzing user jobs: {e}")
            return None
    
    def _compare_jobs(self, jobs_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Perform detailed comparison of multiple jobs
        """
        
        comparison = {
            'summary': {
                'total_jobs': len(jobs_data),
                'analysis_timestamp': datetime.now().isoformat(),
                'job_classifications': {},
                'efficiency_stats': {},
                'resource_usage_stats': {}
            },
            'jobs': [],
            'patterns': {},
            'recommendations': {},
            'outliers': []
        }
        
        # Analyze each job
        efficiency_scores = []
        cpu_percentages = []
        io_percentages = []
        classifications = []
        
        for job_data in jobs_data:
            metrics = job_data.get('metrics', {})
            
            # Classify job
            classification = self.classifier.classify_job(metrics)
            efficiency = self.classifier.get_efficiency_score(metrics)
            
            job_analysis = {
                'job_id': job_data.get('job_id', 'unknown'),
                'user': job_data.get('user', 'unknown'),
                'duration': job_data.get('duration_seconds', 0),
                'classification': classification,
                'efficiency_score': efficiency,
                'metrics': metrics,
                'source_file': job_data.get('source_file', 'unknown')
            }
            
            comparison['jobs'].append(job_analysis)
            
            # Collect statistics
            efficiency_scores.append(efficiency)
            cpu_percentages.append(metrics.get('cpu_percent', 0))
            io_percentages.append(metrics.get('io_percent', 0))
            classifications.append(classification)
        
        # Calculate summary statistics
        comparison['summary']['job_classifications'] = {
            cls: classifications.count(cls) for cls in set(classifications)
        }
        
        comparison['summary']['efficiency_stats'] = {
            'mean': sum(efficiency_scores) / len(efficiency_scores),
            'min': min(efficiency_scores),
            'max': max(efficiency_scores),
            'std': self._calculate_std(efficiency_scores)
        }
        
        comparison['summary']['resource_usage_stats'] = {
            'cpu': {
                'mean': sum(cpu_percentages) / len(cpu_percentages),
                'min': min(cpu_percentages),
                'max': max(cpu_percentages)
            },
            'io': {
                'mean': sum(io_percentages) / len(io_percentages),
                'min': min(io_percentages),
                'max': max(io_percentages)
            }
        }
        
        # Identify patterns
        comparison['patterns'] = self._identify_patterns(comparison['jobs'])
        
        # Generate recommendations
        comparison['recommendations'] = self._generate_comparison_recommendations(comparison)
        
        # Identify outliers
        comparison['outliers'] = self._identify_outliers(comparison['jobs'])
        
        return comparison
    
    def _identify_patterns(self, jobs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Identify patterns across multiple jobs
        """
        
        patterns = {
            'classification_trends': {},
            'efficiency_trends': {},
            'resource_patterns': {},
            'temporal_patterns': {}
        }
        
        # Classification patterns
        classifications = [job['classification'] for job in jobs]
        patterns['classification_trends'] = {
            'most_common': max(set(classifications), key=classifications.count),
            'distribution': {cls: classifications.count(cls) for cls in set(classifications)}
        }
        
        # Efficiency patterns
        efficiencies = [job['efficiency_score'] for job in jobs]
        patterns['efficiency_trends'] = {
            'average': sum(efficiencies) / len(efficiencies),
            'improving_jobs': len([e for e in efficiencies if e > 70]),
            'poor_jobs': len([e for e in efficiencies if e < 30])
        }
        
        # Resource usage patterns
        cpu_usage = [job['metrics'].get('cpu_percent', 0) for job in jobs]
        io_usage = [job['metrics'].get('io_percent', 0) for job in jobs]
        
        patterns['resource_patterns'] = {
            'high_cpu_jobs': len([c for c in cpu_usage if c > 80]),
            'high_io_jobs': len([i for i in io_usage if i > 50]),
            'balanced_jobs': len([i for i, (c, io) in enumerate(zip(cpu_usage, io_usage)) 
                                if 30 < c < 80 and 10 < io < 40]),
            'underutilized_jobs': len([i for i, (c, io) in enumerate(zip(cpu_usage, io_usage)) 
                                     if c < 30 and io < 20])
        }
        
        return patterns
    
    def _generate_comparison_recommendations(self, comparison: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate recommendations based on job comparison
        """
        
        recommendations = {
            'general': [],
            'efficiency': [],
            'resource_optimization': [],
            'workflow_improvements': []
        }
        
        patterns = comparison['patterns']
        efficiency_stats = comparison['summary']['efficiency_stats']
        
        # General recommendations
        if efficiency_stats['mean'] < 50:
            recommendations['general'].append({
                'priority': 'High',
                'category': 'Overall Efficiency',
                'issue': f"Average efficiency is low ({efficiency_stats['mean']:.1f}%)",
                'recommendation': 'Review job configurations and resource allocations'
            })
        
        # Resource optimization
        resource_stats = comparison['summary']['resource_usage_stats']
        if resource_stats['cpu']['mean'] < 40:
            recommendations['resource_optimization'].append({
                'priority': 'Medium',
                'category': 'CPU Utilization',
                'issue': f"Low average CPU utilization ({resource_stats['cpu']['mean']:.1f}%)",
                'recommendation': 'Consider reducing CPU allocation or optimizing algorithms'
            })
        
        if patterns['resource_patterns']['underutilized_jobs'] > len(comparison['jobs']) * 0.3:
            recommendations['resource_optimization'].append({
                'priority': 'High',
                'category': 'Resource Allocation',
                'issue': 'Many jobs are underutilizing resources',
                'recommendation': 'Review and optimize resource requests in job scripts'
            })
        
        # Workflow improvements
        if patterns['classification_trends']['most_common'] == 'Idle-heavy':
            recommendations['workflow_improvements'].append({
                'priority': 'High',
                'category': 'Job Efficiency',
                'issue': 'Most jobs are idle-heavy',
                'recommendation': 'Investigate causes of idle time and optimize job scheduling'
            })
        
        return recommendations
    
    def _identify_outliers(self, jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Identify outlier jobs that deviate significantly from the norm
        """
        
        outliers = []
        
        efficiencies = [job['efficiency_score'] for job in jobs]
        cpu_percentages = [job['metrics'].get('cpu_percent', 0) for job in jobs]
        
        mean_efficiency = sum(efficiencies) / len(efficiencies)
        std_efficiency = self._calculate_std(efficiencies)
        
        mean_cpu = sum(cpu_percentages) / len(cpu_percentages)
        std_cpu = self._calculate_std(cpu_percentages)
        
        for job in jobs:
            efficiency = job['efficiency_score']
            cpu_percent = job['metrics'].get('cpu_percent', 0)
            
            outlier_reasons = []
            
            # Check efficiency outliers
            if abs(efficiency - mean_efficiency) > 2 * std_efficiency:
                if efficiency < mean_efficiency:
                    outlier_reasons.append('Very low efficiency')
                else:
                    outlier_reasons.append('Exceptionally high efficiency')
            
            # Check CPU usage outliers
            if abs(cpu_percent - mean_cpu) > 2 * std_cpu:
                if cpu_percent < mean_cpu:
                    outlier_reasons.append('Very low CPU usage')
                else:
                    outlier_reasons.append('Very high CPU usage')
            
            # Check for extreme values
            if job['metrics'].get('context_switches', 0) > 50000:
                outlier_reasons.append('Excessive context switching')
            
            if job['metrics'].get('total_syscalls', 0) > 100000:
                outlier_reasons.append('Very high syscall activity')
            
            if outlier_reasons:
                outliers.append({
                    'job_id': job['job_id'],
                    'user': job['user'],
                    'reasons': outlier_reasons,
                    'efficiency_score': efficiency,
                    'metrics': job['metrics']
                })
        
        return outliers
    
    def _calculate_std(self, values: List[float]) -> float:
        """
        Calculate standard deviation
        """
        if len(values) < 2:
            return 0
        
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / (len(values) - 1)
        return variance ** 0.5
    
    def _simulate_job_data(self, jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Simulate job monitoring data for demonstration purposes
        In a real scenario, this would load actual monitoring data
        """
        
        import random
        
        simulated_jobs = []
        
        for job in jobs:
            # Simulate metrics based on job characteristics
            duration = random.randint(300, 7200)  # 5 minutes to 2 hours
            
            # Simulate different job types
            job_type = random.choice(['cpu_intensive', 'io_intensive', 'balanced', 'idle'])
            
            if job_type == 'cpu_intensive':
                cpu_percent = random.uniform(70, 95)
                io_percent = random.uniform(5, 20)
                context_switches = random.randint(1000, 5000)
            elif job_type == 'io_intensive':
                cpu_percent = random.uniform(20, 50)
                io_percent = random.uniform(40, 80)
                context_switches = random.randint(5000, 15000)
            elif job_type == 'balanced':
                cpu_percent = random.uniform(40, 70)
                io_percent = random.uniform(20, 40)
                context_switches = random.randint(2000, 8000)
            else:  # idle
                cpu_percent = random.uniform(5, 30)
                io_percent = random.uniform(5, 15)
                context_switches = random.randint(500, 2000)
            
            wait_percent = max(0, 100 - cpu_percent - io_percent)
            
            metrics = {
                'cpu_percent': cpu_percent,
                'io_percent': io_percent,
                'wait_percent': wait_percent,
                'context_switches': context_switches,
                'total_syscalls': random.randint(1000, 50000),
                'io_syscalls': random.randint(100, 5000),
                'net_syscalls': random.randint(10, 1000),
                'cpu_time_ns': int(duration * cpu_percent / 100 * 1e9),
                'wait_time_ns': int(duration * wait_percent / 100 * 1e9),
                'total_io_bytes': random.randint(1024*1024, 1024*1024*1024),
                'total_net_bytes': random.randint(1024, 1024*1024*100),
                'avg_syscall_duration': random.randint(1000, 10000)
            }
            
            simulated_jobs.append({
                'job_id': job.get('job_id', f"sim_{random.randint(1000, 9999)}"),
                'user': job.get('user', 'testuser'),
                'duration_seconds': duration,
                'metrics': metrics
            })
        
        return simulated_jobs
    
    def _generate_comparison_plots(self, comparison: Dict[str, Any], output_dir: str, prefix: str = ""):
        """
        Generate visualization plots for job comparison
        """
        
        try:
            import matplotlib.pyplot as plt
            import seaborn as sns
            
            # Set style
            plt.style.use('default')
            sns.set_palette("husl")
            
            jobs = comparison['jobs']
            
            # Create figure with subplots
            fig, axes = plt.subplots(2, 2, figsize=(15, 12))
            fig.suptitle('Job Comparison Analysis', fontsize=16, fontweight='bold')
            
            # 1. Efficiency Score Distribution
            efficiencies = [job['efficiency_score'] for job in jobs]
            axes[0, 0].hist(efficiencies, bins=20, alpha=0.7, color='skyblue', edgecolor='black')
            axes[0, 0].set_title('Efficiency Score Distribution')
            axes[0, 0].set_xlabel('Efficiency Score')
            axes[0, 0].set_ylabel('Number of Jobs')
            axes[0, 0].axvline(sum(efficiencies)/len(efficiencies), color='red', linestyle='--', label='Mean')
            axes[0, 0].legend()
            
            # 2. Classification Distribution
            classifications = [job['classification'] for job in jobs]
            class_counts = {cls: classifications.count(cls) for cls in set(classifications)}
            axes[0, 1].pie(class_counts.values(), labels=class_counts.keys(), autopct='%1.1f%%')
            axes[0, 1].set_title('Job Classification Distribution')
            
            # 3. CPU vs I/O Usage Scatter
            cpu_usage = [job['metrics'].get('cpu_percent', 0) for job in jobs]
            io_usage = [job['metrics'].get('io_percent', 0) for job in jobs]
            colors = [{'CPU-bound': 'red', 'I/O-bound': 'blue', 'Idle-heavy': 'gray', 'Balanced': 'green'}.get(cls, 'black') 
                     for cls in classifications]
            
            scatter = axes[1, 0].scatter(cpu_usage, io_usage, c=colors, alpha=0.6, s=50)
            axes[1, 0].set_title('CPU vs I/O Usage')
            axes[1, 0].set_xlabel('CPU Usage (%)')
            axes[1, 0].set_ylabel('I/O Usage (%)')
            axes[1, 0].grid(True, alpha=0.3)
            
            # Add legend for scatter plot
            unique_classes = list(set(classifications))
            legend_colors = [{'CPU-bound': 'red', 'I/O-bound': 'blue', 'Idle-heavy': 'gray', 'Balanced': 'green'}.get(cls, 'black') 
                           for cls in unique_classes]
            for i, cls in enumerate(unique_classes):
                axes[1, 0].scatter([], [], c=legend_colors[i], label=cls)
            axes[1, 0].legend()
            
            # 4. Efficiency vs Duration
            durations = [job['duration'] for job in jobs]
            axes[1, 1].scatter(durations, efficiencies, alpha=0.6, color='purple')
            axes[1, 1].set_title('Efficiency vs Job Duration')
            axes[1, 1].set_xlabel('Duration (seconds)')
            axes[1, 1].set_ylabel('Efficiency Score')
            axes[1, 1].grid(True, alpha=0.3)
            
            plt.tight_layout()
            
            # Save plot
            plot_file = Path(output_dir) / f"{prefix}job_comparison_plots.png"
            plt.savefig(plot_file, dpi=300, bbox_inches='tight')
            plt.close()
            
            print(f"Comparison plots saved to: {plot_file}")
            
        except ImportError:
            print("Matplotlib/Seaborn not available. Skipping plot generation.")
        except Exception as e:
            print(f"Error generating plots: {e}")
    
    def _display_comparison_summary(self, comparison: Dict[str, Any]):
        """
        Display a summary of the job comparison
        """
        
        print("\n" + "=" * 70)
        print("MULTI-JOB COMPARISON SUMMARY")
        print("=" * 70)
        
        summary = comparison['summary']
        print(f"Total Jobs Analyzed: {summary['total_jobs']}")
        
        print("\nJOB CLASSIFICATIONS:")
        for cls, count in summary['job_classifications'].items():
            percentage = (count / summary['total_jobs']) * 100
            print(f"  {cls}: {count} jobs ({percentage:.1f}%)")
        
        print("\nEFFICIENCY STATISTICS:")
        eff_stats = summary['efficiency_stats']
        print(f"  Mean Efficiency: {eff_stats['mean']:.1f}%")
        print(f"  Min Efficiency: {eff_stats['min']:.1f}%")
        print(f"  Max Efficiency: {eff_stats['max']:.1f}%")
        print(f"  Standard Deviation: {eff_stats['std']:.1f}%")
        
        print("\nRESOURCE USAGE STATISTICS:")
        cpu_stats = summary['resource_usage_stats']['cpu']
        io_stats = summary['resource_usage_stats']['io']
        print(f"  Average CPU Usage: {cpu_stats['mean']:.1f}% (range: {cpu_stats['min']:.1f}% - {cpu_stats['max']:.1f}%)")
        print(f"  Average I/O Usage: {io_stats['mean']:.1f}% (range: {io_stats['min']:.1f}% - {io_stats['max']:.1f}%)")
        
        patterns = comparison['patterns']
        print("\nIDENTIFIED PATTERNS:")
        print(f"  Most Common Job Type: {patterns['classification_trends']['most_common']}")
        print(f"  High-Performance Jobs: {patterns['efficiency_trends']['improving_jobs']}")
        print(f"  Poor-Performance Jobs: {patterns['efficiency_trends']['poor_jobs']}")
        print(f"  Underutilized Jobs: {patterns['resource_patterns']['underutilized_jobs']}")
        
        outliers = comparison['outliers']
        if outliers:
            print(f"\nOUTLIER JOBS ({len(outliers)} found):")
            for outlier in outliers[:5]:  # Show first 5
                print(f"  Job {outlier['job_id']} ({outlier['user']}): {', '.join(outlier['reasons'])}")
        
        recommendations = comparison['recommendations']
        print("\nKEY RECOMMENDATIONS:")
        for category, recs in recommendations.items():
            if recs:
                print(f"  {category.title()}:")
                for rec in recs[:2]:  # Show top 2 per category
                    print(f"    • [{rec['priority']}] {rec['recommendation']}")
        
        print("\n" + "=" * 70)

def main():
    """
    Main function for job comparison
    """
    
    parser = argparse.ArgumentParser(description='Multi-Job Comparison Tool')
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Compare from files
    files_parser = subparsers.add_parser('files', help='Compare jobs from JSON files')
    files_parser.add_argument('files', nargs='+', help='JSON files containing job data')
    files_parser.add_argument('--output-dir', '-o', default='.', help='Output directory')
    
    # Compare user jobs
    user_parser = subparsers.add_parser('user', help='Compare jobs for a specific user')
    user_parser.add_argument('--user', '-u', required=True, help='Username to analyze')
    user_parser.add_argument('--days', '-d', type=int, default=7, help='Days to look back')
    user_parser.add_argument('--output-dir', '-o', default='.', help='Output directory')
    
    # Common arguments
    parser.add_argument('--config', '-c', help='Configuration file')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Load configuration
    config = {}
    if args.config:
        import yaml
        with open(args.config, 'r') as f:
            config = yaml.safe_load(f)
    
    # Create comparator
    comparator = JobComparator(config)
    
    try:
        if args.command == 'files':
            result = comparator.compare_jobs_from_files(args.files, args.output_dir)
        elif args.command == 'user':
            result = comparator.compare_user_jobs(args.user, args.days, args.output_dir)
        
        if result:
            print("\nComparison completed successfully!")
        else:
            print("\nComparison failed!")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\nComparison interrupted by user")
    except Exception as e:
        print(f"\nError during comparison: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()