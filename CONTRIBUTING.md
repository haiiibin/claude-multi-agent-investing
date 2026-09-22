# Contributing

Thanks for your interest in improving claude-multi-agent-investing. Bug reports,
ideas for new agents or commands, and pull requests are all welcome.

## What this repository is

A set of Claude Code agent definitions (`.claude/agents/`), slash commands
(`.claude/commands/`) and small helper scripts. There is no package to install:
clone the repository and open it in Claude Code to run it.

```bash
git clone https://github.com/haiiibin/claude-multi-agent-investing
cd claude-multi-agent-investing
python scripts/validate_structure.py   # checks that agents, commands and README agree
```

## Pull request guidelines

- Keep changes focused; one concern per PR.
- Run `python scripts/validate_structure.py` before opening the PR.
- If you add or rename an agent or command, update the README tables and counts.
- Update `CHANGELOG.md` under `[Unreleased]`.
- The framework is advisory only. Do not add steps that place orders or move
  money without an explicit confirmation gate.

## Reporting bugs

Open an issue with the command you ran, the agent output you saw, and what you
expected instead. Please strip real account numbers and positions from any
pasted output.
