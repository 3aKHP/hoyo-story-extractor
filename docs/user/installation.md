# 安装指南

## 环境要求

- **Python** ≥ 3.11
- **Git** ≥ 2.38（需要 `sparse-checkout` 支持）
- **[uv](https://docs.astral.sh/uv/)** — Python 包管理器（替代 pip/poetry）

### 安装 uv

```bash
# macOS / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows PowerShell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

## 安装 hoyo-story-extractor

```bash
git clone https://github.com/3aKHP/hoyo-story-extractor.git
cd hoyo-story-extractor

# 安装项目 + 开发依赖（pytest, ruff）
uv sync --extra dev
```

验证安装：

```bash
uv run pytest                  # 45 tests expected
uv run hoyo-extract --version  # hoyo-story-extractor v0.1.0
uv run hoyo-extract --help     # 查看可用命令
```

未激活 `.venv` 时，直接运行 `hoyo-extract` 不一定在 PATH 中；推荐使用
`uv run hoyo-extract ...`。

## 获取游戏数据

项目本身不包含任何游戏数据文件。你需要从社区 datamine 仓库自行获取。

### 原神（Genshin Impact）

**Windows（推荐脚本）**：

```powershell
.\scripts\clone_genshin_raw.ps1 -TargetDir .\genshin_raw
```

如果 GitHub 需要代理：

```powershell
.\scripts\clone_genshin_raw.ps1 -TargetDir .\genshin_raw -Proxy http://127.0.0.1:7897
```

**macOS / Linux（手动命令）**：

```bash
git clone --depth=1 --filter=blob:none --sparse \
  https://github.com/DimbreathBot/AnimeGameData.git genshin_raw

cd genshin_raw
git sparse-checkout set --no-cone \
  /TextMap/TextMapCHS.json \
  /TextMap/TextMap_MediumCHS.json \
  /TextMap/TextMapJP.json \
  /TextMap/TextMap_MediumJP.json \
  /TextMap/TextMapEN.json \
  /TextMap/TextMap_MediumEN.json \
  /BinOutput/CodexQuest/ \
  /BinOutput/Talk/ \
  /ExcelBinOutput/AvatarExcelConfigData.json \
  /ExcelBinOutput/FetterInfoExcelConfigData.json \
  /ExcelBinOutput/FettersExcelConfigData.json \
  /ExcelBinOutput/FetterStoryExcelConfigData.json \
  /ExcelBinOutput/DialogExcelConfigData.json \
  /ExcelBinOutput/NpcExcelConfigData.json \
  /ExcelBinOutput/MaterialExcelConfigData.json \
  /ExcelBinOutput/WeaponExcelConfigData.json \
  /ExcelBinOutput/ReliquaryExcelConfigData.json \
  /ExcelBinOutput/ReliquarySetExcelConfigData.json \
  /ExcelBinOutput/EquipAffixExcelConfigData.json \
  /Readable/CHS/ \
  /Readable/EN/ \
  /Readable/JP/
```

预计 sparse checkout 大小 ~740 MB（全量 6.3 GB）。

### 星穹铁道 / 绝区零

尚在规划中（Phase 5 / Phase 6）。当前公开 CLI 只支持 `genshin`。

## 常见安装问题

### `uv sync` 失败：hatchling 找不到包

确保在项目根目录下执行，`src/hoyo_story/` 目录存在。

### `git sparse-checkout` 报错：not a directory

你的 git 版本可能过旧（<2.38）。升级 git 或使用脚本中的 `--no-cone` 标志。

### 代理问题

如果你在中国大陆，访问 GitHub 可能需要代理。使用 `--proxy` 参数或在 git 全局配置中设置：

```bash
git config --global http.proxy http://127.0.0.1:7897
git config --global https.proxy http://127.0.0.1:7897
```
