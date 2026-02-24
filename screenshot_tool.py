from playwright.sync_api import sync_playwright
import pathlib
import subprocess
import time
from security import requires_permission
from kernel import self_healing_tool

@requires_permission
@self_healing_tool
def capture_app_screenshot(url: str = "http://localhost:8080", is_flutter: bool = True, filename: str = "v1.png") -> str:
    """
    Captures a screenshot of the running app. If is_flutter is True, it starts 
    the Flutter web server first.
    
    Args:
        url: The internal URL to capture.
        is_flutter: Whether to run `flutter run -d chrome` before capturing.
        filename: Name of the screenshot file.
    """
    workspace_dir = pathlib.Path("./workspace").resolve()
    screenshot_dir = workspace_dir / "screenshots"
    screenshot_dir.mkdir(parents=True, exist_ok=True)
    
    save_path = screenshot_dir / filename
    flutter_process = None

    if is_flutter:
        print("[Screenshot] Starting Flutter web server...")
        # Run flutter web headless if possible, or detached
        flutter_process = subprocess.Popen(
            ["flutter", "run", "-d", "web-server", "--web-port", "8080"],
            cwd=str(workspace_dir),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        # Give Flutter some time to build and start serving
        time.sleep(15)

    print(f"[Screenshot] Attempting to capture {url} to {save_path}...")
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            # Wait until there are no network connections for at least 500 ms.
            page.goto(url, wait_until="networkidle", timeout=30000)
            
            page.screenshot(path=str(save_path), full_page=True)
            browser.close()
            
        result_msg = f"Successfully captured screenshot of {url}. Saved to {save_path}"
    except Exception as e:
        result_msg = f"Failed to capture screenshot: {str(e)}"
    finally:
        if flutter_process:
            print("[Screenshot] Terminating Flutter web server...")
            flutter_process.terminate()

    return result_msg
