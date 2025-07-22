import subprocess
import webbrowser
import os
from pathlib import Path

# --- Configuration ---
COV_TARGET = "nos" 
TEST_REPORT_FILENAME = "test_report.html"
COVERAGE_DIR = "htmlcov"


def run_tests():
    """Runs pytest to generate test and coverage reports."""
    print("--- Running tests and generating reports... ---")
    
    command = [
        "pytest",
        f"--cov={COV_TARGET}",
        f"--cov-report=html:{COVERAGE_DIR}",
        f"--html={TEST_REPORT_FILENAME}",
        "--self-contained-html",
    ]
    
    result = subprocess.run(command, capture_output=True, text=True)
    
    print(result.stdout)
    if result.stderr:
        print("--- Errors ---")
        print(result.stderr)
    
    if result.returncode not in [0, 5]: # 0=ok, 5=no tests collected
         print(f"Pytest exited with status code: {result.returncode}")
         return False
         
    print("--- Reports generated successfully. ---")
    return True

def move_test_report():
    """Moves the test report into the coverage directory."""
    source_path = Path(TEST_REPORT_FILENAME)
    dest_dir = Path(COVERAGE_DIR)
    
    if not source_path.exists():
        print(f"Warning: Test report '{TEST_REPORT_FILENAME}' not found. Skipping move.")
        return False
        
    dest_path = dest_dir / TEST_REPORT_FILENAME
    print(f"--- Moving '{source_path}' to '{dest_path}' ---")
    source_path.rename(dest_path)
    return True

def enhance_coverage_report():
    """Adds a link to the test report inside the main coverage report."""
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        print("\nError: 'beautifulsoup4' not installed. Please run 'pip install beautifulsoup4'.")
        return False

    coverage_report_path = Path(COVERAGE_DIR) / "index.html"
    
    if not coverage_report_path.exists():
        print(f"Error: Coverage report not found at {coverage_report_path}")
        return False

    print(f"--- Enhancing coverage report at {coverage_report_path} ---")
    
    with open(coverage_report_path, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f, "html.parser")

    header = soup.find("h1")
    if header:
        # Since the report is now in the same directory, the link is direct.
        link_tag = soup.new_tag(
            "a",
            href=TEST_REPORT_FILENAME,
            style="font-size: 1.2rem; float: right; text-decoration: none; color: #49a;"
        )
        link_tag.string = f"View Test Report ({TEST_REPORT_FILENAME})"
        
        header.append(link_tag)
        
        with open(coverage_report_path, "w", encoding="utf-8") as f:
            f.write(str(soup))
            
        print("--- Link added successfully. ---")
        return True
    else:
        print("Error: Could not find the header in the coverage report to inject the link.")
        return False


def open_report():
    """Opens the final coverage report in the default web browser."""
    report_url = Path(os.getcwd()) / COVERAGE_DIR / "index.html"
    print(f"\n--- Opening report: {report_url.as_uri()} ---")
    webbrowser.open(report_url.as_uri())


if __name__ == "__main__":
    if run_tests():
        if move_test_report():
            if enhance_coverage_report():
                open_report()

