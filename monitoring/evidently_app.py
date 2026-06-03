"""
DriftGuard Isolated Evidently Service App.
Runs inside the isolated Evidently service container to calculate batch statistical drift
without importing any heavy gateway database or pipeline libraries.
"""
import os
import numpy as np
import pandas as pd
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from fastapi import FastAPI, HTTPException

# Initialize FastAPI App
app = FastAPI(
    title="DriftGuard Evidently Service",
    description="Isolated Evidently.ai statistical drift calculation service",
    version="1.0.0"
)

class EvidentlyCalculateRequest(BaseModel):
    reference_data: List[Dict[str, Any]]
    current_data: List[Dict[str, Any]]
    target_column: Optional[str] = None

@app.post("/evidently/calculate", summary="Isolated Evidently calculations REST endpoint")
def calculate_evidently_drift_endpoint(req: EvidentlyCalculateRequest):
    """
    Computes statistical data drift using local evidently packages.
    """
    try:
        ref_df = pd.DataFrame(req.reference_data)
        cur_df = pd.DataFrame(req.current_data)
        
        # Evidently Report integration
        from evidently.report import Report
        from evidently.metric_preset import DataDriftPreset, TargetDriftPreset
        
        metrics = [DataDriftPreset()]
        if req.target_column and req.target_column in ref_df.columns and req.target_column in cur_df.columns:
            metrics.append(TargetDriftPreset())
            
        report = Report(metrics=metrics)
        report.run(reference_data=ref_df, current_data=cur_df)
        result = report.as_dict()
        
        drift_metrics = {}
        overall_drift_detected = False
        
        # Extract data drift from Report structure
        drift_data = result["metrics"][0]["result"]
        for feature, detail in drift_data["drift_by_columns"].items():
            drift_score = detail["drift_score"]
            drift_detected = detail["drift_detected"]
            if drift_detected:
                overall_drift_detected = True
            drift_metrics[feature] = {
                "drift_score": float(drift_score),
                "drift_detected": bool(drift_detected),
                "metric_name": detail["test_name"]
            }
            
        scores = [v["drift_score"] for v in drift_metrics.values()]
        overall_drift_score = float(np.mean(scores)) if scores else 0.0
        
        return {
            "drift_detected": overall_drift_detected,
            "metrics": drift_metrics,
            "overall_drift_score": overall_drift_score
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Evidently computation error: {str(e)}")

@app.get("/api/health")
def healthcheck():
    """
    API Health check
    """
    return {"status": "healthy"}
