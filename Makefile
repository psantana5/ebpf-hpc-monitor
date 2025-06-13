# Makefile for eBPF HPC Monitor
# Provides convenient commands for development, testing, and deployment

.PHONY: help install install-dev test test-coverage lint format clean build docker run-examples docs setup-dev check-deps

# Default target
help:
	@echo "eBPF HPC Monitor - Available Commands:"
	@echo ""
	@echo "Setup and Installation:"
	@echo "  install          Install the package and dependencies"
	@echo "  install-dev      Install development dependencies"
	@echo "  setup-dev        Complete development environment setup"
	@echo "  check-deps       Check system dependencies"
	@echo ""
	@echo "Development:"
	@echo "  test             Run basic tests"
	@echo "  test-coverage    Run tests with coverage report"
	@echo "  lint             Run code linting (flake8, mypy)"
	@echo "  format           Format code with black"
	@echo "  clean            Clean build artifacts and cache"
	@echo ""
	@echo "Docker:"
	@echo "  docker-build     Build Docker image"
	@echo "  docker-run       Run Docker container interactively"
	@echo "  docker-test      Test Docker container"
	@echo ""
	@echo "Examples and Testing:"
	@echo "  run-examples     Run example scripts (requires root)"
	@echo "  monitor-user     Monitor current user (requires root)"
	@echo "  demo             Run demonstration"
	@echo ""
	@echo "Documentation:"
	@echo "  docs             Generate documentation"
	@echo "  docs-serve       Serve documentation locally"
	@echo ""
	@echo "Maintenance:"
	@echo "  build            Build distribution packages"
	@echo "  upload           Upload to PyPI (requires credentials)"
	@echo "  security-check   Run security checks"

# Installation targets
install:
	@echo "Installing eBPF HPC Monitor..."
	pip3 install -r requirements.txt
	pip3 install -e .
	@echo "Installation complete!"

install-dev:
	@echo "Installing development dependencies..."
	pip3 install -r requirements.txt
	pip3 install -e ".[dev,docs,prometheus]"
	@echo "Development dependencies installed!"

setup-dev: install-dev
	@echo "Setting up development environment..."
	# Create necessary directories
	mkdir -p logs output data/monitoring_sessions
	# Copy configuration templates
	cp config/monitor_config.yaml config/dev_config.yaml 2>/dev/null || true
	# Set up pre-commit hooks if available
	which pre-commit >/dev/null && pre-commit install || echo "pre-commit not available"
	@echo "Development environment ready!"

check-deps:
	@echo "Checking system dependencies..."
	@echo "Python version:"
	@python3 --version
	@echo "Checking BCC availability:"
	@python3 -c "from bcc import BPF; print('BCC: OK')" 2>/dev/null || echo "BCC: NOT AVAILABLE"
	@echo "Checking root privileges:"
	@[ "$$(id -u)" = "0" ] && echo "Root: OK" || echo "Root: NOT AVAILABLE (some features require root)"
	@echo "Checking Slurm availability:"
	@which squeue >/dev/null 2>&1 && echo "Slurm: OK" || echo "Slurm: NOT AVAILABLE (fallback mode will be used)"
	@echo "Checking kernel headers:"
	@[ -d "/lib/modules/$$(uname -r)" ] && echo "Kernel headers: OK" || echo "Kernel headers: NOT AVAILABLE"

# Testing targets
test:
	@echo "Running basic tests..."
	python3 -m pytest tests/ -v

test-coverage:
	@echo "Running tests with coverage..."
	python3 -m pytest tests/ --cov=scripts --cov-report=html --cov-report=term
	@echo "Coverage report generated in htmlcov/"

test-integration:
	@echo "Running integration tests (requires root)..."
	@[ "$$(id -u)" = "0" ] || (echo "Integration tests require root privileges" && exit 1)
	python3 tests/test_basic_functionality.py

# Code quality targets
lint:
	@echo "Running code linting..."
	flake8 scripts/ examples/ tests/ --max-line-length=100 --ignore=E203,W503
	mypy scripts/ --ignore-missing-imports
	@echo "Linting complete!"

format:
	@echo "Formatting code with black..."
	black scripts/ examples/ tests/ --line-length=100
	@echo "Code formatting complete!"

format-check:
	@echo "Checking code formatting..."
	black scripts/ examples/ tests/ --line-length=100 --check

