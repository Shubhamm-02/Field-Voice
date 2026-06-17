from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from backend.app.models import Equipment, MaintenanceRecord, Procedure

ROOT = Path(__file__).resolve().parents[3]
SEED_PATH = ROOT / "data" / "domain_seed.json"


class DomainCatalog:
    def __init__(
        self,
        equipment: list[Equipment],
        maintenance: list[MaintenanceRecord],
        procedures: list[Procedure],
    ) -> None:
        self.equipment = equipment
        self.maintenance = maintenance
        self.procedures = procedures
        self.equipment_by_code = {item.code: item for item in equipment}

    @property
    def vocabulary_prompt(self) -> str:
        terms: list[str] = []
        for item in self.equipment:
            terms.extend([item.code, item.name, *item.vocabulary])
        for procedure in self.procedures:
            terms.append(procedure.name)
        return ", ".join(sorted(set(terms)))


@lru_cache
def load_domain_catalog() -> DomainCatalog:
    payload = json.loads(SEED_PATH.read_text())
    return DomainCatalog(
        equipment=[Equipment(**item) for item in payload["equipment"]],
        maintenance=[MaintenanceRecord(**item) for item in payload["maintenance_history"]],
        procedures=[Procedure(**item) for item in payload["procedures"]],
    )

