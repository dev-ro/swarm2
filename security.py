import os
import functools
from typing import Callable, Any

def requires_permission(func: Callable) -> Callable:
    """
    Decorator that pauses execution and prompts the user for (y/n) permission
    before running sensitive tool functions.
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        tool_name = func.__name__
        args_repr = ", ".join(repr(a) for a in args)
        kwargs_repr = ", ".join(f"{k}={v!r}" for k, v in kwargs.items())
        all_args = ", ".join(filter(None, [args_repr, kwargs_repr]))
        
        print("\n" + "="*50)
        print(f"⚠️  SECURITY ALERT: Agent requesting permission ⚠️")
        print(f"Tool: {tool_name}({all_args})")
        print("="*50)
        
        while True:
            choice = input(f"Allow '{tool_name}' to execute? (y/n): ").strip().lower()
            if choice == 'y':
                print("[Gatekeeper] Permission granted. Executing...")
                return func(*args, **kwargs)
            elif choice == 'n':
                print("[Gatekeeper] Permission denied by user.")
                return "Permission Denied: User rejected the execution of this tool."
            else:
                print("Invalid input. Please enter 'y' or 'n'.")
                
    return wrapper

def get_credential(service_name: str) -> str:
    """
    Retrieves a credential for a given service. First checks the environment.
    If not found, it prompts the user to securely paste the credential.
    The agent never handles raw passwords permanently.
    """
    # 1. Check environment variables
    env_var_name = f"{service_name.upper()}_TOKEN"
    token = os.environ.get(env_var_name)
    
    if token:
        return f"Credential for '{service_name}' retrieved successfully from environment."
    
    # 2. If missing, prompt the human
    print("\n" + "="*50)
    print(f"🔐 CREDENTIAL REQUIRED: {service_name} 🔐")
    print(f"The agent requires access to {service_name}.")
    print(f"Please authenticate in your browser and paste the token below.")
    print("="*50)
    
    manual_token = input(f"Enter token for {service_name}: ").strip()
    
    if manual_token:
        # Note: In a real environment, you might hold this in an in-memory secure vault.
        # Here we just inject it into the process environment temporarily.
        os.environ[env_var_name] = manual_token
        return f"Credential for '{service_name}' provided manually and stored in active session."
    else:
        return f"Error: No credential provided for {service_name}."
