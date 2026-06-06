# Contributing

Thanks for your interest in contributing to `hoyo-story-extractor`!

## Setup

```bash
git clone https://github.com/3aKHP/hoyo-story-extractor.git
cd hoyo-story-extractor
uv sync --extra dev
```

## Development workflow

1. **Fork & branch**: create a feature branch (`feat/your-feature`)
2. **Code**: follow [`docs/dev/style.md`](docs/dev/style.md) and surrounding conventions
3. **Test**: `uv run pytest` — all tests must pass
4. **Lint**: `uv run ruff check src/ tests/` — zero warnings required
5. **Commit**: use [Conventional Commits](https://www.conventionalcommits.org/) — `<type>(<scope>): <subject>`
   - Type: `feat` / `fix` / `refactor` / `docs` / `chore` / `test`
   - Scope: `fetch` / `extract` / `convert` / `ci` / `genshin` / `starrail` / `zzz`
6. **PR**: open against `main`, describe what and why

## Architecture

```
src/hoyo_story/
├── fetch.py          ← clone raw data repositories (sparse checkout)
├── extract/
│   ├── base.py       ← shared logic (hash replacement, TextMap merging)
│   ├── genshin.py    ← Genshin-specific extraction
│   ├── starrail.py   ← Star Rail-specific extraction
│   └── zzz.py        ← ZZZ stub (Phase 6)
├── convert.py        ← JSONL → .txt conversion
└── cli.py            ← typer CLI
```

The core design principle: **`fetch.py` downloads, `extract/*.py` resolves hashes into JSONL, `convert.py` formats into readable `.txt`.** Each game's extractor inherits from `BaseExtractor` and only overrides game-specific fields.

## Adding a new extractor

1. Create `extract/yourgame.py` extending `BaseExtractor`
2. Set `game_name`, `text_map_paths`, `quest_data_path` class attributes
3. Override `load_text_map()` if the game uses a non-standard hash scheme
4. Add CLI integration in `cli.py`'s `_get_extractor()`
5. Write tests in `tests/`

## Data policy

**Never commit raw game files** (`.json`, `.jsonl`, `.bin`, `.asset`) to this repository or any data archive. The `.gitignore` already enforces this, but be mindful when adding new file types.

Extracted `.txt` output goes to separate data archive repositories, never to this engine repo.

## Questions?

Open an issue or discussion.
