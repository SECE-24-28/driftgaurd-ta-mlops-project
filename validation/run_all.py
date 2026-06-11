import os
import sys
import subprocess

# Ensure project root is in python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

def run_script(script_name):
    print(f"\n=========================================================")
    print(f"RUNNING: {script_name}")
    print(f"=========================================================")
    
    script_path = os.path.join(os.path.dirname(__file__), script_name)
    try:
        res = subprocess.run([sys.executable, script_path], capture_output=True, text=True, check=True)
        print(res.stdout)
        return True, res.stdout
    except subprocess.CalledProcessError as e:
        print(e.stdout)
        print(f"ERROR running {script_name}: {e.stderr}", file=sys.stderr)
        return False, e.stdout + "\n" + e.stderr

def main():
    scripts = [
        "validate_sdk.py",
        "validate_drift_detection.py",
        "validate_retraining.py",
        "validate_multi_user.py",
        "load_test.py"
    ]
    
    results = {}
    all_passed = True
    
    for script in scripts:
        passed, output = run_script(script)
        results[script] = passed
        if not passed:
            all_passed = False
            
    print("\n=========================================================")
    print("GLOBAL VALIDATION SUITE SUMMARY")
    print("=========================================================")
    for script, passed in results.items():
        status = "PASS" if passed else "FAIL"
        print(f" - {script:<30}: {status}")
        
    print("-" * 57)
    if all_passed:
        print("RESULT: ALL VALIDATION PHASES PASSED SUCCESSFULLY!")
        sys.exit(0)
    else:
        print("RESULT: SOME VALIDATION PHASES FAILED!")
        sys.exit(1)

if __name__ == "__main__":
    main()
