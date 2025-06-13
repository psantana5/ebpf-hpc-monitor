#!/bin/bash
# Simple health check for the container

# Check if Python can import required modules
python3 -c "import sys; sys.path.insert(0, '/app/scripts'); from ebpf_probes import EBPFProbeManager" 2>/dev/null || exit 1

# Check if BCC is working
python3 -c "from bcc import BPF" 2>/dev/null || exit 1

echo "Health check passed"
exit 0