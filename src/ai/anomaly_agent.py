from typing import List, Dict, Any, Optional
import json
import logging
from src.audit_logger import AuditLogger, AuditEntry
from src.config import settings
from openai import OpenAI
from openai_agents import Agent, AgentRuntime

logger = logging.getLogger(__name__)

class AnomalyDetectionAgent:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.openai_api_key
        # Route OpenAI SDK to Gemini's OpenAI-compatible endpoint
        self.client = OpenAI(
            api_key=self.api_key,
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
        )
        
        # Define the AI Guardian Agent using the OpenAI Agents SDK, but targeting Gemini 2.0 Flash
        self.agent = Agent(
            name="AnomalyGuardianAgent",
            instructions="You are a Senior Quality Assurance Agent for a Bank Migration Platform. Your goal is to detect data quality anomalies, failure patterns, and security risks in audit logs. You must output ONLY valid JSON.",
            model="gemini-2.0-flash",
        )
        self.runtime = AgentRuntime(self.agent)

    def analyze_audit_trail(self, migration_id: str) -> Dict[str, Any]:
        """
        Reads the audit log and identifies anomalies using the OpenAI Agents SDK.
        """
        log_path = settings.log_dir / f"audit_{migration_id}.jsonl"
        
        try:
            trail = AuditLogger.read_trail(str(log_path))
            if not trail:
                return {"status": "no_data", "message": "No audit trail found for this migration."}
            
            trail_summary = []
            for entry in trail:
                trail_summary.append(f"[{entry.timestamp}] {entry.event}: {entry.details}")
            
            full_log = "\n".join(trail_summary)
            
            prompt = f"""
            Analyze the following audit log for migration {migration_id} and detect anomalies, unexpected failure patterns, or data quality issues.
            
            LOG DATA:
            {full_log}
            
            If you find an issue, provide:
            1. The anomaly detected.
            2. The suspected root cause.
            3. A technical recommendation for a fix.
            
            Return the result in JSON format:
            {{
                "has_anomalies": true/false,
                "anomalies": [
                    {{ "issue": "...", "cause": "...", "recommendation": "..." }}
                ],
                "overall_health": "Healthy|Warning|Critical"
            }}
            
            Return ONLY the raw JSON object.
            """
            
            response = self.runtime.run(prompt)
            text = response.content.strip()
            
            # Clean markdown blocks if present
            if text.startswith("```"):
                text = text.split("\n", 1)[1].rsplit("\n", 1)[0].strip()
                if text.startswith("json"):
                    text = text[4:].strip()

            return json.loads(text)
            
        except Exception as e:
            logger.error(f"Anomaly detection failed: {str(e)}")
            return {"status": "error", "error": str(e)}
