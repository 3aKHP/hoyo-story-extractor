# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

### Added

- Genshin 7.2 plaintext CodexQuest fields, semantic task titles and chapter
  metadata, with automatic detection and explicit `--data-version 7.2`.
- Three earlier obfuscated Talk layouts retained in the 7.2 snapshot.
- Synthetic regression tests for the 7.2 task schema, speaker names, retained
  Talk layouts, and duplicate avatar display names.

### Fixed

- Talk speaker names accept plaintext name hashes and use the NPC table when
  a dialogue omits its display name. Unresolved NPC names remain unnamed.
- Avatar output uses sequence-prefixed filenames so records sharing a display
  name retain separate files.

## [0.3.0] — 2026-08-13

### Added

- **Genshin 7.0 (CNRELWin7.0.0) support** — upstream re-obfuscates CodexQuest
  field names on every major version; extraction is now version-aware:
  - `extract/base.py`: `QUEST_KEY_MAPS` registers the quest key map for
    6.6 / 6.7 / 7.0; `resolve_quest_keys()` and `detect_quest_version()`
    select the right map, with auto-detection from quest JSON top-level keys
  - `convert.py`: `convert_quests()` accepts `data_version` (default:
    auto-detect), and reads all quest fields through the resolved key map
  - `cli.py`: `convert` / `pipeline` gain `--data-version` for explicit
    override when auto-detection fails
  - Tests: `TestQuestKeyMaps` (mapping + detection), `TestConvertV70`
    (7.0 quest conversion with auto-detect / explicit version / failure path),
    `TestConvertTalksV70` (7.0 talk formats + Group skip), Genshin TextMap
    +512 offset alias tests
- Verified against real CNRELWin7.0.0 data: 503 quests, 55,925 talk files,
  165 avatars.
- **Genshin Talk v7.0 adaption** — upstream made two breaking changes to the
  Talk pipeline in 6.7/7.0, both now handled:
  - TextMap reorganization: Talk dialogue content moved from
    `TextMap_Medium{lang}.json` into `TextMap{lang}.json` with every key
    shifted by +512. `GenshinExtractor.load_text_map()` registers a `K - 512`
    alias for each CHS key (`setdefault`, direct hits win), so Talk content
    hashes resolve without affecting quest/avatar lookups.
  - Type B key re-obfuscation: `IOEDPLCPFFB/DGGDDIMMIDO/HJJLLECCCPI` became
    `PFALHAKIILD/LFGCLNLPAPB/OACNIBLFFDI` in 7.0. `convert_talks()` now
    detects the format per line via `_TALK_FORMATS` (6.6 Type A/B, 7.0 new
    keys, plain `dialogList` files, and the new 7.0 Activity format
    `GDDPNNHLGBL/EENIFNIGHCH/DMIFDJDEFAL`), and skips condition-only Group
    files.

### Changed

- Version bumped to 0.3.0 (was inconsistently reported as 0.1.0 in
  `pyproject.toml` / `__init__.py` while CHANGELOG already tracked 0.2.0).

## [0.2.0] — 2026-06-05

### Added

- **Starrail (Honkai: Star Rail) full extraction pipeline** — Phase 5 complete
  - `extract/starrail.py`: `StarrailExtractor` with `get_stable_hash()` algorithm,
    `load_text_map()`, `_load_talk_sentence_map()`, `extract_quests()`,
    `extract_talks()` (with `_parse_on_sequence()` / `_merge_sessions()`),
    `extract_avatars()`, `extract_misc()`
  - `convert.py`: `convert_starrail_quests()`, `convert_starrail_talks()`,
    `convert_starrail_avatars()`, `convert_starrail_misc()`
  - `fetch.py`: expanded `STARRAIL_PATHS` covering TextMap, ExcelOutput,
    and Config/Level directories
  - `cli.py`: `starrail` registered in `IMPLEMENTED_GAMES` and `_get_extractor()`,
    game-specific converter selection in `pipeline`
  - Unit tests covering stable hash, TextMap merge, TalkSentenceConfig
    loading, quest/talk/avatar/misc extraction + conversion, and pipeline smoke
- `docs/dev/starrail-source-structure.md`: upstream TurnBasedGameData source
  structure audit covering real text sources, sparse checkout gaps, and future
  extractor guardrails

### Changed

- Starrail `.txt` conversion now writes cleaner, Genshin-like products:
  mission dialogue is embedded in quest files, markup escapes are normalized,
  technical asset/config path fields are omitted, and missions with no readable
  body are skipped instead of emitted as `(empty mission)`. Starrail avatar
  filenames now include a sequence prefix so duplicate display names do not
  overwrite each other.
- Starrail avatars now merge real profile and voice sources from
  `StoryAtlas.json`, `StoryAtlasTextmap.json`, `VoiceAtlas.json`, and
  `AvatarAtlas.json` instead of relying on the thin `AvatarConfig.json` table.
- Starrail avatar and misc converters now skip metadata-only records that have
  no reader-facing description, profile, voice line, or story body.
- Starrail sparse checkout paths now use the verified upstream structure:
  `TextMap/` as a whole, real avatar/profile/voice atlas files, and additional
  dialogue graph directories such as `NPCDialogue`, `PropDialogue`,
  `MunicipalChatConfig`, `RogueDialogue`, and `Story/Discussion`.
- `pipeline --type quests|talks|avatars|misc` now writes into the same product
  layout as `--type all`: `<output_dir>/<type>/`, with misc categories under
  `<output_dir>/misc/<category>/`.
- `test_cli.py`: `test_unimplemented_game_is_rejected_without_traceback` now
  uses `zzz` instead of `starrail` (since starrail is now implemented)

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
