#!/usr/bin/env python3
"""
Setup script for eBPF HPC Monitor
"""

from setuptools import setup, find_packages
import os

# Read the contents of README file
this_directory = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(this_directory, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

# Read requirements
with open('requirements.txt') as f:
    requirements = [line.strip() for line in f if line.strip() and not line.startswith('#')]

setup(
    name="ebpf-hpc-monitor",
    version="1.0.0",
    author="Pau Santana",
    author_email="pausantanapi2@gmail.com",
    description="eBPF-based monitoring system for HPC environments and Slurm jobs",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/psantana5/ebpf-hpc-monitor",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: System Administrators",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: MIT License",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: System :: Monitoring",
        "Topic :: System :: Systems Administration",
        "Topic :: Scientific/Engineering",
    ],
    python_requires=">=3.7",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
            "black>=22.0.0",
            "flake8>=5.0.0",
            "mypy>=0.991",
        ],
        "docs": [
            "sphinx>=5.0.0",
            "sphinx-rtd-theme>=1.0.0",
        ],
        "prometheus": [
            "prometheus-client>=0.14.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "hpc-monitor=scripts.hpc_monitor:main",
            "hpc-analyzer=scripts.data_analyzer:main",
        ],
    },
    include_package_data=True,
    package_data={
        "": ["*.yaml", "*.yml", "*.json", "*.md"],
    },
    keywords="ebpf hpc monitoring slurm performance profiling",
    project_urls={
        "Bug Reports": "https://github.com/psantana5/ebpf-hpc-monitor/issues",
        "Source": "https://github.com/psantana5/ebpf-hpc-monitor",
        "Documentation": "https://ebpf-hpc-monitor.readthedocs.io/",
    },
)