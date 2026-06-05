<#
.SYNOPSIS
    Sparse clone DimbreathBot/AnimeGameData for hoyo-story-extractor.
.DESCRIPTION
    Pulls only the files needed for text extraction (~740 MB vs 6.3 GB full).
    Requires git and access to GitHub via proxy at 127.0.0.1:7897.
.PARAMETER TargetDir
    Destination directory (default: .\genshin_raw in current location).
.PARAMETER Proxy
    HTTP(S) proxy address (default: http://127.0.0.1:7897).
.EXAMPLE
    .\clone_genshin_raw.ps1
    .\clone_genshin_raw.ps1 -TargetDir D:\data\genshin_v6.6 -Proxy http://127.0.0.1:7897
#>

param(
    [string]$TargetDir = "genshin_raw",
    [string]$Proxy = "http://127.0.0.1:7897"
)

$ErrorActionPreference = "Stop"

if (Test-Path $TargetDir) {
    Write-Error "目录已存在: $TargetDir`n请删除或指定其他目录。"
    exit 1
}

$repoUrl = "https://github.com/DimbreathBot/AnimeGameData.git"

# In non-cone mode, git needs leading "/" for file paths to disambiguate from dirs.
# Trailing "/" for directories is optional but makes intent clear.
$paths = @(
    "/TextMap/TextMapCHS.json",
    "/TextMap/TextMap_MediumCHS.json",
    "/TextMap/TextMapJP.json",
    "/TextMap/TextMap_MediumJP.json",
    "/TextMap/TextMapEN.json",
    "/TextMap/TextMap_MediumEN.json",
    "/BinOutput/CodexQuest/",
    "/BinOutput/Talk/",
    "/ExcelBinOutput/AvatarExcelConfigData.json",
    "/ExcelBinOutput/FetterInfoExcelConfigData.json",
    "/ExcelBinOutput/FettersExcelConfigData.json",
    "/ExcelBinOutput/FetterStoryExcelConfigData.json",
    "/ExcelBinOutput/DialogExcelConfigData.json",
    "/ExcelBinOutput/NpcExcelConfigData.json",
    "/ExcelBinOutput/MaterialExcelConfigData.json",
    "/ExcelBinOutput/WeaponExcelConfigData.json",
    "/ExcelBinOutput/ReliquaryExcelConfigData.json",
    "/ExcelBinOutput/ReliquarySetExcelConfigData.json",
    "/ExcelBinOutput/EquipAffixExcelConfigData.json",
    "/Readable/CHS/",
    "/Readable/EN/",
    "/Readable/JP/"
)

Write-Host "=== 原神 Raw Data Sparse Checkout ===" -ForegroundColor Cyan
Write-Host "  仓库: $repoUrl"
Write-Host "  代理: $Proxy"
Write-Host "  目标: $TargetDir"
Write-Host "  路径数: $($paths.Count)"
Write-Host ""

# Step 1: sparse clone
Write-Host "[1/2] Sparse clone (depth=1, blobless)..." -ForegroundColor Yellow
$cloneArgs = @(
    "clone", "--depth=1", "--filter=blob:none", "--sparse",
    "-c", "http.proxy=$Proxy",
    "-c", "https.proxy=$Proxy",
    $repoUrl, $TargetDir
)
& git @cloneArgs
if ($LASTEXITCODE -ne 0) {
    Write-Error "git clone 失败"
    exit 1
}

# Step 2: set sparse-checkout paths (non-cone mode for individual files)
Write-Host "[2/2] Setting sparse-checkout paths..." -ForegroundColor Yellow
Push-Location $TargetDir
$checkoutArgs = @("sparse-checkout", "set", "--no-cone") + $paths
& git @checkoutArgs
if ($LASTEXITCODE -ne 0) {
    Pop-Location
    Write-Error "sparse-checkout set 失败"
    exit 1
}
Pop-Location

# Verify key paths exist
Write-Host ""
Write-Host "验证..." -ForegroundColor Yellow
$missing = @()
foreach ($p in @("TextMap", "BinOutput/CodexQuest", "BinOutput/Talk", "ExcelBinOutput", "Readable")) {
    if (-not (Test-Path (Join-Path $TargetDir $p))) {
        $missing += $p
        Write-Host "  MISSING: $p" -ForegroundColor Red
    } else {
        Write-Host "    OK: $p" -ForegroundColor Green
    }
}

if ($missing.Count -gt 0) {
    Write-Error "以下路径未检出: $($missing -join ', ')"
    exit 1
}

# Summary
$size = (Get-ChildItem $TargetDir -Recurse -File | Measure-Object -Property Length -Sum).Sum
$sizeMB = [math]::Round($size / 1MB, 1)
Write-Host ""
Write-Host "=== 完成 ===" -ForegroundColor Green
Write-Host "  路径: $((Resolve-Path $TargetDir).Path)"
Write-Host "  大小: ${sizeMB} MB"
