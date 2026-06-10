"""
DriftGuard Alerting & Notification Client.
Handles distribution of system alert updates to console logs and webhook endpoints like Slack.
"""
import httpx
import logging
from typing import Dict, Any, Optional

from driftguard.config import settings

logger = logging.getLogger("DriftGuard.Alert")

def send_alert(
    event_type: str,
    message: str,
    details: Optional[Dict[str, Any]] = None,
    webhook_url: Optional[str] = None
) -> bool:
    """
    Distributes alert notification updates to platform targets.
    
    Args:
        event_type: Category of the alert (e.g., 'drift_detected', 'retrain_triggered', 'validation_failed', 'model_promoted').
        message: Readable summary message string.
        details: Optional JSON data properties containing details about the event.
        webhook_url: Optional override of settings Slack Webhook URL.
        
    Returns:
        True if successfully sent (or logged when offline), False on HTTP failure.
    """
    payload_details = details or {}
    url = webhook_url or settings.SLACK_WEBHOOK_URL
    
    # 1. Standard Logger Print
    log_msg = f"[ALERT - {event_type.upper()}] {message} | Details: {payload_details}"
    if event_type in ["drift_detected", "validation_failed", "rollback"]:
        logger.error(log_msg)
    else:
        logger.info(log_msg)

    # 2. Slack Webhook Dispatch
    if not url or "mock_webhook_url" in url:
        logger.debug("No active Slack webhook configured. Skipping network alert.")
        return True

    try:
        # Construct premium formatted Slack block
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"🛡️ DriftGuard Alert: {event_type.replace('_', ' ').title()}",
                    "emoji": True
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Message:*\n{message}"
                }
            }
        ]

        if payload_details:
            details_str = "\n".join([f"• *{k}:* {v}" for k, v in payload_details.items()])
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Metadata:*\n{details_str}"
                }
            })

        slack_payload = {"blocks": blocks}
        
        with httpx.Client(timeout=3.0) as client:
            resp = client.post(url, json=slack_payload)
            if resp.status_code in [200, 201]:
                logger.info("Successfully posted alert to Slack channel.")
                return True
            else:
                logger.error(f"Slack webhook endpoint returned HTTP {resp.status_code}: {resp.text}")
                return False
                
    except Exception as e:
        logger.error(f"Failed to transmit Slack webhook: {e}")
        return False
