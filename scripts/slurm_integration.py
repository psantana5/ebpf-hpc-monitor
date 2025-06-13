#!/usr/bin/env python3
"""
Slurm Integration Module

This module provides integration with Slurm workload manager to map
processes to jobs and gather job information.

Author: Pau Santana
License: MIT
"""

import logging
import os
import re
import subprocess
import time
from pathlib import Path
from typing import Dict, List, Optional, Set

import psutil

logger = logging.getLogger(__name__)

class SlurmIntegration:
    """
    Handles integration with Slurm workload manager
    """
    
    def __init__(self, config: Dict):
        self.config = config
        self.slurm_available = self._check_slurm_availability()
        self.job_cache = {}
        self.pid_to_job_cache = {}
        self.cache_timeout = config.get('cache_timeout', 30)  # 30 seconds
        self.last_cache_update = 0
        
        if not self.slurm_available:
            logger.warning("Slurm not available, using process-based monitoring")
    
    def _check_slurm_availability(self) -> bool:
        """Check if Slurm commands are available"""
        
        try:
            subprocess.run(['squeue', '--version'], 
                         capture_output=True, check=True, timeout=5)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
            return False
    
    def get_running_jobs(self) -> List[Dict]:
        """Get list of currently running Slurm jobs"""
        
        if not self.slurm_available:
            return self._get_fallback_jobs()
        
        try:
            # Use squeue to get running jobs
            cmd = [
                'squeue',
                '--states=RUNNING',
                '--format=%i,%j,%u,%t,%M,%N,%C,%m',
                '--noheader'
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            if result.returncode != 0:
                logger.error(f"squeue failed: {result.stderr}")
                return self._get_fallback_jobs()
            
            jobs = []
            for line in result.stdout.strip().split('\n'):
                if not line:
                    continue
                
                parts = line.split(',')
                if len(parts) >= 8:
                    job = {
                        'job_id': parts[0],
                        'name': parts[1],
                        'user': parts[2],
                        'state': parts[3],
                        'time': parts[4],
                        'nodes': parts[5].split('+') if parts[5] else [],
                        'cpus': parts[6],
                        'memory': parts[7],
                        'partition': self._get_job_partition(parts[0])
                    }
                    jobs.append(job)
            
            logger.debug(f"Found {len(jobs)} running Slurm jobs")
            return jobs
            
        except subprocess.TimeoutExpired:
            logger.error("squeue command timed out")
            return self._get_fallback_jobs()
        except Exception as e:
            logger.error(f"Error getting Slurm jobs: {e}")
            return self._get_fallback_jobs()
    
    def get_job_info(self, job_id: str) -> List[Dict]:
        """Get information for a specific job"""
        
        if not self.slurm_available:
            return self._get_fallback_jobs()
        
        try:
            cmd = [
                'squeue',
                '--job', job_id,
                '--format=%i,%j,%u,%t,%M,%N,%C,%m,%P',
                '--noheader'
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            if result.returncode != 0:
                logger.error(f"squeue failed for job {job_id}: {result.stderr}")
                return []
            
            jobs = []
            for line in result.stdout.strip().split('\n'):
                if not line:
                    continue
                
                parts = line.split(',')
                if len(parts) >= 9:
                    job = {
                        'job_id': parts[0],
                        'name': parts[1],
                        'user': parts[2],
                        'state': parts[3],
                        'time': parts[4],
                        'nodes': parts[5].split('+') if parts[5] else [],
                        'cpus': parts[6],
                        'memory': parts[7],
                        'partition': parts[8]
                    }
                    jobs.append(job)
            
            return jobs
            
        except Exception as e:
            logger.error(f"Error getting job info for {job_id}: {e}")
            return []
    
    def get_user_jobs(self, username: str) -> List[Dict]:
        """Get jobs for a specific user"""
        
        if not self.slurm_available:
            return self._get_fallback_jobs(user_filter=username)
        
        try:
            cmd = [
                'squeue',
                '--user', username,
                '--states=RUNNING',
                '--format=%i,%j,%u,%t,%M,%N,%C,%m,%P',
                '--noheader'
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            if result.returncode != 0:
                logger.error(f"squeue failed for user {username}: {result.stderr}")
                return []
            
            jobs = []
            for line in result.stdout.strip().split('\n'):
                if not line:
                    continue
                
                parts = line.split(',')
                if len(parts) >= 9:
                    job = {
                        'job_id': parts[0],
                        'name': parts[1],
                        'user': parts[2],
                        'state': parts[3],
                        'time': parts[4],
                        'nodes': parts[5].split('+') if parts[5] else [],
                        'cpus': parts[6],
                        'memory': parts[7],
                        'partition': parts[8]
                    }
                    jobs.append(job)
            
            return jobs
            
        except Exception as e:
            logger.error(f"Error getting jobs for user {username}: {e}")
            return []
    
    def get_job_pids(self, job_id: str) -> Set[int]:
        """Get PIDs associated with a Slurm job"""
        
        # Check cache first
        current_time = time.time()
        if (job_id in self.job_cache and 
            current_time - self.last_cache_update < self.cache_timeout):
            return self.job_cache[job_id]
        
        pids = set()
        
        if self.slurm_available:
            pids = self._get_slurm_job_pids(job_id)
        
        if not pids:
            # Fallback: try to find PIDs through process inspection
            pids = self._get_pids_by_process_inspection(job_id)
        
        # Update cache
        self.job_cache[job_id] = pids
        self.last_cache_update = current_time
        
        return pids
    
    def _get_slurm_job_pids(self, job_id: str) -> Set[int]:
        """Get PIDs using Slurm-specific methods"""
        
        pids = set()
        
        # Method 1: Use sstat to get process information
        try:
            cmd = ['sstat', '--job', job_id, '--format=JobID,AvePID', '--parsable2', '--noheader']
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                for line in result.stdout.strip().split('\n'):
                    if '|' in line:
                        parts = line.split('|')
                        if len(parts) >= 2 and parts[1].isdigit():
                            pids.add(int(parts[1]))
        except Exception as e:
            logger.debug(f"sstat method failed: {e}")
        
        # Method 2: Check cgroup information
        if not pids:
            pids.update(self._get_pids_from_cgroup(job_id))
        
        # Method 3: Check /proc for Slurm environment variables
        if not pids:
            pids.update(self._get_pids_from_proc_env(job_id))
        
        return pids
    
    def _get_pids_from_cgroup(self, job_id: str) -> Set[int]:
        """Get PIDs from cgroup information"""
        
        pids = set()
        
        # Common cgroup paths for Slurm
        cgroup_paths = [
            f'/sys/fs/cgroup/systemd/slurm/uid_*/job_{job_id}',
            f'/sys/fs/cgroup/slurm/uid_*/job_{job_id}',
            f'/sys/fs/cgroup/memory/slurm/uid_*/job_{job_id}',
            f'/sys/fs/cgroup/cpuset/slurm/uid_*/job_{job_id}'
        ]
        
        for pattern in cgroup_paths:
            try:
                import glob
                for cgroup_dir in glob.glob(pattern):
                    cgroup_procs = Path(cgroup_dir) / 'cgroup.procs'
                    if cgroup_procs.exists():
                        with open(cgroup_procs, 'r') as f:
                            for line in f:
                                pid = line.strip()
                                if pid.isdigit():
                                    pids.add(int(pid))
            except Exception as e:
                logger.debug(f"Cgroup method failed for {pattern}: {e}")
        
        return pids
    
    def _get_pids_from_proc_env(self, job_id: str) -> Set[int]:
        """Get PIDs by checking /proc/*/environ for Slurm variables"""
        
        pids = set()
        
        try:
            for proc in psutil.process_iter(['pid', 'environ']):
                try:
                    environ = proc.info['environ'] or {}
                    
                    # Check for Slurm environment variables
                    slurm_job_id = environ.get('SLURM_JOB_ID', '')
                    slurm_jobid = environ.get('SLURM_JOBID', '')
                    
                    if slurm_job_id == job_id or slurm_jobid == job_id:
                        pids.add(proc.info['pid'])
                        
                        # Also add child processes
                        try:
                            for child in psutil.Process(proc.info['pid']).children(recursive=True):
                                pids.add(child.pid)
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            pass
                            
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue
                    
        except Exception as e:
            logger.debug(f"Proc environ method failed: {e}")
        
        return pids
    
    def _get_pids_by_process_inspection(self, job_id: str) -> Set[int]:
        """Fallback method to find PIDs by process inspection"""
        
        pids = set()
        
        try:
            # Look for processes with job_id in command line or environment
            for proc in psutil.process_iter(['pid', 'cmdline', 'environ', 'name']):
                try:
                    # Check command line
                    cmdline = ' '.join(proc.info['cmdline'] or [])
                    if job_id in cmdline:
                        pids.add(proc.info['pid'])
                        continue
                    
                    # Check environment variables
                    environ = proc.info['environ'] or {}
                    for key, value in environ.items():
                        if 'SLURM' in key and job_id in str(value):
                            pids.add(proc.info['pid'])
                            break
                            
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue
                    
        except Exception as e:
            logger.debug(f"Process inspection failed: {e}")
        
        return pids
    
    def _get_job_partition(self, job_id: str) -> str:
        """Get partition for a job"""
        
        try:
            cmd = ['squeue', '--job', job_id, '--format=%P', '--noheader']
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            
            if result.returncode == 0:
                return result.stdout.strip()
                
        except Exception:
            pass
        
        return 'unknown'
    
    def _get_fallback_jobs(self, user_filter: Optional[str] = None) -> List[Dict]:
        """Fallback method when Slurm is not available"""
        
        jobs = []
        
        try:
            # Create pseudo-jobs based on running processes
            job_counter = 1
            
            for proc in psutil.process_iter(['pid', 'username', 'name', 'cmdline', 'create_time']):
                try:
                    # Filter by user if specified
                    if user_filter and proc.info['username'] != user_filter:
                        continue
                    
                    # Skip system processes
                    if proc.info['username'] in ['root', 'daemon', 'nobody']:
                        continue
                    
                    # Create a pseudo-job for each user process
                    job = {
                        'job_id': f'proc_{job_counter}',
                        'name': proc.info['name'],
                        'user': proc.info['username'],
                        'state': 'RUNNING',
                        'time': str(int(time.time() - proc.info['create_time'])),
                        'nodes': [os.uname().nodename],
                        'cpus': '1',
                        'memory': 'unknown',
                        'partition': 'fallback'
                    }
                    
                    jobs.append(job)
                    job_counter += 1
                    
                    # Limit to avoid too many pseudo-jobs
                    if len(jobs) >= 50:
                        break
                        
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue
                    
        except Exception as e:
            logger.error(f"Fallback job detection failed: {e}")
        
        return jobs
    
    def get_job_accounting_info(self, job_id: str) -> Dict:
        """Get accounting information for a completed job"""
        
        if not self.slurm_available:
            return {}
        
        try:
            cmd = [
                'sacct',
                '--job', job_id,
                '--format=JobID,JobName,User,Partition,State,ExitCode,Start,End,Elapsed,CPUTime,MaxRSS,MaxVMSize',
                '--parsable2',
                '--noheader'
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            if result.returncode != 0:
                logger.error(f"sacct failed for job {job_id}: {result.stderr}")
                return {}
            
            lines = result.stdout.strip().split('\n')
            if not lines or not lines[0]:
                return {}
            
            # Parse the first line (main job info)
            parts = lines[0].split('|')
            if len(parts) >= 12:
                return {
                    'job_id': parts[0],
                    'job_name': parts[1],
                    'user': parts[2],
                    'partition': parts[3],
                    'state': parts[4],
                    'exit_code': parts[5],
                    'start_time': parts[6],
                    'end_time': parts[7],
                    'elapsed': parts[8],
                    'cpu_time': parts[9],
                    'max_rss': parts[10],
                    'max_vmsize': parts[11]
                }
                
        except Exception as e:
            logger.error(f"Error getting accounting info for job {job_id}: {e}")
        
        return {}
    
    def is_job_running(self, job_id: str) -> bool:
        """Check if a job is currently running"""
        
        jobs = self.get_job_info(job_id)
        return any(job['state'] == 'RUNNING' for job in jobs)
    
    def get_node_jobs(self, node_name: str) -> List[Dict]:
        """Get jobs running on a specific node"""
        
        if not self.slurm_available:
            return []
        
        try:
            cmd = [
                'squeue',
                '--nodelist', node_name,
                '--states=RUNNING',
                '--format=%i,%j,%u,%t,%M,%N,%C,%m,%P',
                '--noheader'
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            if result.returncode != 0:
                logger.error(f"squeue failed for node {node_name}: {result.stderr}")
                return []
            
            jobs = []
            for line in result.stdout.strip().split('\n'):
                if not line:
                    continue
                
                parts = line.split(',')
                if len(parts) >= 9:
                    job = {
                        'job_id': parts[0],
                        'name': parts[1],
                        'user': parts[2],
                        'state': parts[3],
                        'time': parts[4],
                        'nodes': parts[5].split('+') if parts[5] else [],
                        'cpus': parts[6],
                        'memory': parts[7],
                        'partition': parts[8]
                    }
                    jobs.append(job)
            
            return jobs
            
        except Exception as e:
            logger.error(f"Error getting jobs for node {node_name}: {e}")
            return []
    
    def clear_cache(self):
        """Clear the PID cache"""
        
        self.job_cache.clear()
        self.pid_to_job_cache.clear()
        self.last_cache_update = 0
        logger.debug("Slurm cache cleared")