[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$GameRoot,

    [Parameter(Mandatory = $true)]
    [string]$MainMod,

    [string]$PythonPath,

    [switch]$SkipMainModValidation
)

$ErrorActionPreference = "Stop"
$RepoRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot "..\.."))
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
    (Join-Path $ModRoot "descriptor.mod"),
    (Join-Path $PSScriptRoot "requirements-validation.txt")
)) {
    if (-not $requiredPath -or -not (Test-Path -LiteralPath $requiredPath)) {
        throw "Required path is missing: $requiredPath"
    }
}

$pythonProbeOutput = @()
$pythonProbeExitCode = 1
try {
    $pythonProbeOutput = & $PythonPath -c "import sys,numpy,PIL; assert sys.version_info >= (3,10); nv=int(numpy.__version__.split(chr(46))[0]); pv=int(PIL.__version__.split(chr(46))[0]); assert 2 <= nv < 3; assert 10 <= pv < 13" 2>&1
    $pythonProbeExitCode = $LASTEXITCODE
}
catch {
    $pythonProbeOutput = @($_.Exception.Message)
}
if ($pythonProbeExitCode -ne 0) {
    $requirements = Join-Path $PSScriptRoot "requirements-validation.txt"
    throw "Validation requires Python 3.10+ with NumPy and Pillow. Create an isolated runtime, run '& <python> -m pip install -r $requirements', and pass its executable with -PythonPath. Probe output: $($pythonProbeOutput -join ' ')"
}
$pythonVersion = & $PythonPath --version
$dependencyVersions = & $PythonPath -c "import numpy,PIL; print(numpy.__version__+chr(32)+PIL.__version__)"
Write-Host "$pythonVersion; NumPy/Pillow $dependencyVersions satisfy validation ranges"

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

function Invoke-PowerShellFile {
    param(
        [Parameter(Mandatory = $true)]
        [string]$ScriptPath,

        [string[]]$ScriptArguments = @()
    )

    Write-Host "`n>>> $([IO.Path]::GetFileName($ScriptPath)) $($ScriptArguments -join ' ')"
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $ScriptPath @ScriptArguments
    if ($LASTEXITCODE -ne 0) {
        throw "$ScriptPath failed with exit code $LASTEXITCODE"
    }
}

Invoke-PythonFile `
    -ScriptPath (Join-Path $ModRoot "tools\jxp_map_validation\validate_map.py") `
    -ScriptArguments @("--game-root", $GameRoot, "--strict-history")

Invoke-PythonFile `
    -ScriptPath (Join-Path $ModRoot "tools\jxp_map_validation\validate_history.py") `
    -ScriptArguments @("--game-root", $GameRoot, "--main-mod", $MainMod)

Invoke-PythonFile `
    -ScriptPath (Join-Path $ModRoot "tools\jxp_map_validation\validate_content.py") `
    -ScriptArguments @("--game-root", $GameRoot, "--main-mod", $MainMod)

Invoke-PythonFile `
    -ScriptPath (Join-Path $ModRoot "tools\jxp_map_validation\validate_main_compatibility.py") `
    -ScriptArguments @("--game-root", $GameRoot, "--main-mod", $MainMod)

Invoke-PythonFile `
    -ScriptPath (Join-Path $ModRoot "tools\jxp_map_validation\validate_assets.py")

$pinnedSkillScripts = Join-Path $RepoRoot "skills\eu4-modding\scripts"
$skillScripts = $pinnedSkillScripts
foreach ($skillScript in @(
    "check_mission_series_overlap.py",
    "validate_eu4_mod.ps1",
    "validate_jxp_mod.ps1"
)) {
    $skillScriptPath = Join-Path $skillScripts $skillScript
    if (-not (Test-Path -LiteralPath $skillScriptPath -PathType Leaf)) {
        throw "Required pinned EU4 skill script is missing: $skillScriptPath"
    }
}
Invoke-PythonFile `
    -ScriptPath (Join-Path $skillScripts "check_mission_series_overlap.py") `
    -ScriptArguments @($ModRoot)

Invoke-PowerShellFile `
    -ScriptPath (Join-Path $skillScripts "validate_eu4_mod.ps1") `
    -ScriptArguments @("-ModPath", $ModRoot, "-GameRoot", $GameRoot, "-Strict")

if (-not $SkipMainModValidation) {
    Invoke-PowerShellFile `
        -ScriptPath (Join-Path $skillScripts "validate_jxp_mod.ps1") `
        -ScriptArguments @(
            "-ModPath", $MainMod,
            "-GameRoot", $GameRoot,
            "-PythonPath", $PythonPath
        )
}

Write-Host "`nPASS: companion and dependency static validation completed."
Write-Host "No EU4 process was started; runtime acceptance remains a separate approved step."
