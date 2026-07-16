"""Turns raw character skill-level data into the `description_value_NN` slot
dicts the skill_rules builders consume.

lootandwaifus stores each level as raw text; encoders hand-numbered its numeric
tokens left-to-right when transcribing fixtures, so the extractor reproduces
exactly that convention. Some encoders skipped non-value numbers (trigger
phrases like "Burst stage 3"); those units carry a per-unit `drop_tokens`
override in their SKILL_VALUE_MANIFESTS, added only where the assembly
verification harness fails (see test_skill_value_assembly.py) — never
speculatively. dotgg levels are already native slot dicts and pass through.
"""
import re

_NUMBER = re.compile(r"\d+(?:\.\d+)?")


def extract_lootandwaifus_slots(level_text, drop_tokens=()):
    dropped = set(drop_tokens)
    tokens = [t for i, t in enumerate(_NUMBER.findall(level_text)) if i not in dropped]
    return {f"description_value_{i + 1:02d}": token for i, token in enumerate(tokens)}


def dotgg_slots(level_dict):
    return {key: value for key, value in level_dict.items() if value != ""}
