from typing import List, Dict, Any, Optional
import json
import logging
import re
from openai import OpenAI
from openai_agents import Agent, AgentRuntime
from src.models import BankSchema, MappingRule
from src.registry import BankRegistry
from src.config import settings

logger = logging.getLogger(__name__)

MAX_USER_INPUT_LENGTH = 5000


def _sanitize_input(text: str) -> str:
    text = text[:MAX_USER_INPUT_LENGTH]
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)
    text = re.sub(r'(?i)ignore\s+(previous|above|all)\s+instructions', '[filtered]', text)
    text = re.sub(r'(?i)system\s*:', '[filtered]', text)
    text = re.sub(r'(?i)you\s+are\s+now', '[filtered]', text)
    return text

class SchemaIntelligenceAgent:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.openai_api_key
        self.registry = BankRegistry()
        
        # Define the AI Agent using the OpenAI Agents SDK, but targeting Gemini 2.0 Flash
        self.agent = Agent(
            name="SchemaMapperAgent",
            instructions="You are a Senior Fintech Data Engineer. Your goal is to map UN Wallet source data to target bank schemas with 100% precision. You must output ONLY valid JSON.",
            model="gemini-2.0-flash",
        )
        self.runtime = AgentRuntime(self.agent)

    def suggest_mapping(self, source_bank: str, target_bank: str, target_docs: str) -> Dict[str, Any]:
        """
        Uses the OpenAI Agents SDK to analyze target bank documentation and suggest a mapping.
        """
        source_schema = self.registry.get_schema(source_bank)
        if not source_schema:
            raise ValueError(f"Source bank {source_bank} not found in registry.")

        safe_docs = _sanitize_input(target_docs)
        safe_target = _sanitize_input(target_bank)

        prompt = f"""
        SOURCE SCHEMA (UN Wallet):
        {source_schema.model_dump_json(indent=2)}

        TARGET BANK REQUIREMENTS:
        {safe_docs}

        Generate a JSON object for target bank '{safe_target}' following this exact structure:
        {{
            "bank_name": "{target_bank}",
            "version": "1.0.0",
            "fields": {{ "target_field": "description" }},
            "mappings": [
                {{ "source_field": "source_field_name", "target_field": "target_field_name", "transform": "none|split_name|format_date" }}
            ],
            "masking_rules": {{ "field_name": "mask_type" }}
        }}
        Return ONLY the JSON object.
        """
        
        # Execute through the Agent Runtime
        response = self.runtime.run(prompt)
        text = response.content.strip()
        
        # Clean markdown blocks if present
        if text.startswith("```"):
            text = text.split("\n", 1)[1].rsplit("\n", 1)[0].strip()
            if text.startswith("json"):
                text = text[4:].strip()

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            logger.error(f"Agent returned invalid JSON: {text}")
            raise RuntimeError("AI Agent failed to generate a valid JSON schema.")

    def apply_suggestion(self, suggestion: Dict[str, Any]) -> str:
        schema = BankSchema(
            bank_name=suggestion["bank_name"],
            version=suggestion["version"],
            fields=suggestion["fields"],
            mappings=[MappingRule(**m) for m in suggestion["mappings"]],
            masking_rules=suggestion["masking_rules"],
        )
        return self.registry.register_bank(suggestion["bank_name"], schema)
