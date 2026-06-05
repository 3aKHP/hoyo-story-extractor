# Changelog

All notable changes to this project will be documented in this file.

## [0.1.0] — 2026-06-05

### Added

- Project skeleton with `uv`/`hatchling` build, `typer` CLI, `pytest` + `ruff`
- `fetch.py`: sparse checkout of raw data repositories via git subprocess
- `extract/base.py`: `replace_hashes()` recursive hash-to-text resolver, `merge_text_maps()`, `BaseExtractor` with default extraction pipeline
- `extract/genshin.py`: `GenshinExtractor` supporting quests, talks, avatars, and misc (materials/weapons/relics)
- `extract/starrail.py`: `StarrailExtractor` stub (Phase 5)
- `extract/zzz.py`: `ZZZExtractor` stub (Phase 6)
- `convert.py`: JSONL-to-.txt converters for all data types (quests, talks, avatars, misc)
- `cli.py`: `hoyo-extract` CLI with `fetch`, `extract`, `convert`, `pipeline` commands
- `scripts/clone_genshin_raw.ps1`: Windows PowerShell sparse-clone helper
- Full v6.6 data format support (adapted obfuscated key names for Talk types)
- CLI smoke tests and user-friendly failure coverage
- 45 unit tests covering all modules

### Changed

- Align Python `fetch` sparse checkout paths with the full Genshin extraction pipeline
- Require explicit raw data/TextMap source files instead of silently producing empty output
- Document `uv run hoyo-extract ...` as the copy-paste-safe local CLI invocation
- Public CLI now rejects planned-but-unimplemented games with a clear message
- `.gitignore` excludes all raw game data formats (`.json`, `.jsonl`)
