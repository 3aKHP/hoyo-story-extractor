# Starrail Source Repository Structure

This note records a source-tree audit of
`https://gitlab.com/Dimbreath/turnbasedgamedata.git` so future Starrail
extractors do not mistake thin config tables for the real text sources.

Audit snapshot:

- local repo: `starrail_raw`
- upstream remote: `https://gitlab.com/Dimbreath/turnbasedgamedata.git`
- audited commit: `14c1d18f`
- branch: `main`

## Top-Level Layout

The upstream tree is much wider than the current sparse checkout:

| Top-level path | File count | Notes |
| --- | ---: | --- |
| `Config/` | 113,118 | Runtime graph/config JSON. Many dialogue flows live here. |
| `Story/` | 5,358 | Performance/discussion story graphs. Some contain option talks. |
| `Stages/` | 2,826 | Stage output data, mostly not reader-facing text. |
| `ExcelOutput/` | 2,065 | Main structured tables. Most text catalog data starts here. |
| `TextMap/` | 29 | Language text maps. Some languages are split into numbered parts. |

The stale sparse checkout that exposed the avatar-shell bug only contained a
narrow subset:

```text
TextMap/TextMapCHS.json
TextMap/TextMapMainCHS.json
ExcelOutput/MainMission.json
ExcelOutput/SubMission.json
ExcelOutput/MissionChapterConfig.json
ExcelOutput/TalkSentenceConfig.json
ExcelOutput/AvatarConfig.json
ExcelOutput/ItemConfig.json
ExcelOutput/ItemConfigBook.json
ExcelOutput/ItemConfigEquipment.json
ExcelOutput/ItemConfigRelic.json
Config/Level/Mission/
Config/Level/TrainVisitor/
```

Do not treat any existing local sparse checkout as the full source map until it
has been compared with the current `STARRAIL_PATHS`.

## TextMap Layout

Text lives behind several indirection styles, so a new extractor must inspect
the field shape before choosing a resolver.

Observed text forms:

- Hash object: `{"Hash": 123}` resolved directly against TextMap.
- Stable hash of a string field value, used by some ExcelOutput fields such as
  `MissionChapterConfig.ChapterName`.
- `TalkSentenceID` indirection through `ExcelOutput/TalkSentenceConfig.json`.
- Graph tasks under `OnStartSequece` / `TaskList` where text IDs are nested in
  action payloads.

Language files are not perfectly uniform. For example, `TextMapKR.json` does
not exist in the audited tree; Korean base TextMap is split as
`TextMapKR_0.json` and `TextMapKR_1.json`. Russian and Thai also have split
base maps. Avoid assuming every language is exactly `TextMap{lang}.json` plus
`TextMapMain{lang}.json`.

## High-Value Text Sources

### Quests And Mission Dialogue

Primary structured tables:

| File | Role | Important fields |
| --- | --- | --- |
| `ExcelOutput/MainMission.json` | Main mission metadata | `MainMissionID`, `Name`, `ChapterID` |
| `ExcelOutput/SubMission.json` | Mission objectives/descriptions | `SubMissionID`, `TargetText`, `DescrptionText` |
| `ExcelOutput/MissionChapterConfig.json` | Chapter labels | `ID`, `ChapterName`, `StageName`, `ChapterDesc` |
| `ExcelOutput/TalkSentenceConfig.json` | Dialogue sentence lookup | `TalkSentenceID`, `TalkSentenceText`, speaker/name fields when present |

Runtime hierarchy and embedded dialogue:

- `Config/Level/Mission/<main_id>/MissionInfo_<main_id>.json`
- `Config/Level/Mission/<main_id>/MissionInfo_<main_id>.partial.json`
- `MissionJsonPath` entries pointing at sub-mission graph JSON
- `Config/Level/Mission/**/{Talk,Act,Drop,Battle,...}/*.json`

Important trap: real mission files often keep the detailed `SubMissionList` in
the sibling `.partial.json`, while the primary file may only have
`StartSubMissionList` / `FinishSubMissionList`.

### Talks And World Dialogue

