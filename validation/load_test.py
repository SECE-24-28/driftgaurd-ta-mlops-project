import os
import sys
import time
import httpx
import numpy as np
from sklearn.datasets import load_breast_cancer
from sklearn.ensemble import RandomForestClassifier

# Ensure project root is in python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from driftguard.tracker import DriftGuard

# Import psutil for resource monitoring
try:
    import psutil
except ImportError:
    psutil = None

def get_cpu_memory():
    if psutil:
        process = psutil.Process(os.getpid())
        mem_mb = process.memory_info().rss / (1024 * 1024)
        cpu_pct = psutil.cpu_percent(interval=0.1)
        return mem_mb, cpu_pct
    return 0.0, 0.0

def run_load_test():
    print("=========================================================")
    print("PHASE G: LOAD & PERFORMANCE TEST")
    print("=========================================================")
    
    report = {
        "Phase": "Phase G: Load & Performance Test",
        "Total_Predictions": 10000,
        "Steps": []
    }

    # Setup model and data
    data = load_breast_cancer()
    X = data.data
    y = data.target
    
    indices = np.arange(len(X))
    np.random.seed(42)
    np.random.shuffle(indices)
    X_train = X[:300]
    y_train = y[:300]
    X_live = X[400:]

    clf = RandomForestClassifier(n_estimators=10, random_state=42)
    clf.fit(X_train, y_train)

    api_url = "http://127.0.0.1:8000"
    api_key = "dg-default-key"
    headers = {"X-API-Key": api_key}
    model_id = "val-load-model"

    # Pre-register model
    try:
        httpx.post(f"{api_url}/register", json={
            "model_id": model_id,
            "project_id": 1,
            "drift_threshold": 0.50,
            "features": [f"feat_{i}" for i in range(X.shape[1])]
        }, headers=headers)
    except Exception as e:
        print(f"[FAIL] Pre-registration failed: {e}")
        return report

    # Initialize DriftGuard client
    dg = DriftGuard(
        model_id=model_id,
        api_url=api_url,
        api_key=api_key,
        project_id=1,
        drift_threshold=0.50,
        auto_retrain=False
    )
    wrapped = dg.wrap(clf)

    # Generate 10,000 samples by resampling
    np.random.seed(42)
    resample_idx = np.random.choice(len(X_live), size=10000, replace=True)
    X_load = X_live[resample_idx]

    batch_size = 100
    num_batches = 10000 // batch_size

    print(f"Triggering {report['Total_Predictions']} predictions in {num_batches} batches of size {batch_size}...")
    
    initial_mem, initial_cpu = get_cpu_memory()
    latencies = []
    
    start_time = time.time()
    for b in range(num_batches):
        batch = X_load[b * batch_size : (b + 1) * batch_size]
        
        t0 = time.time()
        _ = wrapped.predict(batch)
        latencies.append(time.time() - t0)
        
        # Pacing delay between batches to avoid socket congestion
        time.sleep(0.01)

    duration = time.time() - start_time
    print("Waiting 5 seconds for telemetry threads to complete...")
    time.sleep(5.0)
    
    final_mem, final_cpu = get_cpu_memory()
    mem_growth = final_mem - initial_mem

    # Compute latency statistics (per batch)
    latencies_ms = [l * 1000.0 for l in latencies]
    avg_latency = np.mean(latencies_ms)
    p95_latency = np.percentile(latencies_ms, 95)
    p99_latency = np.percentile(latencies_ms, 99)

    print(f"\nLoad Test Completed in {duration:.2f} seconds.")
    print(f"Memory Check: Initial = {initial_mem:.2f} MB | Final = {final_mem:.2f} MB | Growth = {mem_growth:.2f} MB")
    print(f"Latency stats per batch of {batch_size}:")
    print(f" - Average: {avg_latency:.2f} ms")
    print(f" - P95: {p95_latency:.2f} ms")
    print(f" - P99: {p99_latency:.2f} ms")

    # Verify server is still alive
    try:
        resp = httpx.get(f"{api_url}/openapi.json")
        server_ok = resp.status_code == 200
    except Exception:
        server_ok = False

    status = "PASS" if (server_ok and mem_growth < 25.0) else "FAIL"
    if not server_ok:
        detail = "Server crashed/unreachable after load test."
    elif mem_growth >= 25.0:
        detail = f"High memory growth: {mem_growth:.2f} MB"
    else:
        detail = f"10k predictions processed successfully. Avg batch latency: {avg_latency:.2f}ms"

    report["Steps"].append({
        "name": "Load Test Execution",
        "status": status,
        "detail": detail,
        "metrics": {
            "duration_sec": duration,
            "initial_memory_mb": initial_mem,
            "final_memory_mb": final_mem,
            "memory_growth_mb": mem_growth,
            "avg_latency_ms": avg_latency,
            "p95_latency_ms": p95_latency,
            "p99_latency_ms": p99_latency,
            "server_healthy": server_ok
        }
    })

    return report

if __name__ == "__main__":
    res = run_load_test()
    print("\nSummary results:")
    for step in res["Steps"]:
        print(f" - {step['name']}: {step['status']} ({step['detail']})")
