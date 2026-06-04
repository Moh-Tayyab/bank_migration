"""
Pipeline stage adapters.

Each adapter wraps an existing component and implements the PipelineStage
protocol: process(data, ctx) -> data. Adapters are thin — they translate
between the component's interface and the pipeline's uniform Dict[str, Any] flow.
"""

from typing import Any, Dict, Optional

from .canonical_store import CanonicalStore
from .models import CanonicalRecord, Record
from .parser import Parser
from .pipeline import PipelineContext, PipelineError
from .rules_engine import RulesEngine
from .schema_mapper import SchemaMapper
from .security import SecurityMasker
from .validator import Validator


class ValidateStage:
    """Validates the record. Raises PipelineError on failure."""

    def __init__(self, validator: Optional[Validator] = None):
        self._validator = validator or Validator()

    def process(self, data: Dict[str, Any], ctx: PipelineContext) -> Dict[str, Any]:
        record = Record(
            data=data,
            record_id=ctx.record_id,
            source_bank=ctx.source_bank,
        )
        result = self._validator.validate(record)
        if not result.is_valid:
            errors = "; ".join(f"{e.field}: {e.message}" for e in result.errors)
            raise PipelineError("validate", errors, ctx.record_id)
        return data


class ParseStage:
    """Parses names, dates, addresses, and currencies in the record."""

    def __init__(self, parser: Optional[Parser] = None):
        self._parser = parser or Parser()

    def process(self, data: Dict[str, Any], ctx: PipelineContext) -> Dict[str, Any]:
        return self._parser.parse_all(data)


class MapStage:
    """Maps source fields to target bank schema."""

    def __init__(self, mapper: Optional[SchemaMapper] = None):
        self._mapper = mapper or SchemaMapper()

    def process(self, data: Dict[str, Any], ctx: PipelineContext) -> Dict[str, Any]:
        record = Record(
            data=data,
            record_id=ctx.record_id,
            source_bank=ctx.source_bank,
            target_bank=ctx.target_bank,
        )
        mapped = self._mapper.map_record(record, ctx.target_bank)
        return mapped.data


class RulesStage:
    """Applies business rules (strip, capitalize, nullify, etc.)."""

    def __init__(self, engine: Optional[RulesEngine] = None):
        self._engine = engine

    def process(self, data: Dict[str, Any], ctx: PipelineContext) -> Dict[str, Any]:
        record = Record(
            data=data,
            record_id=ctx.record_id,
            source_bank=ctx.source_bank,
            target_bank=ctx.target_bank,
        )
        return self._engine.apply(record)


class MaskStage:
    """Masks PII fields. Pure — no audit side effects."""

    def __init__(self, masker: Optional[SecurityMasker] = None):
        self._masker = masker or SecurityMasker()

    def process(self, data: Dict[str, Any], ctx: PipelineContext) -> Dict[str, Any]:
        return self._masker.mask(data, ctx.record_id)


class StoreStage:
    """Stores the canonical record. Side-effect only, passes data through."""

    def __init__(self, canonical: Optional[CanonicalStore] = None):
        self._canonical = canonical or CanonicalStore()

    def process(self, data: Dict[str, Any], ctx: PipelineContext) -> Dict[str, Any]:
        canonical = CanonicalRecord(
            record_id=ctx.record_id,
            raw_data=ctx.raw_data,
            canonical_data=data,
            source_bank=ctx.source_bank,
        )
        self._canonical.store(canonical)
        return data