# Docker targets
docker-build:
	@echo "Building Docker image..."
	docker build -t ebpf-hpc-monitor .
	@echo "Docker image built successfully!"

docker-run:
	@echo "Running Docker container interactively..."
	docker run -it --privileged --pid=host --net=host \
		-v /sys/kernel/debug:/sys/kernel/debug:rw \
		-v /lib/modules:/lib/modules:ro \
		-v /usr/src:/usr/src:ro \
		-v $$(pwd)/output:/app/output \
		ebpf-hpc-monitor

docker-test:
	@echo "Testing Docker container..."
	docker run --rm --privileged --pid=host \
		-v /sys/kernel/debug:/sys/kernel/debug:rw \
		-v /lib/modules:/lib/modules:ro \
		ebpf-hpc-monitor python3 -c "from bcc import BPF; print('Docker test: OK')"

# Example and demo targets
run-examples:
	@echo "Running example scripts..."
	@[ "$$(id -u)" = "0" ] || (echo "Examples require root privileges" && exit 1)
	@echo "Running basic monitoring example..."
	python3 examples/basic_monitoring.py

monitor-user:
	@echo "Monitoring current user for 30 seconds..."
	@[ "$$(id -u)" = "0" ] || (echo "Monitoring requires root privileges" && exit 1)
	python3 scripts/hpc_monitor.py --user $$(logname) --duration 30 --real-time

demo:
	@echo "Running demonstration..."
	@[ "$$(id -u)" = "0" ] || (echo "Demo requires root privileges" && exit 1)
	@echo "Starting demo monitoring session..."
	python3 scripts/hpc_monitor.py --user $$(logname) --duration 60 --output demo_output.json
	@echo "Demo complete! Check demo_output.json for results."

# Documentation targets
docs:
	@echo "Generating documentation..."
	@which sphinx-build >/dev/null || (echo "Sphinx not installed. Run 'pip install sphinx sphinx-rtd-theme'" && exit 1)
	cd docs && make html
	@echo "Documentation generated in docs/_build/html/"

docs-serve:
	@echo "Serving documentation locally..."
	@which python3 -m http.server >/dev/null || (echo "Python HTTP server not available" && exit 1)
	cd docs/_build/html && python3 -m http.server 8080

# Build and distribution targets
build:
	@echo "Building distribution packages..."
	python3 setup.py sdist bdist_wheel
	@echo "Packages built in dist/"

