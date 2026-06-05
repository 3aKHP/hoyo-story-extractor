# hoyo-story-extractor

本文件是给 Codex 的项目级说明。它总结了这个仓库的工作方式、必须同步的文件、
数据红线和容易踩的坑。

## 项目概况

- 项目名：`hoyo-story-extractor`
- 仓库：`3aKHP/hoyo-story-extractor`
- 目标：从 HoYoverse 社区 datamine raw data 中提取剧情文本，产出纯 `.txt`
  文件供知识库、检索和 NLP 数据集使用
- 当前公开 CLI：只支持 `genshin`
- 后续阶段：`starrail` / `zzz` 保留代码桩，但未实现前不能在 CLI 中伪装可用

## 工作方式

- 动手前先读 `README.md`、`CONTRIBUTING.md`、`docs/dev/style.md`、相关源码和测试。
- 只改当前任务需要的文件；发现相邻问题可以记录或小范围修补，不做顺手大重构。
- 没有明确要求时，不主动 commit、push、merge。
- 需要提交时，使用 Conventional Commits。
- 用户可见行为变化时，同步 README、相关 docs、CHANGELOG 和测试。
- 做 PR review 时，只看最新 head、checks 和日志，不依赖旧结论。

## 架构纪律

详细规则见 `docs/dev/style.md`。核心边界：

- `fetch.py` 只负责 sparse checkout raw data，不解析、不转换。
- `extract/` 负责 raw JSON -> 已替换哈希的 JSONL，不写人类可读 `.txt`。
- `convert.py` 负责 JSONL -> `.txt`，不读取 TextMap、不 clone 仓库。
- `cli.py` 只做命令编排和用户友好错误提示，保持薄层。
- `docs/` 只能描述当前 release 真实可用的行为；计划中的阶段必须标成 planned。

允许依赖方向：

```
cli -> fetch / extract / convert
extract -> extract/base
convert -> extract/base constants only
tests -> public API plus focused private helpers when needed
```

## 数据政策

- 绝不提交 raw game data 或中间产物：`*_raw/`、`*.json`、`*.jsonl`、本地输出目录都应保持忽略。
- `genshin_raw/`、`local_dev/`、`local_prod/` 只作本机验证，不进入 commit。
- GitHub/CI 中 raw JSON 和 JSONL 只能出现在临时目录。
- 数据归档仓库只放生成后的 `.txt`，不要混进提取引擎仓库。
- 合规/DMCA 文档用风险说明和项目政策口吻，不写绝对法律结论。

## 版本与文档同步

版本号变更时同步：

- `pyproject.toml`
- `src/hoyo_story/__init__.py`
- `CHANGELOG.md`

行为或命令变化时检查：

- `README.md`
- `docs/user/installation.md`
- `docs/user/usage.md`
- `docs/dev/testing.md`
- `CONTRIBUTING.md`
- `.github/workflows/ci.yml`

新增公开入口、CLI 错误路径、sparse checkout 路径或数据格式适配时必须补测试。

## 测试与验证

常用命令：

```bash
uv run ruff check src/ tests/
uv run pytest
uv run pytest --cov=src/hoyo_story --cov-report=term-missing
uv build
uv run hoyo-extract --help
```

测试要求：

- 使用 `tmp_path` 和极小 synthetic JSON fixture，不在 CI 依赖真实 raw data。
- 新 CLI 行为要覆盖 happy path 和 failure path，且 failure path 不应 traceback。
- sparse checkout 逻辑用 monkeypatch 捕获 git 命令参数，不在单元测试里 clone 外部仓库。
- 真实 v6.6 raw data 验证只能作为本地或专门集成检查，不作为默认 CI 前提。

## 已知陷阱

- `uv sync` 后普通 shell 未必能直接运行 `hoyo-extract`；公开文档应使用
  `uv run hoyo-extract ...`。
- Python `fetch` 的 sparse paths 必须和 `scripts/clone_genshin_raw.ps1` 保持一致。
  支持 `--type all` 就必须包含 Talk、Avatar、Material、Weapon、Reliquary 和 Readable。
- 缺 TextMap、raw 目录或 source JSON 时必须明确失败，不能产出空 JSONL 或 `0 files`。
- 未实现游戏不要暴露成可运行能力；CLI 应清楚拒绝 `starrail` / `zzz` 直到实现并测试。
- Genshin misc enrichment 需要保留 `skillAffix` 和 `icon`，否则武器技能和圣遗物故事会丢。
- `.gitignore` 全局忽略 `*.json`/`*.jsonl` 是安全边界；如果未来需要提交 JSON 配置，
  必须显式评估并使用更窄的 allowlist。

## 本地笔记

- 临时脚本、一次性输出、真实 raw data、实验结果放在 `local_dev/` 或 `local_prod/`。
- 审计或验证生成的 `dist/`、`.coverage`、`build/` 和 `_audit*` 目录，结束前清理。
