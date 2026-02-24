from python_on_whales import docker
from python_on_whales.exceptions import DockerException
import uuid
from security import requires_permission

class SandboxedExecutor:
    """
    Executes Python code or shell commands strictly within an isolated Docker container.
    Defaults to no network access for ultimate security.
    """
    
    def __init__(self, image: str = "python:3.11-slim"):
        self.image = image
        
    def _run_in_container(self, command: list, require_network: bool) -> str:
        network_mode = "bridge" if require_network else "none"
        container_name = f"sandbox_{uuid.uuid4().hex[:8]}"
        
        try:
            print(f"[Sandbox] Starting container '{container_name}' (Network: {network_mode})")
            
            # Using inline execution rather than keeping a long-lived container for simplicity
            # For complex apps, we'd mount volumes. Here, we execute right inside the container.
            output = docker.run(
                self.image,
                command,
                name=container_name,
                remove=True,
                networks=[network_mode] if network_mode != "none" else [],
                network_mode=network_mode if network_mode == "none" else None
            )
            return f"Execution successful:\n{output}"
            
        except DockerException as e:
            return f"Sandbox execution failed: {e.stderr if hasattr(e, 'stderr') else str(e)}"
        except Exception as e:
             return f"Unexpected sandbox error: {str(e)}"

    def execute_python(self, code: str, require_network: bool = False) -> str:
        """
        Executes arbitrary python code inside the sandbox.
        If network access is requested, it MUST trigger HITL permission.
        """
        command = ["python", "-c", code]
        
        if require_network:
            return self._execute_with_permission(command=command, script=code)
        
        return self._run_in_container(command, require_network=False)
        
    def execute_shell(self, cmd: str, require_network: bool = False) -> str:
        """
        Executes arbitrary shell commands inside the sandbox.
        """
        command = ["sh", "-c", cmd]
        
        if require_network:
             return self._execute_with_permission(command=command, script=cmd)
             
        return self._run_in_container(command, require_network=False)

    @requires_permission
    def _execute_with_permission(self, command: list, script: str) -> str:
        """
        Private wrapper to trigger the HITL check if network is required.
        """
        return self._run_in_container(command, require_network=True)