The current sparse paths cover only part of the dialogue surface. Additional
upstream directories exist and are likely text-bearing:

| Path | File count in audited tree | Notes |
| --- | ---: | --- |
| `Config/Level/Mission/` | 29,996 | Mission, quest, drop, talk, battle, and act graphs. |
| `Config/Level/NPCDialogue/` | 6,642 | NPC standing/world dialogue graphs. |
| `Config/Level/PropDialogue/` | 2,750 | Object/gadget dialogue graphs. |
| `Config/Level/MunicipalChatConfig/` | 1,503 | Ambient municipal chat; uses `TalkSentenceID`. |
| `Config/Level/RogueDialogue/` | 612 | Simulated Universe/rogue dialogue graphs. |
| `Config/Level/Tutorial/` | 1,350 | Tutorial UI/guide text graphs. |

Several paths currently listed or used as assumptions are not present in the
audited upstream tree:

- `Config/Level/Story/`
- `Config/Level/Activity/`
- `Config/Level/Message/`

Phone/messages are not under `Config/Level/Message/`; they are structured in
`ExcelOutput/Message*.json`.

### Character Profiles And Voices

`ExcelOutput/AvatarConfig.json` is only a basic avatar config table. It is not
the character profile source.

Actual character archive sources:

| File | Role | Important fields |
| --- | --- | --- |
| `ExcelOutput/StoryAtlas.json` | Character details and stories | `AvatarID`, `StoryID`, `Story`, `Unlock` |
| `ExcelOutput/StoryAtlasTextmap.json` | Story section titles | `StoryID`, `StoryName` |
| `ExcelOutput/VoiceAtlas.json` | Character voice titles and text | `AvatarID`, `VoiceID`, `VoiceTitle`, `Voice_M`, `SortID` |
| `ExcelOutput/AvatarAtlas.json` | Character atlas metadata | `AvatarID`, `CV_CN`, `CV_JP`, `CV_KR`, `CV_EN`, `CampID` |
| `ExcelOutput/AvatarCamp.json` | Camp/faction metadata | camp IDs and labels |
| `ExcelOutput/AvatarBaseType.json` | Path/base type labels | path IDs and labels |
| `ExcelOutput/AvatarComefrom.json` | Acquisition/source labels | `Desc`, `GotoID`, `GotoParam` |

Example mapping:

- `StoryAtlas.AvatarID = 1001` is March 7th.
- `StoryID = 1` maps through `StoryAtlasTextmap` to `角色详情`.
- `StoryID = 2..5` map to `角色故事·一` through `角色故事·四`.
- `StoryID = 21..22` hold alternate-path profile text such as March 7th's
  Xianzhou form.
- The player avatar uses `StoryID = 11..16`, with titles like `关于「你」`
  and `你的「故事」•一`.

### Phone Messages

Phone/message data is in `ExcelOutput`, not `Config/Level/Message/`.

| File | Role | Important fields |
| --- | --- | --- |
| `MessageContactsConfig.json` | Contacts | `ID`, `Name`, `SignatureText`, `ContactsType`, `ContactsCamp` |
| `MessageGroupConfig.json` | Contact-to-section grouping | `ID`, `MessageContactsID`, `MessageSectionIDList` |
| `MessageSectionConfig.json` | Message section starts | `ID`, `StartMessageItemIDList`, `IsPerformMessage` |
| `MessageItemConfig.json` | Message nodes | `ID`, `Sender`, `ItemType`, `MainText`, `OptionText`, `NextItemIDList`, `SectionID` |
| `MessageItemTextOverride.json` | Conditional overrides | `ItemID`, `MainText`, `Conditions` |

This is a graph-like conversation format and should not be parsed as simple
flat rows.

### Books, Items, Equipment, And Relics

Current misc extraction uses item-style tables, but richer text exists in more
specific tables.

