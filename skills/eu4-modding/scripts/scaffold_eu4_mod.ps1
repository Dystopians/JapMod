param(
	[Parameter(Mandatory=$true)]
	[string]$ModId,

	[string]$DisplayName,

	[string]$SupportedVersion,

	[string]$GameRoot = (Get-Location).Path,

	[string]$GameDataPath,

	[string[]]$Tags = @("Gameplay", "Events", "Missions And Decisions"),

	[switch]$Force
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Convert-ToSupportedVersion {
	param([string]$RawVersion)
	if ($RawVersion -match "v?(\d+)\.(\d+)") {
		return "$($Matches[1]).$($Matches[2]).*"
	}
	return "1.*"
}

if ($ModId -notmatch "^[a-z0-9_\\-]+$") {
	throw "ModId must contain only lowercase letters, digits, underscore, or hyphen."
}

if (-not $DisplayName) {
	$DisplayName = ($ModId -replace "[-_]+", " ")
	$DisplayName = (Get-Culture).TextInfo.ToTitleCase($DisplayName)
}

$settingsPath = Join-Path $GameRoot "launcher-settings.json"
if (-not $SupportedVersion) {
	if (Test-Path -LiteralPath $settingsPath) {
		$settings = Get-Content -Raw -Encoding UTF8 -LiteralPath $settingsPath | ConvertFrom-Json
		$SupportedVersion = Convert-ToSupportedVersion $settings.rawVersion
	}
	else {
		$SupportedVersion = "1.*"
	}
}

if (-not $GameDataPath) {
	$GameDataPath = Join-Path ([Environment]::GetFolderPath("MyDocuments")) "Paradox Interactive\Europa Universalis IV"
}

$modBase = Join-Path $GameDataPath "mod"
$modPath = Join-Path $modBase $ModId
$outerDescriptor = Join-Path $modBase "$ModId.mod"

if ((Test-Path -LiteralPath $modPath) -and -not $Force) {
	throw "Mod folder already exists: $modPath. Pass -Force to reuse it."
}
if ((Test-Path -LiteralPath $outerDescriptor) -and -not $Force) {
	throw "Outer descriptor already exists: $outerDescriptor. Pass -Force to overwrite it."
}

New-Item -ItemType Directory -Force -Path $modPath | Out-Null
$dirs = @(
	"common\country_tags",
	"common\countries",
	"common\event_modifiers",
	"common\ideas",
	"decisions",
	"events",
	"gfx\flags",
	"history\countries",
	"localisation",
	"missions"
)
foreach ($dir in $dirs) {
	New-Item -ItemType Directory -Force -Path (Join-Path $modPath $dir) | Out-Null
}

$tagLines = ($Tags | ForEach-Object { "`t`"$_`"" }) -join [Environment]::NewLine
$outer = @"
name="$DisplayName"
path="mod/$ModId"
supported_version="$SupportedVersion"
tags={
$tagLines
}
"@
$inner = @"
name="$DisplayName"
supported_version="$SupportedVersion"
tags={
$tagLines
}
"@

New-Item -ItemType Directory -Force -Path $modBase | Out-Null
Set-Content -LiteralPath $outerDescriptor -Value $outer -Encoding UTF8
Set-Content -LiteralPath (Join-Path $modPath "descriptor.mod") -Value $inner -Encoding UTF8

[PSCustomObject]@{
	ModId = $ModId
	DisplayName = $DisplayName
	SupportedVersion = $SupportedVersion
	ModPath = $modPath
	OuterDescriptor = $outerDescriptor
}
