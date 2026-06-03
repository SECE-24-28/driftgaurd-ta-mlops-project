"""
DriftGuard Auto-Rollback Service.
Actively evaluates deployed canary SLA performance and triggers emergency traffic rollbacks on failures.
"""
import logging
from typing import Dict, Any

from pipeline.deploy_pipeline import rollback_canary

logger = logging.getLogger("DriftGuard.RollbackService")

class RollbackService:
    """
    Validates model latency and accuracy SLAs, initiating rollbacks automatically on breaches.
    """
    def __init__(self, max_error_rate: float = 0.05, max_latency_ms: float = 500.0):
        self.max_error_rate = max_error_rate
        self.max_latency_ms = max_latency_ms

    def evaluate_sla_and_check_rollback(
        self,
        model_id: str,
        current_error_rate: float,
        current_p99_latency_ms: float
    ) -> bool:
        """
        Validates telemetry performance and rolls back immediately on failures.
        
        Args:
            model_id: Monitored model ID.
            current_error_rate: Current computed error fraction.
            current_p99_latency_ms: Current p99 latency in milliseconds.
            
        Returns:
            True if SLA is healthy, False if breached and rollback was initiated.
        """
        logger.info(f"[{model_id}] Evaluating canary deployment SLAs | Error Rate: {current_error_rate*100:.2f}% (Limit: {self.max_error_rate*100:.1f}%), p99 Latency: {current_p99_latency_ms:.1f}ms (Limit: {self.max_latency_ms}ms)")
        
        error_breach = current_error_rate > self.max_error_rate
        latency_breach = current_p99_latency_ms > self.max_latency_ms
        
        if error_breach or latency_breach:
            logger.warning(f"[{model_id}] SLA BREACH DETECTED! Initiating emergency rollback...")
            rollback_canary(model_id)
            return False
            
        logger.info(f"[{model_id}] Canary SLAs within healthy boundaries.")
        return True
