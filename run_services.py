import subprocess
import sys
import time
import signal
import os

def get_python_executable():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    venv_py = os.path.join(base_dir, "venv", "bin", "python")
    if os.path.exists(venv_py):
        return venv_py
    return sys.executable

def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    py_exec = get_python_executable()
    
    # Add packages to PYTHONPATH for child processes
    env = os.environ.copy()
    pkg_dir = os.path.join(base_dir, "packages", "html_note_formatter")
    env["PYTHONPATH"] = f"{pkg_dir}:{env.get('PYTHONPATH', '')}"

    SERVICES = [
        {"name": "Resource Service (Port 8001)", "cwd": "services/resource_service", "cmd": [py_exec, "-m", "uvicorn", "main:app", "--port", "8001"]},
        {"name": "Processing Service (Port 8002)", "cwd": "services/processing_service", "cmd": [py_exec, "-m", "uvicorn", "main:app", "--port", "8002"]},
        {"name": "App API Gateway (Port 8000)", "cwd": "services/app_api", "cmd": [py_exec, "-m", "uvicorn", "main:app", "--port", "8000"]}
    ]

    processes = []
    
    print("=" * 60)
    print("Starting Secure Notes & Export Microservices Architecture...")
    print("=" * 60)
    
    def cleanup(signum=None, frame=None):
        print("\nStopping services...")
        for p in processes:
            p.terminate()
        for p in processes:
            p.wait()
        print("All services stopped.")
        sys.exit(0)

    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)

    for svc in SERVICES:
        full_cwd = os.path.join(base_dir, svc["cwd"])
        print(f"[+] Launching {svc['name']}...")
        p = subprocess.Popen(svc["cmd"], cwd=full_cwd, env=env)
        processes.append(p)
        time.sleep(1) # stagger launch

    print("\nAll 3 services are active!")
    print("API Gateway Swagger Docs: http://127.0.0.1:8000/docs")
    print("Press Ctrl+C to terminate all services.\n")

    while True:
        time.sleep(1)

if __name__ == "__main__":
    main()
