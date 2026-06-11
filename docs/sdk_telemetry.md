# SDK & Telemetry Queue Architecture

This document describes how the DriftGuard Python SDK intercepts model inputs/outputs, buffers prediction payloads, and streams telemetry data asynchronously to the central monitoring gateway.

---

## 1. Inference Interception Protocol

DriftGuard wraps models to capture features and predictions without modifying model invocation code.

```text
                  ┌──────────────────────────────────────────────┐
                  │                 Wrapped Model                │
                  └──────────────────────┬───────────────────────┘
                                         │ predict()
                                         ▼
                  ┌──────────────────────────────────────────────┐
                  │       Standardized Input & ADWIN Check       │
                  └──────────────────────┬───────────────────────┘
                                         │
                        ┌────────────────┴────────────────┐
                        │ Put telemetry payload           │
                        ▼                                 ▼
         ┌──────────────────────────────┐  ┌──────────────────────────────┐
         │       Telemetry Queue        │  │      ADWIN Drift Score       │
         │       (Bounded: 15000)       │  └──────────────────────────────┘
         └──────────────┬───────────────┘
                        │
                        │ (Worker consumes async)
                        ▼
         ┌──────────────────────────────┐
         │      Persistent HTTP         │
         │       Connection Pool        │
         └──────────────┬───────────────┘
                        │
                        ▼ POST /predict/{id}
         ┌──────────────────────────────┐
         │     DriftGuard API Server    │
         └──────────────────────────────┘
```

* **Method Delegation**: When a model is wrapped using `wrapped = dg.wrap(model)`, the `DriftGuardModelWrapper` class intercepts `predict()`, `predict_proba()`, and `__call__()` invocations. Remaining properties and methods are delegated using Python's `__getattr__`.
* **Standardization**: Input formats (such as PyTorch tensors, Pandas DataFrames, or raw text lists) are standardized into 2D float32 numpy arrays before drift calculations begin.

---

## 2. Ingestion Backpressure & Bounded Queue

To prevent network latency from affecting client inference performance, logging is decoupled from prediction execution:

* **Bounded Buffer**: The internal queue is limited to `15,000` records.
* **Drop Strategy**: If the queue fills up, new payloads are dropped immediately, and a `queue.Full` warning is logged. This prioritizes prediction speed over telemetry completion.
* **Tracking Quality Counters**: The SDK tracks transmission quality using three metrics:
  - `telemetry_queued`: Incremented on ingestion.
  - `telemetry_sent`: Incremented on successful HTTP status 200 upload.
  - `telemetry_failed`: Incremented when payloads are dropped or fail after retry limits.

---

## 3. Worker Thread & Network Resilience

A background consumer thread (`_telemetry_worker_loop`) handles the upload queue:

* **Persistent Pool**: Reuses a single `httpx.Client()` session to minimize the overhead of TCP connection handshakes.
* **Socket Recovery**: If a connection reset is encountered (e.g., `WinError 10054` or `10061`), the worker releases the corrupted pool and creates a new `httpx.Client()` session.
* **Exponential Backoff**: Failed requests are retried up to 5 times using exponential backoff to allow database locks to clear.
* **Graceful Shutdown**: Handled via `atexit`. When the application exits, the worker stops accepting new requests, drains the queue, and joins the thread before terminating.
