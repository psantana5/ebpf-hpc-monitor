#!/usr/bin/env python3
"""
Basic Functionality Tests for eBPF HPC Monitor

This module contains basic tests to verify the core functionality
of the HPC monitoring system.

Author: Pau Santana
License: MIT
"""

import unittest
import sys
import os
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Add the scripts directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent / 'scripts'))

try:
    from data_analyzer import JobAnalyzer, JobClassifier
    from slurm_integration import SlurmIntegration
except ImportError as e:
    print(f"Warning: Could not import modules: {e}")
    print("Some tests may be skipped")

class TestJobAnalyzer(unittest.TestCase):
    """
    Test cases for JobAnalyzer class
    """
    
    def setUp(self):
        """Set up test fixtures"""
        self.analyzer = JobAnalyzer()
        
        # Sample event data for testing
        self.sample_events = [
            {
                'type': 'syscall',
                'name': 'read',
                'pid': 1234,
                'duration': 5000,  # nanoseconds
                'timestamp': 1642248000000000000
            },
            {
                'type': 'syscall',
                'name': 'write',
                'pid': 1234,
                'duration': 3000,
                'timestamp': 1642248001000000000
            },
            {
                'type': 'sched_switch',
                'pid': 1234,
                'prev_state': 'R',
                'next_pid': 5678,
                'timestamp': 1642248002000000000
            },
            {
                'type': 'io_event',
                'operation': 'read',
                'pid': 1234,
                'bytes': 4096,
                'timestamp': 1642248003000000000
            }
        ]
    
    def test_aggregate_metrics_basic(self):
        """Test basic metrics aggregation"""
        pids = [1234]
        metrics = self.analyzer.aggregate_metrics(self.sample_events, pids)
        
        # Check that metrics are returned
        self.assertIsInstance(metrics, dict)
        self.assertIn('total_syscalls', metrics)
        self.assertIn('context_switches', metrics)
        self.assertIn('total_io_bytes', metrics)
        
        # Check specific values
        self.assertEqual(metrics['total_syscalls'], 2)
        self.assertEqual(metrics['context_switches'], 1)
        self.assertEqual(metrics['total_io_bytes'], 4096)
    
    def test_aggregate_metrics_empty_events(self):
        """Test metrics aggregation with empty events"""
        pids = [1234]
        metrics = self.analyzer.aggregate_metrics([], pids)
        
        # Should return default values
        self.assertEqual(metrics['total_syscalls'], 0)
        self.assertEqual(metrics['context_switches'], 0)
        self.assertEqual(metrics['total_io_bytes'], 0)
    
    def test_aggregate_metrics_no_pids(self):
        """Test metrics aggregation with no PIDs"""
        metrics = self.analyzer.aggregate_metrics(self.sample_events, [])
        
        # Should still process events but may have different results
        self.assertIsInstance(metrics, dict)
    
    def test_calculate_percentages(self):
        """Test percentage calculations"""
        # Mock some timing data
        with patch.object(self.analyzer, '_calculate_time_percentages') as mock_calc:
            mock_calc.return_value = {
                'cpu_percent': 75.0,
                'io_percent': 15.0,
                'wait_percent': 10.0
            }
            
            pids = [1234]
            metrics = self.analyzer.aggregate_metrics(self.sample_events, pids)
            
            # Check that percentages are included
            self.assertIn('cpu_percent', metrics)
            self.assertIn('io_percent', metrics)
            self.assertIn('wait_percent', metrics)

