# Code Style and Architecture

This document is for all collaborators, human and AI. It records the project's
architecture rules, refactoring triggers, changelog discipline, test expectations,
and traps we have already hit.

Daily contributor workflow lives in [`../../CONTRIBUTING.md`](../../CONTRIBUTING.md).
Architecture details live in [`architecture.md`](architecture.md).

---

## Architecture Rules

The project is small, but it handles unstable upstream data. Keep the shape simple
and strict so future game/version adapters do not turn into a pile of special cases.

### File Responsibilities

- `fetch.py` only obtains raw data with sparse checkout. It should not parse game data
  or format output.
- `extract/` resolves raw JSON into JSONL with hashes replaced. It should not write
  human-facing Markdown text.
- `convert.py` formats extracted JSONL into readable `.txt` files. It should not clone
  repositories or read TextMap files directly.
- `cli.py` wires commands together and owns user-facing errors. It should stay thin.
- `docs/` records behavior that is true for the current release. Planned phases must
  be labeled as planned, not described as working features.

### Layering

Allowed direction:

```
cli -> fetch / extract / convert
extract -> extract/base
convert -> extract/base constants only
tests -> public API plus focused private helpers when needed
```

Avoid reverse dependencies. In particular:

- extractors must not call CLI helpers
- converters must not inspect raw repositories
- fetch must not know converter output formats
- docs must not promise behavior that tests or smoke checks cannot support

### Extraction Discipline

- Missing raw data, TextMap files, or expected source directories should fail loudly.
  Never silently produce empty JSONL or `0 files` for a bad input path.
- Keep raw game files out of this repository. `*_raw/`, `*.json`, and `*.jsonl` are
  ignored for a reason.
- Game support must match the public CLI. Stubs for future games are fine, but the CLI
  should reject them clearly until they are implemented and tested.
- Obfuscated upstream keys are version-specific. Keep key constants close to the
  extractor/converter that uses them, and update docs/tests when they change.

## Refactoring Triggers

Extract or split code when any of these becomes true:

- the same parsing or formatting logic appears in two places
- a function grows past roughly 50 lines or has more than three nested levels
- a block has its own state, update rules, and query behavior
- a behavior needs an isolated test but is buried inside a larger command
- a source file approaches roughly 300 lines and has multiple responsibilities

Do not extract for ceremony. A single-use, clear, short block can stay inline.

## Naming and Comments

- Public functions and classes should have concise docstrings explaining what and why.
- Do not write comments that repeat the code. Do comment upstream quirks, version-specific
  keys, legal/data-policy constraints, and counterintuitive behavior.
- Prefer descriptive names over generic helpers like `utils.py` or `helper.py`.
- Keep user-facing error messages concrete: name the missing env var, directory, file,
  or unsupported game.

## Testing

Use `tmp_path` and tiny synthetic JSON fixtures for unit tests. Do not depend on real
raw game data in CI.

Required checks before a release or PR:

```bash
uv run ruff check src/ tests/
uv run pytest
uv run pytest --cov=src/hoyo_story --cov-report=term-missing
uv build
```

Test expectations:

- New pure parsing/formatting helpers need unit tests.
- New CLI behavior needs `typer.testing.CliRunner` coverage for both happy path and
  user-friendly failure path.
- New sparse checkout paths should be tested by monkeypatching git calls, not by cloning
  external repositories in CI.
- Real-data integration checks may live in local-only workflows, but they must not be
  required for CI.

## Changelog and Versioning

Follow SemVer. For releases, keep these in sync:

- `pyproject.toml` project version
- `src/hoyo_story/__init__.py` `__version__`
- `CHANGELOG.md`

Use Keep a Changelog categories where they fit: Added, Changed, Deprecated, Removed,
Fixed, Security. Write entries for users and downstream maintainers, not as copied
commit messages.

## Common Traps

- `uv sync` does not put `hoyo-extract` on PATH in every shell. Public docs should use
  `uv run hoyo-extract ...` unless they explicitly ask users to activate `.venv`.
- Python `fetch` paths and helper scripts must stay aligned. If one supports `--type all`,
  the other must include Talk, Avatar, Material, Weapon, Reliquary, and Readable paths too.
- `merge_text_maps()` can skip missing files for low-level utility use, but extractors
  should validate required TextMap files before writing outputs.
- Genshin misc enrichment needs metadata such as `skillAffix` and `icon`; dropping those
  during generic extraction breaks weapon skills and relic stories later.
- Generated JSONL and `.txt` output belong in local/output or data archive repositories,
  not in this engine repository.
- Legal/risk docs should be framed as project policy and risk reduction, not absolute
  legal conclusions.
