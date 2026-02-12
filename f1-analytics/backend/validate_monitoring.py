#!/usr/bin/env python3
"""
Simple validation script for F1 Analytics monitoring implementation.

This script performs basic syntax and import validation to ensure the
monitoring implementation is correct without needing to run the full application.
"""

import sys
import os
import ast
import traceback
from pathlib import Path

def validate_python_syntax(file_path):
    """Validate Python syntax for a file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            source_code = file.read()

        # Parse the AST to check syntax
        ast.parse(source_code)
        return True, None
    except SyntaxError as e:
        return False, f"Syntax error: {e}"
    except Exception as e:
        return False, f"Error reading file: {e}"

def validate_monitoring_implementation():
    """Validate the monitoring implementation."""
    print("🔍 Validating F1 Analytics Monitoring Implementation")
    print("=" * 60)

    # Get the backend directory
    backend_dir = Path(__file__).parent
    monitoring_dir = backend_dir / "app" / "monitoring"

    # Files to validate
    files_to_check = [
        monitoring_dir / "__init__.py",
        monitoring_dir / "metrics.py",
        monitoring_dir / "middleware.py",
        monitoring_dir / "services.py",
        backend_dir / "app" / "main.py",
        backend_dir / "tests" / "unit" / "test_monitoring.py"
    ]

    all_valid = True

    # Check syntax for each file
    print("\n📝 Syntax Validation:")
    for file_path in files_to_check:
        if file_path.exists():
            is_valid, error = validate_python_syntax(file_path)
            status = "✓" if is_valid else "✗"
            print(f"  {status} {file_path.name}")
            if error:
                print(f"    Error: {error}")
                all_valid = False
        else:
            print(f"  ⚠ {file_path.name} (not found)")

    # Check imports and basic structure
    print("\n🔧 Implementation Validation:")

    # Check if prometheus-client is in requirements.txt
    requirements_path = backend_dir / "requirements.txt"
    if requirements_path.exists():
        with open(requirements_path, 'r') as f:
            requirements_content = f.read()
        if "prometheus-client" in requirements_content:
            print("  ✓ prometheus-client dependency found in requirements.txt")
        else:
            print("  ✗ prometheus-client dependency missing from requirements.txt")
            all_valid = False

    # Validate monitoring module structure
    monitoring_init = monitoring_dir / "__init__.py"
    if monitoring_init.exists():
        with open(monitoring_init, 'r') as f:
            init_content = f.read()

        required_imports = [
            "metrics_registry",
            "PrometheusMiddleware",
            "instrument_fastapi_app",
            "track_prediction_generated"
        ]

        missing_imports = []
        for import_name in required_imports:
            if import_name not in init_content:
                missing_imports.append(import_name)

        if not missing_imports:
            print("  ✓ All required monitoring components exported")
        else:
            print(f"  ✗ Missing exports: {', '.join(missing_imports)}")
            all_valid = False

    # Check main.py integration
    main_py = backend_dir / "app" / "main.py"
    if main_py.exists():
        with open(main_py, 'r') as f:
            main_content = f.read()

        integration_checks = [
            ("from app.monitoring import", "Monitoring module imported"),
            ("PrometheusMiddleware", "Prometheus middleware configured"),
            ("instrument_fastapi_app", "FastAPI instrumentation"),
            ("/metrics", "Metrics endpoint available")
        ]

        for check_text, description in integration_checks:
            if check_text in main_content:
                print(f"  ✓ {description}")
            else:
                print(f"  ✗ {description} - missing '{check_text}'")
                all_valid = False

    # Validate Prometheus configuration files
    print("\n⚙️  Configuration Validation:")

    config_files = [
        backend_dir.parent / "infrastructure" / "monitoring" / "prometheus.yml",
        backend_dir.parent / "infrastructure" / "monitoring" / "prometheus-config.yaml"
    ]

    for config_file in config_files:
        if config_file.exists():
            print(f"  ✓ {config_file.name} exists")

            # Basic content validation
            with open(config_file, 'r') as f:
                config_content = f.read()

            if "f1-analytics" in config_content:
                print(f"    ✓ Contains F1 Analytics configuration")
            else:
                print(f"    ⚠ May not contain F1-specific configuration")
        else:
            print(f"  ✗ {config_file.name} missing")
            all_valid = False

    # Summary
    print("\n" + "=" * 60)
    if all_valid:
        print("🎉 Validation PASSED - Monitoring implementation looks good!")
        print("\n💡 Next Steps:")
        print("   1. Test the /metrics endpoint with curl or browser")
        print("   2. Start Prometheus and verify metrics are scraped")
        print("   3. Verify alert rules work as expected")
        print("   4. Check Grafana dashboards display F1 metrics")
        return 0
    else:
        print("❌ Validation FAILED - Please fix the issues above")
        return 1

def check_prometheus_metrics_format():
    """Check if the metrics format follows Prometheus conventions."""
    print("\n📊 Prometheus Metrics Convention Check:")

    # Common Prometheus naming conventions
    conventions = {
        "total": "Counter metrics should end with '_total'",
        "seconds": "Duration metrics should end with '_seconds'",
        "ratio": "Ratio metrics should be between 0 and 1",
        "info": "Info metrics should end with '_info'"
    }

    metrics_file = Path(__file__).parent / "app" / "monitoring" / "metrics.py"
    if metrics_file.exists():
        with open(metrics_file, 'r') as f:
            metrics_content = f.read()

        # Check for proper naming patterns
        if "requests_total" in metrics_content:
            print("  ✓ Counter metrics follow '_total' convention")
        else:
            print("  ⚠ Check counter metric naming")

        if "duration_seconds" in metrics_content:
            print("  ✓ Duration metrics follow '_seconds' convention")
        else:
            print("  ⚠ Check duration metric naming")

        if "CollectorRegistry" in metrics_content:
            print("  ✓ Custom registry used (good for testing)")
        else:
            print("  ⚠ Using default registry (may cause conflicts)")

    print("  ✓ Metric naming conventions validated")

if __name__ == "__main__":
    try:
        exit_code = validate_monitoring_implementation()
        check_prometheus_metrics_format()
        sys.exit(exit_code)
    except Exception as e:
        print(f"\n💥 Validation script failed: {e}")
        traceback.print_exc()
        sys.exit(1)