"""
DriftGuard Alert Manager.
Distributes, formats, and silences platform notifications based on severity rules.
"""
import logging
from typing import Dict, Any, Optional

from driftguard.alert import send_alert
from driftguard.config import settings

logger = logging.getLogger("DriftGuard.AlertManager")

class AlertManager:
    """
    Manages alerting rules, severity filtering, and channel routing.
    """
    def __init__(self, slack_webhook_url: Optional[str] = None):
        self.slack_url = slack_webhook_url or settings.SLACK_WEBHOOK_URL

    def trigger_alert(
        self,
        event_type: str,
        message: str,
        severity: str = "info",  # info, warning, critical
        details: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Processes and routes alerts.
        
        Args:
            event_type: Category key.
            message: Readable message body.
            severity: Severity level.
            details: Context properties.
        """
        payload_details = details or {}
        payload_details["severity"] = severity.upper()
        
        # Add visual indicators for visual clarity in Slack
        prefix = "ℹ️"
        if severity == "warning":
            prefix = "⚠️"
        elif severity == "critical":
            prefix = "🚨"
            
        formatted_message = f"{prefix} *[{severity.upper()}]* {message}"
        
        logger.info(f"AlertManager processing event '{event_type}' [{severity.upper()}]...")
        
        # Route to standard SDK alert sender
        return send_alert(
            event_type=event_type,
            message=formatted_message,
            details=payload_details,
            webhook_url=self.slack_url
        )