clean:
	@echo "Cleaning build artifacts and cache..."
	rm -rf build/ dist/ *.egg-info/
	rm -rf __pycache__/ */__pycache__/ */*/__pycache__/
	rm -rf .pytest_cache/ .mypy_cache/ .coverage htmlcov/
	rm -rf logs/*.log output/*.json output/*.csv
	find . -name "*.pyc" -delete
	find . -name "*.pyo" -delete
	find . -name "*~" -delete
	@echo "Cleanup complete!"

deep-clean: clean
	@echo "Deep cleaning (including virtual environments)..."
	rm -rf venv/ env/ .venv/
	docker system prune -f
	@echo "Deep cleanup complete!"

# Security and maintenance targets
security-check:
	@echo "Running security checks..."
	@which bandit >/dev/null || (echo "Bandit not installed. Run 'pip install bandit'" && exit 1)
	bandit -r scripts/ examples/ -f json -o security_report.json
	@echo "Security report generated: security_report.json"

upload: build
	@echo "Uploading to PyPI..."
	@which twine >/dev/null || (echo "Twine not installed. Run 'pip install twine'" && exit 1)
	twine upload dist/*

upload-test: build
	@echo "Uploading to Test PyPI..."
	@which twine >/dev/null || (echo "Twine not installed. Run 'pip install twine'" && exit 1)
	twine upload --repository-url https://test.pypi.org/legacy/ dist/*

# Development workflow targets
dev-setup: setup-dev
	@echo "Development setup complete!"
	@echo "Next steps:"
	@echo "  1. Run 'make check-deps' to verify system dependencies"
	@echo "  2. Run 'make test' to verify installation"
	@echo "  3. Run 'sudo make monitor-user' to test monitoring"

ci-test: lint format-check test
	@echo "CI tests passed!"

release-check: clean lint test build
	@echo "Release checks passed!"
	@echo "Ready for release. Run 'make upload' to publish."

# Quick development commands
quick-test:
	@echo "Quick test run..."
	python3 -c "import sys; sys.path.insert(0, 'scripts'); from data_analyzer import JobAnalyzer; print('Import test: OK')"

quick-monitor:
	@echo "Quick monitoring test (10 seconds)..."
	@[ "$$(id -u)" = "0" ] || (echo "Monitoring requires root privileges" && exit 1)
	python3 scripts/hpc_monitor.py --user $$(logname) --duration 10

# Environment information
info:
	@echo "eBPF HPC Monitor - Environment Information:"
	@echo "==========================================="
	@echo "Python: $$(python3 --version)"
	@echo "Platform: $$(uname -a)"
	@echo "User: $$(whoami) (UID: $$(id -u))"
	@echo "Working Directory: $$(pwd)"
	@echo "Available Memory: $$(free -h | grep '^Mem:' | awk '{print $$2}' 2>/dev/null || echo 'N/A')"
	@echo "Kernel Version: $$(uname -r)"
	@echo "Docker: $$(docker --version 2>/dev/null || echo 'Not available')"
	@echo "Git: $$(git --version 2>/dev/null || echo 'Not available')"

# Installation verification
verify-install:
	@echo "Verifying installation..."
	@python3 -c "import sys; sys.path.insert(0, 'scripts'); from ebpf_probes import EBPFProbeManager; print('eBPF Probes: OK')"
	@python3 -c "import sys; sys.path.insert(0, 'scripts'); from slurm_integration import SlurmIntegration; print('Slurm Integration: OK')"
	@python3 -c "import sys; sys.path.insert(0, 'scripts'); from data_analyzer import JobAnalyzer; print('Data Analyzer: OK')"
	@python3 -c "from bcc import BPF; print('BCC: OK')" 2>/dev/null || echo "BCC: NOT AVAILABLE"
	@echo "Installation verification complete!"

# Performance testing
perf-test:
	@echo "Running performance tests..."
	@[ "$$(id -u)" = "0" ] || (echo "Performance tests require root privileges" && exit 1)
	@echo "Testing with high-frequency monitoring..."
	python3 scripts/hpc_monitor.py --user $$(logname) --duration 30 --config config/test_config.yaml

# Backup and restore
backup:
	@echo "Creating backup..."
	mkdir -p backups
	tar -czf backups/ebpf-hpc-monitor-backup-$$(date +%Y%m%d-%H%M%S).tar.gz \
		--exclude='backups' --exclude='.git' --exclude='__pycache__' \
		--exclude='*.pyc' --exclude='output' --exclude='logs' .
	@echo "Backup created in backups/"

# Help for specific topics
help-docker:
	@echo "Docker Usage Help:"
	@echo "================="
	@echo "Build image:     make docker-build"
	@echo "Run interactive: make docker-run"
	@echo "Test container:  make docker-test"
	@echo ""
	@echo "Manual Docker commands:"
	@echo "docker run --privileged --pid=host --net=host \\"
	@echo "  -v /sys/kernel/debug:/sys/kernel/debug:rw \\"
	@echo "  -v /lib/modules:/lib/modules:ro \\"
	@echo "  ebpf-hpc-monitor"

help-monitoring:
	@echo "Monitoring Usage Help:"
	@echo "====================="
	@echo "Monitor user:        sudo python3 scripts/hpc_monitor.py --user USERNAME"
	@echo "Monitor job:         sudo python3 scripts/hpc_monitor.py --job-id JOBID"
	@echo "Real-time display:   sudo python3 scripts/hpc_monitor.py --user USERNAME --real-time"
	@echo "Custom duration:     sudo python3 scripts/hpc_monitor.py --user USERNAME --duration 300"
	@echo "Save to file:        sudo python3 scripts/hpc_monitor.py --user USERNAME --output results.json"
	@echo ""
	@echo "Note: Root privileges required for eBPF operations"

# Show project structure
structure:
	@echo "Project Structure:"
	@echo "================="
	@tree -I '__pycache__|*.pyc|*.log|output|logs|.git' . 2>/dev/null || find . -type f -name "*.py" -o -name "*.md" -o -name "*.yaml" -o -name "Makefile" -o -name "Dockerfile" | grep -v __pycache__ | sort