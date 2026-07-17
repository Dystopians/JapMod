[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$GameRoot,

    [Parameter(Mandatory = $true)]
    [string]$MainMod,

    [string]$PythonPath,

    [switch]$AllowSourceDownload,

    [switch]$SkipValidation
)

$ErrorActionPreference = "Stop"
$ModRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot ".."))
$GameRoot = [IO.Path]::GetFullPath($GameRoot)
$MainMod = [IO.Path]::GetFullPath($MainMod)

if (-not $PythonPath) {
    $bundled = Join-Path $env:USERPROFILE ".cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
    if (Test-Path -LiteralPath $bundled) {
        $PythonPath = $bundled
    }
    else {
        $pythonCommand = Get-Command python -ErrorAction SilentlyContinue
        if ($pythonCommand) {
            $PythonPath = $pythonCommand.Source
        }
    }
}

foreach ($requiredPath in @(
    $PythonPath,
    (Join-Path $GameRoot "launcher-settings.json"),
    (Join-Path $MainMod "descriptor.mod"),
    (Join-Path $ModRoot "descriptor.mod")
)) {
    if (-not $requiredPath -or -not (Test-Path -LiteralPath $requiredPath)) {
        throw "Required path is missing: $requiredPath"
    }
}

function Invoke-PythonFile {
    param(
        [Parameter(Mandatory = $true)]
        [string]$ScriptPath,

        [string[]]$ScriptArguments = @()
    )

    Write-Host "`n>>> $([IO.Path]::GetFileName($ScriptPath)) $($ScriptArguments -join ' ')"
    & $PythonPath $ScriptPath @ScriptArguments
    if ($LASTEXITCODE -ne 0) {
        throw "$ScriptPath failed with exit code $LASTEXITCODE"
    }
}

$mapArguments = @("--game-root", $GameRoot)
if (-not $AllowSourceDownload) {
    $mapArguments += "--offline"
}

Invoke-PythonFile `
    -ScriptPath (Join-Path $ModRoot "tools\jxp_map_builder\build_map.py") `
    -ScriptArguments $mapArguments

Invoke-PythonFile `
    -ScriptPath (Join-Path $ModRoot "tools\jxp_asset_builder\build_assets.py")

Invoke-PythonFile `
    -ScriptPath (Join-Path $ModRoot "tools\jxp_map_builder\build_countries.py") `
    -ScriptArguments @("--game-root", $GameRoot, "--main-mod", $MainMod)

Invoke-PythonFile `
    -ScriptPath (Join-Path $ModRoot "tools\jxp_map_builder\build_history.py") `
    -ScriptArguments @("--game-root", $GameRoot)

$escapeScript = Join-Path $env:USERPROFILE ".codex\skills\eu4-modding\scripts\escape_eu4_special_localisation.py"
if (-not (Test-Path -LiteralPath $escapeScript)) {
    throw "EU4 localisation converter is missing: $escapeScript"
}

$localisationPairs = @(
    [PSCustomObject]@{
        Source = Join-Path $ModRoot "localisation_source\jxp_map_l_english_utf8_source.yml"
        Target = Join-Path $ModRoot "localisation\jxp_map_l_english.yml"
    },
    [PSCustomObject]@{
        Source = Join-Path $ModRoot "localisation_source\jxp_map_content_l_english_utf8_source.yml"
        Target = Join-Path $ModRoot "localisation\jxp_map_content_l_english.yml"
    }
)
foreach ($pair in $localisationPairs) {
    Invoke-PythonFile -ScriptPath $escapeScript -ScriptArguments @($pair.Source, $pair.Target)
}

$mainVisualizer = Join-Path $MainMod "tools\jxp_visualizer\generate_visualizer.py"
if (-not (Test-Path -LiteralPath $mainVisualizer)) {
    throw "Main-mod visualizer generator is missing: $mainVisualizer"
}

Invoke-PythonFile `
    -ScriptPath $mainVisualizer `
    -ScriptArguments @(
        "--mod-root", $ModRoot,
        "--game-root", $GameRoot,
        "--output", (Join-Path $ModRoot "tools\jxp_visualizer\jxp_map_visualizer.html")
    )

Invoke-PythonFile `
    -ScriptPath (Join-Path $ModRoot "tools\jxp_visualizer\generate_combined_visualizer.py") `
    -ScriptArguments @("--main-mod", $MainMod, "--game-root", $GameRoot)

if (-not $SkipValidation) {
    $validateScript = Join-Path $ModRoot "tools\validate_all.ps1"
    Write-Host "`n>>> validate_all.ps1"
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $validateScript `
        -GameRoot $GameRoot `
        -MainMod $MainMod `
        -PythonPath $PythonPath
    if ($LASTEXITCODE -ne 0) {
        throw "Full validation failed with exit code $LASTEXITCODE"
    }
}

Write-Host "`nBuild complete. No EU4 process was started."