| Area | Strong source candidates | Notes |
| --- | --- | --- |
| General items | `ItemConfig.json`, `ItemConfigAvatar.json`, `ItemComefrom*.json` | Item names/descriptions and acquisition text. |
| Books | `LocalbookConfig.json`, `BookSeriesConfig.json`, `BookSeriesWorld.json` | `LocalbookConfig.BookContent` contains full book text. |
| Light cones | `EquipmentConfig.json`, `EquipmentSkillConfig.json`, `EquipmentAtlas.json` | Use equipment tables for stronger names/skills/atlas state. |
| Relics | `RelicDataInfo.json`, `RelicSetConfig.json`, relic affix tables | Some relic story fields are not plain top-level hash objects; inspect resolver shape first. |

### Lore, NPC, And Enemy Atlas

Other reader-facing sources found in `ExcelOutput`:

| File | Role |
| --- | --- |
| `NounAtlas.json` | Glossary/lore terms and descriptions. |
| `AtlasConfig.json`, `AtlasUnlock*.json` | Atlas categories/unlock text. |
| `NPCMonsterData.json` | NPC monster display names. |
| `MonsterConfig.json` | Monster names, introductions, strategy text. |
| `MonsterGuide*.json` | Enemy guide phases, tags, and strategy descriptions. |
| `NPCData.json`, `StoryCharacter.json` | Mostly entity/path mapping; not enough by itself for reader-facing text. |

## Current Sparse Coverage

The Starrail sparse path list now includes the verified sources needed by the
current public `quests`, `talks`, `avatars`, and `misc` extractors:

```text
TextMap/
ExcelOutput/MainMission.json
ExcelOutput/SubMission.json
ExcelOutput/MissionChapterConfig.json
ExcelOutput/TalkSentenceConfig.json
ExcelOutput/AvatarConfig.json
ExcelOutput/AvatarAtlas.json
ExcelOutput/StoryAtlas.json
ExcelOutput/StoryAtlasTextmap.json
ExcelOutput/VoiceAtlas.json
ExcelOutput/AvatarComefrom.json
ExcelOutput/AvatarCamp.json
ExcelOutput/AvatarBaseType.json
ExcelOutput/ItemConfig*.json
ExcelOutput/ItemPlayerCard.json
Config/Level/Mission/
Config/Level/TrainVisitor/
Config/Level/NPCDialogue/
Config/Level/PropDialogue/
Config/Level/MunicipalChatConfig/
Config/Level/Tutorial/
Config/Level/RogueDialogue/
Story/Discussion/
Story/Mission/
```

The following stale or invalid paths were found during the audit and should not
be reintroduced without a fresh upstream check:

```text
TextMap/TextMapKR.json
ExcelOutput/AvatarPlayerTitleConfig.json
Config/Level/Story/
Config/Level/Activity/
Config/Level/Message/
```

Text-bearing sources that remain planned but are not yet part of the public
output model include:

```text
ExcelOutput/Message*.json          # phone messages
ExcelOutput/LocalbookConfig.json   # full book contents
ExcelOutput/BookSeriesConfig.json  # book series metadata
ExcelOutput/Equipment*.json        # richer light cone data
ExcelOutput/Relic*.json            # richer relic data
ExcelOutput/NounAtlas.json         # glossary/lore
ExcelOutput/Monster*.json          # enemy atlas and guides
```

Some local checkouts may be older than `src/hoyo_story/fetch.py`; always compare
`git sparse-checkout list` with the current source code before trusting local
raw data.

## Guardrails For Future Extractors

Before adding or changing a Starrail extractor:

1. Inventory the upstream tree with `git ls-tree -r --name-only HEAD -- <path>`.
2. Verify every sparse path exists upstream, including language-specific
   TextMap variants.
3. Sample at least one real JSON row and identify its text indirection style:
   hash object, stable hash, `TalkSentenceID`, or graph action payload.
4. Check whether a thin config table has a companion atlas/textmap/detail table.
   `AvatarConfig.json` vs `StoryAtlas.json` is the cautionary example.
5. Keep raw JSON out of this repository; commit only extractor code, synthetic
   fixtures, and documentation.
6. For generated output, audit both reported write count and actual filesystem
   file count to catch duplicate-name overwrites.
7. Prefer small source-specific parsers over assuming all `ExcelOutput` files
   share the same schema.
