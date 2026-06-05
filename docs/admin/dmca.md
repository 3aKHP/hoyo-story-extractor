# DMCA 风险与合规策略

## 风险分析

本页是项目维护层面的风险说明，不构成法律意见。公开发布或运营数据归档仓库前，
仍建议按实际用途和所在地咨询专业法律意见。

本项目目标是**只分发提取后的纯文本对话转录**，不包含任何原始游戏文件。这与被 DMCA 下架的仓库有明显差异：

| | 被 DMCA 的仓库 | 本项目（数据仓库） |
|------|------|------|
| 仓库内容 | 游戏原始 JSON/Bin 文件 | 纯 `.txt` 对话转录 |
| 是否包含游戏代码 | 是 | 否 |
| 是否包含美术/音频 | 是 | 否 |
| 是否可被认定为"盗版" | 高风险（直接复制） | 风险相对较低但仍需谨慎 |

## 已有安全运行的先例

| 仓库 | 运行时长 | DMCA 状态 |
|------|:---:|------|
| `ci-ke/ProjectSekai-story` | 14 个月，日更 | ✅ |
| `mrzjy/GenshinDialog` | 3 年 | ✅ |
| `mrzjy/StarrailDialogue` | 活跃维护中 | ✅ |
| 各游戏 wiki（fandom 等） | 数十年 | ✅ |

## 米哈游的 DMCA 模式

从社区观察看，米哈游对游戏资产文件相关仓库有过较积极的 DMCA 执法：
- 2023-2025 年间多次对 Dimbreath 及 fork 发起 DMCA
- 对 `GenshinTextures`（纹理）、`GenshinCutscenes`（过场）发起 DMCA
- 尚未在本项目调研范围内发现针对纯对话文本仓库的典型案例

这表明执法重点在**游戏资产文件**（代码、纹理、音频、视频），而非文本转录。

## 预防措施

### 1. 提取引擎与数据分离

```
hoyo-story-extractor       ← 提取脚本（Python源码），不含游戏数据
teyvat-story-archive       ← 数据输出（纯 .txt），不含原始格式
```

- 提取引擎仓库可以被 fork/镜像，不含任何游戏知识产权
- 即使数据仓库被 DMCA，提取引擎不受影响，可快速重建

### 2. 数据仓库绝不包含原始游戏文件

```gitignore
# 绝不允许
*.json
*.jsonl
*.bin
*.asset
```

CI workflow 中应有校验步骤防止误提交。

### 3. Raw data URL 不硬编码

仓库地址通过环境变量注入，提取引擎代码本身是"一个通用的游戏文本提取框架"。

### 4. 多源冗余

```
主源：DimbreathBot/AnimeGameData (GitHub)
备用：Sycamore0/GenshinData (GitHub fork)
备用：git.mero.moe (Gitea 自托管)  
备用：本地缓存（保留最后一次成功提取的快照）
```

### 5. CI 临时空间隔离

```
GitHub Actions Runner（临时 VM）
  /tmp/raw/        ← sparse checkout，构建结束后销毁
  /tmp/extracted/  ← JSONL 中间产物，构建结束后销毁
  /tmp/output/     ← .txt 产出 → git commit & push
```

### 6. 仓库命名策略

| 层级 | 名称 | 策略 |
|------|------|------|
| 提取引擎 | `hoyo-story-extractor` | "hoyo" 是 HoYoverse 社区缩写，不匹配商标扫描 |
| 原神数据 | `teyvat-story-archive` | "Teyvat" = 提瓦特（游戏内虚构地名） |
| 星铁数据 | `starrail-story-archive` | "starrail" 非完整商标 "Honkai: Star Rail" |
| ZZZ 数据 | `zzz-story-archive` | "zzz" 是社区通用缩写 |

参考先例：`DimbreathBot/AnimeGameData`（不用 Genshin）、`TurnBasedGameData`（不用 Honkai Star Rail）。

## 风险矩阵

| 风险 | 概率 | 影响 | 缓解后剩余风险 |
|------|:---:|------|------|
| 数据仓库被 DMCA | 低 | 中（可 fork 恢复） | 极低 |
| 提取器仓库被 DMCA | 低-中 | 低（脚本不含游戏数据） | 低 |
| Raw data 源被 DMCA | **高** | 低（切换备用源） | 低 |
| Dimbreath 停止更新 | 中 | 中（无法跟进最新版本） | 中 |
| 混淆 key 名随版本变更 | 中 | 中（需手动适配） | 中 |

## 核心结论

数据仓库**严格只包含 `.txt` 对话转录**可以显著降低风险，但不能消除风险。  
维护时应持续执行 raw data 禁止提交、CI 校验、快速下架响应和独立数据仓库策略。
