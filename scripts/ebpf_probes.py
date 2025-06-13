#!/usr/bin/env python3
"""
eBPF Probes Manager

This module contains eBPF probe definitions and management for monitoring
system calls, scheduling events, and other kernel activities.

Author: Pau Santana
License: MIT
"""

import logging
import time
from collections import defaultdict
from typing import Dict, List, Optional, Set

from bcc import BPF
import psutil

logger = logging.getLogger(__name__)

class EBPFProbeManager:
    """
    Manages eBPF probes for monitoring various kernel events
    """
    
    def __init__(self, config: Dict):
        self.config = config
        self.bpf = None
        self.probes_loaded = False
        self.start_time = time.time()
        
        # Data storage
        self.syscall_counts = defaultdict(lambda: defaultdict(int))
        self.sched_events = defaultdict(list)
        self.io_events = defaultdict(list)
        self.net_events = defaultdict(list)
        
        # Filter configuration
        self.filter_type = config.get('filter', 'all')
        self.monitored_pids = set()
    
    def get_ebpf_program(self) -> str:
        """
        Generate the eBPF C program based on configuration
        """
        
        program = """
#include <uapi/linux/ptrace.h>
#include <linux/sched.h>
#include <linux/fs.h>
#include <linux/socket.h>

// Data structures for events
struct syscall_data_t {
    u32 pid;
    u32 tid;
    u32 uid;
    u64 ts;
    char comm[TASK_COMM_LEN];
    u64 syscall_id;
    u64 duration;
};

struct sched_data_t {
    u32 prev_pid;
    u32 next_pid;
    u64 ts;
    char prev_comm[TASK_COMM_LEN];
    char next_comm[TASK_COMM_LEN];
    u32 prev_state;
};

struct io_data_t {
    u32 pid;
    u32 tid;
    u64 ts;
    char comm[TASK_COMM_LEN];
    u64 bytes;
    u64 offset;
    char filename[256];
    u32 is_read;
};

struct net_data_t {
    u32 pid;
    u32 tid;
    u64 ts;
    char comm[TASK_COMM_LEN];
    u64 bytes;
    u32 is_send;
    u32 protocol;
};

// Maps for storing data
BPF_HASH(syscall_enter_time, u64, u64);
BPF_PERF_OUTPUT(syscall_events);
BPF_PERF_OUTPUT(sched_events);
BPF_PERF_OUTPUT(io_events);
BPF_PERF_OUTPUT(net_events);

// Helper function to check if PID should be monitored
static inline int should_monitor_pid(u32 pid) {
    // For now, monitor all processes
    // TODO: Add PID filtering based on Slurm jobs
    return 1;
}

// Syscall entry probe
int syscall_enter(struct pt_regs *ctx) {
    u64 pid_tgid = bpf_get_current_pid_tgid();
    u32 pid = pid_tgid >> 32;
    u32 tid = pid_tgid;
    
    if (!should_monitor_pid(pid))
        return 0;
    
    u64 ts = bpf_ktime_get_ns();
    syscall_enter_time.update(&pid_tgid, &ts);
    
    return 0;
}

// Syscall exit probe
int syscall_exit(struct pt_regs *ctx) {
    u64 pid_tgid = bpf_get_current_pid_tgid();
    u32 pid = pid_tgid >> 32;
    u32 tid = pid_tgid;
    
    if (!should_monitor_pid(pid))
        return 0;
    
    u64 *enter_ts = syscall_enter_time.lookup(&pid_tgid);
    if (!enter_ts)
        return 0;
    
    u64 exit_ts = bpf_ktime_get_ns();
    u64 duration = exit_ts - *enter_ts;
    
    struct syscall_data_t data = {};
    data.pid = pid;
    data.tid = tid;
    data.uid = bpf_get_current_uid_gid();
    data.ts = exit_ts;
    data.syscall_id = PT_REGS_ORIG_RAX(ctx);
    data.duration = duration;
    bpf_get_current_comm(&data.comm, sizeof(data.comm));
    
    syscall_events.perf_submit(ctx, &data, sizeof(data));
    syscall_enter_time.delete(&pid_tgid);
    
    return 0;
}

// Scheduler switch probe
int trace_sched_switch(struct pt_regs *ctx, struct task_struct *prev, struct task_struct *next) {
    u32 prev_pid = prev->pid;
    u32 next_pid = next->pid;
    
    if (!should_monitor_pid(prev_pid) && !should_monitor_pid(next_pid))
        return 0;
    
    struct sched_data_t data = {};
    data.prev_pid = prev_pid;
    data.next_pid = next_pid;
    data.ts = bpf_ktime_get_ns();
    data.prev_state = prev->state;
    
    bpf_probe_read_kernel_str(&data.prev_comm, sizeof(data.prev_comm), prev->comm);
    bpf_probe_read_kernel_str(&data.next_comm, sizeof(data.next_comm), next->comm);
    
    sched_events.perf_submit(ctx, &data, sizeof(data));
    
    return 0;
}

// File read probe
int trace_read_entry(struct pt_regs *ctx, struct file *file, char __user *buf, size_t count) {
    u64 pid_tgid = bpf_get_current_pid_tgid();
    u32 pid = pid_tgid >> 32;
    u32 tid = pid_tgid;
    
    if (!should_monitor_pid(pid))
        return 0;
    
    struct io_data_t data = {};
    data.pid = pid;
    data.tid = tid;
    data.ts = bpf_ktime_get_ns();
    data.bytes = count;
    data.is_read = 1;
    bpf_get_current_comm(&data.comm, sizeof(data.comm));
    
    // Try to get filename
    if (file && file->f_path.dentry) {
        bpf_probe_read_kernel_str(&data.filename, sizeof(data.filename), 
                                file->f_path.dentry->d_name.name);
    }
    
    io_events.perf_submit(ctx, &data, sizeof(data));
    
    return 0;
}

// File write probe
int trace_write_entry(struct pt_regs *ctx, struct file *file, const char __user *buf, size_t count) {
    u64 pid_tgid = bpf_get_current_pid_tgid();
    u32 pid = pid_tgid >> 32;
    u32 tid = pid_tgid;
    
    if (!should_monitor_pid(pid))
        return 0;
    
    struct io_data_t data = {};
    data.pid = pid;
    data.tid = tid;
    data.ts = bpf_ktime_get_ns();
    data.bytes = count;
    data.is_read = 0;
    bpf_get_current_comm(&data.comm, sizeof(data.comm));
    
    // Try to get filename
    if (file && file->f_path.dentry) {
        bpf_probe_read_kernel_str(&data.filename, sizeof(data.filename), 
                                file->f_path.dentry->d_name.name);
    }
    
    io_events.perf_submit(ctx, &data, sizeof(data));
    
    return 0;
}

// Network send probe
int trace_send_entry(struct pt_regs *ctx, struct socket *sock, struct msghdr *msg, size_t size) {
    u64 pid_tgid = bpf_get_current_pid_tgid();
    u32 pid = pid_tgid >> 32;
    u32 tid = pid_tgid;
    
    if (!should_monitor_pid(pid))
        return 0;
    
    struct net_data_t data = {};
    data.pid = pid;
    data.tid = tid;
    data.ts = bpf_ktime_get_ns();
    data.bytes = size;
    data.is_send = 1;
    bpf_get_current_comm(&data.comm, sizeof(data.comm));
    
    if (sock && sock->sk) {
        data.protocol = sock->sk->sk_protocol;
    }
    
    net_events.perf_submit(ctx, &data, sizeof(data));
    
    return 0;
}

// Network receive probe
int trace_recv_entry(struct pt_regs *ctx, struct socket *sock, struct msghdr *msg, size_t size, int flags) {
    u64 pid_tgid = bpf_get_current_pid_tgid();
    u32 pid = pid_tgid >> 32;
    u32 tid = pid_tgid;
    
    if (!should_monitor_pid(pid))
        return 0;
    
    struct net_data_t data = {};
    data.pid = pid;
    data.tid = tid;
    data.ts = bpf_ktime_get_ns();
    data.bytes = size;
    data.is_send = 0;
    bpf_get_current_comm(&data.comm, sizeof(data.comm));
    
    if (sock && sock->sk) {
        data.protocol = sock->sk->sk_protocol;
    }
    
    net_events.perf_submit(ctx, &data, sizeof(data));
    
    return 0;
}
"""
        
        return program
    
    def load_probes(self):
        """
        Load and attach eBPF probes
        """
        
        try:
            # Compile eBPF program
            self.bpf = BPF(text=self.get_ebpf_program())
            
            # Attach probes based on filter
            if self.filter_type in ['all', 'syscall']:
                self._attach_syscall_probes()
            
            if self.filter_type in ['all', 'sched']:
                self._attach_sched_probes()
            
            if self.filter_type in ['all', 'io']:
                self._attach_io_probes()
            
            if self.filter_type in ['all', 'net']:
                self._attach_net_probes()
            
            # Setup event handlers
            self._setup_event_handlers()
            
            self.probes_loaded = True
            logger.info(f"eBPF probes loaded successfully (filter: {self.filter_type})")
            
        except Exception as e:
            logger.error(f"Failed to load eBPF probes: {e}")
            raise
    
    def _attach_syscall_probes(self):
        """Attach syscall monitoring probes"""
        
        # Attach to syscall entry/exit
        self.bpf.attach_raw_tracepoint(tp="sys_enter", fn_name="syscall_enter")
        self.bpf.attach_raw_tracepoint(tp="sys_exit", fn_name="syscall_exit")
        
        logger.debug("Syscall probes attached")
    
    def _attach_sched_probes(self):
        """Attach scheduler monitoring probes"""
        
        # Attach to scheduler switch events
        self.bpf.attach_kprobe(event="finish_task_switch", fn_name="trace_sched_switch")
        
        logger.debug("Scheduler probes attached")
    
    def _attach_io_probes(self):
        """Attach I/O monitoring probes"""
        
        # Attach to file I/O functions
        self.bpf.attach_kprobe(event="vfs_read", fn_name="trace_read_entry")
        self.bpf.attach_kprobe(event="vfs_write", fn_name="trace_write_entry")
        
        logger.debug("I/O probes attached")
    
    def _attach_net_probes(self):
        """Attach network monitoring probes"""
        
        # Attach to network functions
        try:
            self.bpf.attach_kprobe(event="sock_sendmsg", fn_name="trace_send_entry")
            self.bpf.attach_kprobe(event="sock_recvmsg", fn_name="trace_recv_entry")
        except Exception as e:
            logger.warning(f"Some network probes failed to attach: {e}")
        
        logger.debug("Network probes attached")
    
    def _setup_event_handlers(self):
        """Setup event handlers for perf buffers"""
        
        # Syscall events
        if self.filter_type in ['all', 'syscall']:
            self.bpf["syscall_events"].open_perf_buffer(self._handle_syscall_event)
        
        # Scheduler events
        if self.filter_type in ['all', 'sched']:
            self.bpf["sched_events"].open_perf_buffer(self._handle_sched_event)
        
        # I/O events
        if self.filter_type in ['all', 'io']:
            self.bpf["io_events"].open_perf_buffer(self._handle_io_event)
        
        # Network events
        if self.filter_type in ['all', 'net']:
            self.bpf["net_events"].open_perf_buffer(self._handle_net_event)
    
    def _handle_syscall_event(self, cpu, data, size):
        """Handle syscall events"""
        
        event = self.bpf["syscall_events"].event(data)
        
        pid = event.pid
        syscall_id = event.syscall_id
        duration = event.duration
        
        self.syscall_counts[pid][syscall_id] += 1
        
        # Store detailed event data
        if not hasattr(self, 'detailed_syscalls'):
            self.detailed_syscalls = defaultdict(list)
        
        self.detailed_syscalls[pid].append({
            'timestamp': event.ts,
            'syscall_id': syscall_id,
            'duration': duration,
            'comm': event.comm.decode('utf-8', 'replace')
        })
    
    def _handle_sched_event(self, cpu, data, size):
        """Handle scheduler events"""
        
        event = self.bpf["sched_events"].event(data)
        
        sched_data = {
            'timestamp': event.ts,
            'prev_pid': event.prev_pid,
            'next_pid': event.next_pid,
            'prev_comm': event.prev_comm.decode('utf-8', 'replace'),
            'next_comm': event.next_comm.decode('utf-8', 'replace'),
            'prev_state': event.prev_state
        }
        
        self.sched_events[event.prev_pid].append(sched_data)
        self.sched_events[event.next_pid].append(sched_data)
    
    def _handle_io_event(self, cpu, data, size):
        """Handle I/O events"""
        
        event = self.bpf["io_events"].event(data)
        
        io_data = {
            'timestamp': event.ts,
            'pid': event.pid,
            'bytes': event.bytes,
            'is_read': bool(event.is_read),
            'filename': event.filename.decode('utf-8', 'replace'),
            'comm': event.comm.decode('utf-8', 'replace')
        }
        
        self.io_events[event.pid].append(io_data)
    
    def _handle_net_event(self, cpu, data, size):
        """Handle network events"""
        
        event = self.bpf["net_events"].event(data)
        
        net_data = {
            'timestamp': event.ts,
            'pid': event.pid,
            'bytes': event.bytes,
            'is_send': bool(event.is_send),
            'protocol': event.protocol,
            'comm': event.comm.decode('utf-8', 'replace')
        }
        
        self.net_events[event.pid].append(net_data)
    
    def poll_events(self, timeout_ms: int = 100):
        """Poll for new events"""
        
        if not self.probes_loaded:
            return
        
        try:
            self.bpf.perf_buffer_poll(timeout=timeout_ms)
        except KeyboardInterrupt:
            pass
    
    def get_current_data(self) -> Dict:
        """Get current monitoring data"""
        
        # Poll for recent events
        self.poll_events()
        
        return {
            'syscall_counts': dict(self.syscall_counts),
            'sched_events': dict(self.sched_events),
            'io_events': dict(self.io_events),
            'net_events': dict(self.net_events),
            'detailed_syscalls': getattr(self, 'detailed_syscalls', {})
        }
    
    def set_monitored_pids(self, pids: Set[int]):
        """Set PIDs to monitor"""
        
        self.monitored_pids = pids
        logger.debug(f"Monitoring {len(pids)} PIDs")
    
    def cleanup(self):
        """Cleanup eBPF resources"""
        
        if self.bpf:
            try:
                # Detach all probes
                self.bpf.cleanup()
                logger.info("eBPF probes cleaned up")
            except Exception as e:
                logger.error(f"Error during cleanup: {e}")
        
        self.probes_loaded = False
    
    def get_stats(self) -> Dict:
        """Get monitoring statistics"""
        
        total_syscalls = sum(sum(counts.values()) for counts in self.syscall_counts.values())
        total_sched_events = sum(len(events) for events in self.sched_events.values())
        total_io_events = sum(len(events) for events in self.io_events.values())
        total_net_events = sum(len(events) for events in self.net_events.values())
        
        return {
            'uptime_seconds': time.time() - self.start_time,
            'total_syscalls': total_syscalls,
            'total_sched_events': total_sched_events,
            'total_io_events': total_io_events,
            'total_net_events': total_net_events,
            'monitored_pids': len(self.monitored_pids),
            'probes_loaded': self.probes_loaded
        }