# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

## [1.1.0] - 2026-08-14

### Added

- CI workflow validating the agent/command structure (12 agents, 13 commands,
  frontmatter integrity, README counts) on every push and pull request.
- Community files: code of conduct, pull-request template, and a Dependabot
  config that keeps the GitHub Actions used in CI up to date.
- README badges for CI status, latest release, and license.

## [1.0.0] - 2026-07-30

First stable release.

### Added

- 12 agents: 5 opinionated personas (Buffett, Munger, Burry, bull, bear),
  6 fact-gathering analysts (fundamentals, technical, news, macro, risk,
  SEC filings), and a portfolio-manager synthesizer.
- 13 slash commands covering research, portfolio review, rebalancing,
  tax-loss harvesting, cash allocation, stress testing, earnings calendars,
  corporate-action reconciliation, decision journaling, and YouTube signal
  extraction.
- Five-level rating scale (Buy > Overweight > Hold > Underweight > Sell) with
  tax-aware routing across Canadian account types (taxable / TFSA / registered).
- Terminal demo GIF in the README.
- Bootstrap script, example Notion config, and sample portfolio for first-run
  setup. Advisory only; no order execution.

[Unreleased]: https://github.com/haiiibin/claude-multi-agent-investing/compare/v1.1.0...HEAD
[1.1.0]: https://github.com/haiiibin/claude-multi-agent-investing/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/haiiibin/claude-multi-agent-investing/releases/tag/v1.0.0
