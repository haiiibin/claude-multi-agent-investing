#!/usr/bin/env python3
"""Validate the agent/command file structure this framework ships.

Checks, in order:
1. `.claude/agents/` holds exactly the expected number of agent definitions,
   each with YAML frontmatter whose `name:` matches its filename.
2. `.claude/commands/` holds exactly the expected number of slash commands,
   each with a `description:` in its frontmatter.
3. The README's advertised agent/command counts match the actual files.

Exits non-zero on the first failure so CI blocks structural drift.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
AGENTS_DIR = ROOT / ".claude" / "agents"
COMMANDS_DIR = ROOT / ".claude" / "commands"
README = ROOT / "README.md"

EXPECTED_AGENTS = 12
EXPECTED_COMMANDS = 13

errors: list[str] = []


def frontmatter(path: Path) -> dict[str, str]:
    """Parse the simple `key: value` pairs of a `---` frontmatter block."""
    text = path.read_text(encoding="utf-8")
    match = re.match(r"\A---\n(.*?)\n---\n", text, re.DOTALL)
    if not match:
        return {}
    fields: dict[str, str] = {}
    for line in match.group(1).splitlines():
        if ":" in line and not line.startswith((" ", "\t")):
            key, _, value = line.partition(":")
            fields[key.strip()] = value.strip()
    return fields


agents = sorted(AGENTS_DIR.glob("*.md"))
if len(agents) != EXPECTED_AGENTS:
    errors.append(f"expected {EXPECTED_AGENTS} agents, found {len(agents)}")
for path in agents:
    fm = frontmatter(path)
    if not fm:
        errors.append(f"{path.name}: missing frontmatter block")
        continue
    if fm.get("name") != path.stem:
        errors.append(f"{path.name}: frontmatter name {fm.get('name')!r} != filename stem")
    if not fm.get("description"):
        errors.append(f"{path.name}: missing description")

commands = sorted(COMMANDS_DIR.glob("*.md"))
if len(commands) != EXPECTED_COMMANDS:
    errors.append(f"expected {EXPECTED_COMMANDS} commands, found {len(commands)}")
for path in commands:
    fm = frontmatter(path)
    if not fm.get("description"):
        errors.append(f"{path.name}: missing frontmatter description")

readme = README.read_text(encoding="utf-8")
if f"{len(agents)} agents" not in readme:
    errors.append(f"README does not say '{len(agents)} agents'")
if f"{len(commands)} slash commands" not in readme:
    errors.append(f"README does not say '{len(commands)} slash commands'")

if errors:
    for line in errors:
        print(f"FAIL: {line}")
    sys.exit(1)

print(f"OK: {len(agents)} agents, {len(commands)} commands, README counts match")
