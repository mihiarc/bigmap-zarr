#!/usr/bin/env python3
"""
Verify that all PR fixes have been implemented correctly.
"""

import sys
from pathlib import Path

def verify_imports():
    """Check that imports are fixed."""
    print("Checking import fixes...")

    # Check that bigmap/utils/examples.py exists
    examples_utils = Path("bigmap/utils/examples.py")
    assert examples_utils.exists(), "bigmap/utils/examples.py not found"
    print("✓ bigmap/utils/examples.py exists")

    # Check that example files import from bigmap
    example_files = list(Path("examples").glob("0*.py"))
    for example in example_files:
        content = example.read_text()
        assert "from bigmap import" in content, f"{example.name} missing bigmap imports"
        assert "from examples.utils import" not in content, f"{example.name} still has old imports"
    print(f"✓ All {len(example_files)} example files use correct imports")

    # Check bigmap/__init__.py exports
    init_file = Path("bigmap/__init__.py")
    content = init_file.read_text()
    assert "from bigmap.utils.examples import" in content
    assert "AnalysisConfig" in content
    assert "safe_download_species" in content
    print("✓ bigmap/__init__.py exports example utilities")

def verify_no_private_api():
    """Check that private API usage is removed."""
    print("\nChecking private API usage...")

    example_03 = Path("examples/03_location_configs.py")
    content = example_03.read_text()
    assert "_config[" not in content, "Still using _config private attribute"
    assert "_detect_state_plane_crs" not in content, "Still using private method"
    assert "LocationConfig.from_county" in content, "Not using public API"
    print("✓ No private API usage in 03_location_configs.py")

def verify_error_handling():
    """Check that error handling is added."""
    print("\nChecking error handling...")

    example_01 = Path("examples/01_quickstart.py")
    content = example_01.read_text()
    assert "safe_download_species" in content, "Not using safe download function"
    assert "try:" in content or "except" in content, "Missing error handling"
    print("✓ Error handling added to 01_quickstart.py")

    examples_utils = Path("bigmap/utils/examples.py")
    content = examples_utils.read_text()
    assert "def safe_download_species" in content
    assert "max_retries" in content
    assert "ConnectionError" in content
    print("✓ safe_download_species function with retry logic exists")

def verify_config_class():
    """Check that AnalysisConfig exists."""
    print("\nChecking configuration class...")

    examples_utils = Path("bigmap/utils/examples.py")
    content = examples_utils.read_text()
    assert "@dataclass" in content
    assert "class AnalysisConfig:" in content
    assert "biomass_threshold:" in content
    assert "diversity_percentile:" in content
    assert "max_pixels:" in content
    print("✓ AnalysisConfig dataclass exists with all fields")

def verify_memory_management():
    """Check memory management functions."""
    print("\nChecking memory management...")

    examples_utils = Path("bigmap/utils/examples.py")
    content = examples_utils.read_text()
    assert "def safe_load_zarr_with_memory_check" in content
    assert "max_pixels" in content
    assert "downsampling" in content.lower() or "sample" in content.lower()
    print("✓ Memory management function exists")

def verify_citations():
    """Check CITATIONS.md exists."""
    print("\nChecking citations...")

    citations = Path("CITATIONS.md")
    assert citations.exists(), "CITATIONS.md not found"
    content = citations.read_text()
    assert "Shannon" in content
    assert "Simpson" in content
    assert "Pielou" in content
    assert "BIGMAP" in content
    print("✓ CITATIONS.md exists with all references")

def verify_tests():
    """Check test file exists."""
    print("\nChecking tests...")

    test_file = Path("tests/integration/test_examples.py")
    assert test_file.exists(), "test_examples.py not found"
    content = test_file.read_text()
    assert "TestExamplesSmoke" in content
    assert "test_utils_module" in content
    assert "AnalysisConfig" in content
    print("✓ Smoke tests exist")

def verify_documentation():
    """Check documentation updates."""
    print("\nChecking documentation...")

    tutorial = Path("docs/tutorials/species-diversity-analysis.md")
    content = tutorial.read_text()
    assert "Scientific Background" in content
    assert "Shannon, 1948" in content
    assert "Simpson, 1949" in content
    assert "Interpreting Results" in content
    assert "Ecological Implications" in content
    print("✓ Documentation includes scientific background")

def main():
    print("=" * 60)
    print("Verifying PR Fixes Implementation")
    print("=" * 60)

    try:
        verify_imports()
        verify_no_private_api()
        verify_error_handling()
        verify_config_class()
        verify_memory_management()
        verify_citations()
        verify_tests()
        verify_documentation()

        print("\n" + "=" * 60)
        print("✅ ALL CHECKS PASSED - PR fixes successfully implemented!")
        print("=" * 60)
        return 0

    except AssertionError as e:
        print(f"\n❌ VERIFICATION FAILED: {e}")
        return 1
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())