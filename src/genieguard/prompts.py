SPEC_SCHEMA_SNIPPET = """
{
  "meta": {"name": "string", "seed": "int", "version": "0.1"},
  "map": {
    "w": "int 8..20",
    "h": "int 8..20",
    "walls": [[x, y], ...],
    "flags": {"A": [x, y], "B": [x, y]}
  },
  "spawns": {"A": [x, y], "B": [x, y]},
  "rules": {"max_turns": "int 30..120", "win": "capture_flag"},
  "params": {"move_cost": 1, "capture_range": 0, "deadlock_repeat": "int 4..10"}
}
""".strip()


SPEC_SYSTEM_PROMPT = f"""
You output only valid JSON object for GameSpec v0.1.
No markdown, no explanation text.
Constraints:
- Ensure map has at least one path between each spawn and enemy flag.
- Keep coordinates inside map.
- Include all mandatory fields from this schema:
{SPEC_SCHEMA_SNIPPET}
""".strip()


PATCH_SYSTEM_PROMPT = """
You are PatchSynth. Select one minimal patch candidate and explain why in one short sentence.
You must return JSON:
{
  "selected_index": int,
  "rationale": "string",
  "expected_effect": {"deadlock_rate":"down|same", "win_skew":"down|same", "exploit_dominance":"down|same"}
}
""".strip()
