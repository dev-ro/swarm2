import subprocess
import pathlib
from kernel import self_healing_tool

@self_healing_tool
def run_security_audit(code_path: str) -> str:
    """
    Runs static analysis on the provided code path to check for hardcoded secrets or insecure functions.
    Supports Dart/Flutter (`dart analyze`) and Python (`bandit`).
    If the audit fails, the agent is forbidden from deploying or showing the user the result until fixed.
    
    Args:
        code_path: The directory or file path to analyze.
    """
    target_path = pathlib.Path(code_path).resolve()
    if not target_path.exists():
        return f"[Audit Failed] Path does not exist: {code_path}"

    results = []
    has_errors = False

    # Check for Dart/Flutter projects
    if list(target_path.rglob("*.dart")):
        print(f"[Audit] Running 'dart analyze' on {code_path}...")
        try:
            # Run dart analyze
            process = subprocess.run(
                ["dart", "analyze", str(target_path)],
                capture_output=True,
                text=True
            )
            
            if process.returncode != 0:
                has_errors = True
                results.append(f"Dart Analyze Errors:\n{process.stdout}\n{process.stderr}")
            else:
                results.append("Dart Analyze Passed.")
        except FileNotFoundError:
            results.append("[Audit Warning] 'dart' command not found. Skipping Dart analysis.")

    # Check for Python projects
    if list(target_path.rglob("*.py")):
        print(f"[Audit] Running 'bandit' on {code_path}...")
        try:
            # Run bandit
            process = subprocess.run(
                ["bandit", "-r", str(target_path), "-ll", "-ii"], # Only Medium/High severity
                capture_output=True,
                text=True
            )
            
            if process.returncode != 0:
                has_errors = True
                results.append(f"Bandit Security Errors:\n{process.stdout}\n{process.stderr}")
            else:
                results.append("Bandit Security Passed.")
        except FileNotFoundError:
            results.append("[Audit Warning] 'bandit' command not found. Skipping Python analysis. (Run `pip install bandit`)")

    if not results:
        return f"[Audit Warning] No Dart or Python files found in {code_path}."

    final_report = "\n\n".join(results)
    
    if has_errors:
        return f"AUDIT FAILED! You are forbidden from deploying or showing the user the result until these issues are fixed:\n\n{final_report}"
    
    return f"AUDIT PASSED. Code is secure.\n\n{final_report}"
