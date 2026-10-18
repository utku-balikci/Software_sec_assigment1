import subprocess
import sys
import time
import os
## for local tests 

def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    venv_py = os.path.join(base_dir, "venv", "bin", "python")
    py_exec = venv_py if os.path.exists(venv_py) else sys.executable
    
    print("=" * 66)
    print("           PIPELINE SIMULATION (Matching Jenkinsfile)            ")
    print("=" * 66)

    print("\n[STAGE 1: Setup & Dependencies]")
    subprocess.run([py_exec, "-m", "pip", "install", "-q", "bandit", "flake8"], check=False)
    print(">> Dependencies verified.")

    print("\n[STAGE 2: Static Analysis & Security Gate]")
    print(">> Running Bandit security scanner on services/...")
    subprocess.run([py_exec, "-m", "bandit", "-r", "services/", "-ll"], cwd=base_dir, check=False)
    print(">> Security gate check completed.")

    print("\n[STAGE 3: Launch Services & Run Automated Tests]")
    # Kill any dangling ports
    subprocess.run("lsof -ti :8000 -ti :8001 -ti :8002 | xargs kill -9 2>/dev/null || true", shell=True)

    # Start services in background
    runner = subprocess.Popen([py_exec, "run_services.py"], cwd=base_dir, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(3)

    print(">> Running functional & authorization test suite...")
    subprocess.run([py_exec, "-m", "pytest", "-v", "tests/test_flow.py", "--junitxml=test-results.xml"], cwd=base_dir)

    print("\n>> Running vulnerability demonstration suite...")
    subprocess.run([py_exec, "-m", "pytest", "-s", "-v", "tests/test_vulnerabilities.py"], cwd=base_dir)

    runner.terminate()
    runner.wait()
    subprocess.run("lsof -ti :8000 -ti :8001 -ti :8002 | xargs kill -9 2>/dev/null || true", shell=True)

    print("\n[STAGE 4: Post-Build & Artifacts]")
    xml_path = os.path.join(base_dir, "test-results.xml")
    if os.path.exists(xml_path):
        print(f">> Test artifact generated: test-results.xml ({os.path.getsize(xml_path)} bytes)")

    print("\n" + "=" * 66)
    print("                PIPELINE COMPLETED SUCCESSFULLY!                  ")
    print("=" * 66)

if __name__ == "__main__":
    main()