class TestJobClassifier(unittest.TestCase):
    """
    Test cases for JobClassifier class
    """
    
    def setUp(self):
        """Set up test fixtures"""
        self.classifier = JobClassifier()
    
    def test_classify_cpu_bound_job(self):
        """Test classification of CPU-bound job"""
        metrics = {
            'cpu_percent': 85.0,
            'io_percent': 10.0,
            'wait_percent': 5.0,
            'context_switches': 1000,
            'total_syscalls': 5000
        }
        
        classification = self.classifier.classify_job(metrics)
        self.assertEqual(classification, 'CPU-bound')
    
    def test_classify_io_bound_job(self):
        """Test classification of I/O-bound job"""
        metrics = {
            'cpu_percent': 25.0,
            'io_percent': 60.0,
            'wait_percent': 15.0,
            'context_switches': 8000,
            'total_syscalls': 15000
        }
        
        classification = self.classifier.classify_job(metrics)
        self.assertEqual(classification, 'I/O-bound')
    
    def test_classify_idle_heavy_job(self):
        """Test classification of idle-heavy job"""
        metrics = {
            'cpu_percent': 15.0,
            'io_percent': 10.0,
            'wait_percent': 75.0,
            'context_switches': 500,
            'total_syscalls': 1000
        }
        
        classification = self.classifier.classify_job(metrics)
        self.assertEqual(classification, 'Idle-heavy')
    
    def test_classify_balanced_job(self):
        """Test classification of balanced job"""
        metrics = {
            'cpu_percent': 45.0,
            'io_percent': 35.0,
            'wait_percent': 20.0,
            'context_switches': 3000,
            'total_syscalls': 8000
        }
        
        classification = self.classifier.classify_job(metrics)
        self.assertEqual(classification, 'Balanced')
    
    def test_efficiency_score_calculation(self):
        """Test efficiency score calculation"""
        # High efficiency job
        high_eff_metrics = {
            'cpu_percent': 80.0,
            'io_percent': 15.0,
            'wait_percent': 5.0,
            'context_switches': 1000,
            'total_syscalls': 5000
        }
        
        high_score = self.classifier.get_efficiency_score(high_eff_metrics)
        self.assertGreater(high_score, 70)
        
        # Low efficiency job
        low_eff_metrics = {
            'cpu_percent': 10.0,
            'io_percent': 5.0,
            'wait_percent': 85.0,
            'context_switches': 100,
            'total_syscalls': 200
        }
        
        low_score = self.classifier.get_efficiency_score(low_eff_metrics)
        self.assertLess(low_score, 30)
    
    def test_get_recommendations(self):
        """Test recommendation generation"""
        metrics = {
            'cpu_percent': 25.0,
            'io_percent': 60.0,
            'wait_percent': 15.0,
            'context_switches': 8000,
            'total_syscalls': 15000
        }
        
        classification = 'I/O-bound'
        recommendations = self.classifier.get_recommendations(metrics, classification)
        
        self.assertIsInstance(recommendations, list)
        self.assertGreater(len(recommendations), 0)
        
        # Should contain I/O-related recommendations
        rec_text = ' '.join(recommendations).lower()
        self.assertTrue(any(keyword in rec_text for keyword in ['i/o', 'io', 'storage', 'disk']))

class TestSlurmIntegration(unittest.TestCase):
    """
    Test cases for SlurmIntegration class
    """
    
    def setUp(self):
        """Set up test fixtures"""
        self.config = {
            'fallback_mode': True,  # Enable fallback for testing
            'commands': {
                'squeue': 'squeue',
                'sacct': 'sacct',
                'sstat': 'sstat'
            }
        }
        self.slurm = SlurmIntegration(self.config)
    
    @patch('subprocess.run')
    def test_check_slurm_availability_success(self, mock_run):
        """Test successful Slurm availability check"""
        mock_run.return_value = Mock(returncode=0, stdout="SLURM 22.05.3")
        
        available = self.slurm.check_slurm_availability()
        self.assertTrue(available)
    
    @patch('subprocess.run')
    def test_check_slurm_availability_failure(self, mock_run):
        """Test failed Slurm availability check"""
        mock_run.side_effect = FileNotFoundError()
        
        available = self.slurm.check_slurm_availability()
        self.assertFalse(available)
    
    @patch('subprocess.run')
    def test_get_running_jobs_success(self, mock_run):
        """Test getting running jobs successfully"""
        mock_output = """JOBID|USER|NAME|PARTITION|STATE|NODES|CPUS
12345|user1|test_job|compute|RUNNING|node01|16
12346|user2|another_job|compute|RUNNING|node02|8"""
        
        mock_run.return_value = Mock(returncode=0, stdout=mock_output)
        
        jobs = self.slurm.get_running_jobs()
        
        self.assertEqual(len(jobs), 2)
        self.assertEqual(jobs[0]['job_id'], '12345')
        self.assertEqual(jobs[0]['user'], 'user1')
        self.assertEqual(jobs[0]['state'], 'RUNNING')
    
    @patch('subprocess.run')
    def test_get_job_info_success(self, mock_run):
        """Test getting job info successfully"""
        mock_output = """JOBID|USER|NAME|PARTITION|STATE|NODES|CPUS
12345|user1|test_job|compute|RUNNING|node01|16"""
        
        mock_run.return_value = Mock(returncode=0, stdout=mock_output)
        
        job_info = self.slurm.get_job_info('12345')
        
        self.assertIsNotNone(job_info)
        self.assertEqual(len(job_info), 1)
        self.assertEqual(job_info[0]['job_id'], '12345')
    
    def test_fallback_mode_process_inspection(self):
        """Test fallback mode using process inspection"""
        # This test uses the fallback mode which doesn't require Slurm
        with patch('psutil.process_iter') as mock_process_iter:
            # Mock some processes
            mock_proc1 = Mock()
            mock_proc1.info = {
                'pid': 1234,
                'ppid': 1,
                'name': 'test_process',
                'username': 'testuser',
                'cmdline': ['./test_program', '--arg1']
            }
            
            mock_proc2 = Mock()
            mock_proc2.info = {
                'pid': 5678,
                'ppid': 1234,
                'name': 'child_process',
                'username': 'testuser',
                'cmdline': ['./child_program']
            }
            
            mock_process_iter.return_value = [mock_proc1, mock_proc2]
            
            jobs = self.slurm._fallback_get_jobs()
            
            # Should find at least one job group
            self.assertGreater(len(jobs), 0)

