"""
utils/pokemon_validator.py

Uses two JSON files — no PokeAPI, no async, instant startup.

fixed.json:        display_name -> base_name  (1251 entries, all forms/regionals)
officialname.json: base_name -> [multilingual aliases]
"""

import json
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
FIXED_PATH = DATA_DIR / "fixed.json"
OFFICIAL_PATH = DATA_DIR / "officialname.json"


class PokemonValidator:
    def __init__(self):
        self._alias_to_key: dict[str, str] = {}
        self._ready = False

    def load(self):
        try:
            with open(FIXED_PATH, "r", encoding="utf-8") as f:
                fixed: dict[str, str] = json.load(f)
            with open(OFFICIAL_PATH, "r", encoding="utf-8") as f:
                official: dict[str, list[str]] = json.load(f)

            # Step 1: All fixed.json keys are valid
            for display_name in fixed.keys():
                key = display_name.lower()
                self._alias_to_key[key] = key

            # Step 2: Build base_name -> list of fixed keys
            base_to_keys: dict[str, list[str]] = {}
            for display_name, base_name in fixed.items():
                base_to_keys.setdefault(base_name.lower(), []).append(display_name.lower())

            # Step 3: Map multilingual aliases -> canonical fixed key
            for base_name, aliases in official.items():
                fixed_keys = base_to_keys.get(base_name.lower(), [])
                if not fixed_keys:
                    continue
                canonical = fixed_keys[0]
                for alias in aliases:
                    a = alias.lower().strip()
                    if a and a not in self._alias_to_key:
                        self._alias_to_key[a] = canonical

            self._ready = True
            print(f"[VALIDATOR] Loaded {len(self._alias_to_key)} names/aliases")

        except Exception as e:
            print(f"[VALIDATOR ERROR] {e}")

    def is_valid(self, name: str) -> bool:
        return name.strip().lower() in self._alias_to_key

    def normalize(self, name: str) -> str:
        return self._alias_to_key.get(name.strip().lower(), name.strip().lower())

    def display(self, normalized: str) -> str:
        return normalized.title()

    def validate_bulk(self, names: list[str]) -> tuple[list[str], list[str]]:
        valid, invalid, seen = [], [], set()
        for n in names:
            n = n.strip()
            if not n:
                continue
            if self.is_valid(n):
                norm = self.normalize(n)
                if norm not in seen:
                    valid.append(norm)
                    seen.add(norm)
            else:
                invalid.append(n)
        return valid, invalid

    @property
    def ready(self) -> bool:
        return self._ready


validator = PokemonValidator()