class TestConfigurationLoading(unittest.TestCase):
    """
    Test configuration loading and validation
    """
    
    def test_load_sample_config(self):
        """Test loading the sample configuration file"""
        config_path = Path(__file__).parent.parent / 'config' / 'monitor_config.yaml'
        
        if config_path.exists():
            import yaml
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
            
            # Check that main sections exist
            self.assertIn('ebpf', config)
            self.assertIn('slurm', config)
            self.assertIn('classification', config)
            self.assertIn('output', config)
            
            # Check eBPF configuration
            ebpf_config = config['ebpf']
            self.assertIn('enabled', ebpf_config)
            self.assertIn('probes', ebpf_config)
            
            # Check Slurm configuration
            slurm_config = config['slurm']
            self.assertIn('enabled', slurm_config)
            self.assertIn('commands', slurm_config)
        else:
            self.skipTest("Configuration file not found")
    
    def test_load_test_config(self):
        """Test loading the test configuration file"""
        config_path = Path(__file__).parent.parent / 'data' / 'test_data' / 'test_config.yaml'
        
        if config_path.exists():
            import yaml
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
            
            # Check test-specific sections
            self.assertIn('test_settings', config)
            self.assertIn('development', config)
            
            # Check that test mode is enabled
            test_settings = config['test_settings']
            self.assertIn('mock_data', test_settings)
        else:
            self.skipTest("Test configuration file not found")

class TestSampleDataLoading(unittest.TestCase):
    """
    Test loading and validation of sample data
    """
    
    def test_load_sample_job_data(self):
        """Test loading sample job data"""
        sample_path = Path(__file__).parent.parent / 'data' / 'sample_outputs' / 'sample_job_data.json'
        
        if sample_path.exists():
            with open(sample_path, 'r') as f:
                data = json.load(f)
            
            # Check main structure
            self.assertIn('monitoring_session', data)
            self.assertIn('jobs', data)
            self.assertIn('summary', data)
            
            # Check jobs data
            jobs = data['jobs']
            self.assertGreater(len(jobs), 0)
            
            for job in jobs:
                self.assertIn('job_id', job)
                self.assertIn('user', job)
                self.assertIn('metrics', job)
                self.assertIn('classification', job)
                
                # Check metrics structure
                metrics = job['metrics']
                required_metrics = [
                    'cpu_percent', 'io_percent', 'wait_percent',
                    'total_syscalls', 'context_switches'
                ]
                for metric in required_metrics:
                    self.assertIn(metric, metrics)
                
                # Check classification structure
                classification = job['classification']
                self.assertIn('type', classification)
                self.assertIn('efficiency_score', classification)
        else:
            self.skipTest("Sample data file not found")

class TestUtilityFunctions(unittest.TestCase):
    """
    Test utility functions and helpers
    """
    
    def test_format_bytes(self):
        """Test byte formatting utility"""
        # This would test a utility function if it exists
        # For now, we'll test the concept
        
        def format_bytes(bytes_val):
            """Simple byte formatter for testing"""
            for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
                if bytes_val < 1024.0:
                    return f"{bytes_val:.1f} {unit}"
                bytes_val /= 1024.0
            return f"{bytes_val:.1f} PB"
        
        self.assertEqual(format_bytes(1024), "1.0 KB")
        self.assertEqual(format_bytes(1048576), "1.0 MB")
        self.assertEqual(format_bytes(1073741824), "1.0 GB")
    
    def test_validate_job_id(self):
        """Test job ID validation"""
        def validate_job_id(job_id):
            """Simple job ID validator for testing"""
            if not job_id:
                return False
            if not isinstance(job_id, str):
                return False
            if not job_id.isdigit():
                return False
            return True
        
        self.assertTrue(validate_job_id("12345"))
        self.assertFalse(validate_job_id(""))
        self.assertFalse(validate_job_id("abc"))
        self.assertFalse(validate_job_id(None))

def create_test_suite():
    """
    Create a test suite with all test cases
    """
    suite = unittest.TestSuite()
    
    # Add test classes
    test_classes = [
        TestJobAnalyzer,
        TestJobClassifier,
        TestSlurmIntegration,
        TestConfigurationLoading,
        TestSampleDataLoading,
        TestUtilityFunctions
    ]
    
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        suite.addTests(tests)
    
    return suite

def main():
    """
    Main function to run tests
    """
    print("Running eBPF HPC Monitor Basic Functionality Tests")
    print("=" * 60)
    
    # Check if we're running as root (required for some eBPF operations)
    if os.geteuid() == 0:
        print("Running as root - eBPF tests enabled")
    else:
        print("Not running as root - some eBPF tests may be skipped")
    
    # Create and run test suite
    suite = create_test_suite()
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "=" * 60)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Skipped: {len(result.skipped)}")
    
    if result.failures:
        print("\nFailures:")
        for test, traceback in result.failures:
            print(f"  - {test}: {traceback.split('\n')[-2]}")
    
    if result.errors:
        print("\nErrors:")
        for test, traceback in result.errors:
            print(f"  - {test}: {traceback.split('\n')[-2]}")
    
    # Return exit code
    return 0 if result.wasSuccessful() else 1

if __name__ == '__main__':
    sys.exit(main())