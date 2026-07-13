[CmdletBinding()]
param(
	[Parameter(Mandatory = $true)]
	[string]$ModPath,

	[Parameter(Mandatory = $true)]
	[string]$GameRoot,

	[string]$PythonPath,

	[switch]$SkipUnitTests
)

$ErrorActionPreference = "Stop"
$mod = [IO.Path]::GetFullPath($ModPath)
$game = [IO.Path]::GetFullPath($GameRoot)
$validator = Join-Path $mod "tools\jxp_validation\run_validation.py"
$tests = Join-Path $mod "tools\jxp_validation\tests"

if (-not (Test-Path -LiteralPath (Join-Path $mod "descriptor.mod"))) {
	throw "Mod descriptor is missing: $mod"
}
if (-not (Test-Path -LiteralPath (Join-Path $game "launcher-settings.json"))) {
	throw "EU4 game root is invalid: $game"
}
if (-not (Test-Path -LiteralPath $validator)) {
	throw "JXP validator is missing: $validator"
}

if (-not $PythonPath) {
	$bundled = Join-Path $env:USERPROFILE ".cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
	if (Test-Path -LiteralPath $bundled) {
		$PythonPath = $bundled
	}
	else {
		$command = Get-Command python -ErrorAction SilentlyContinue
		if ($command) {
			$PythonPath = $command.Source
		}
	}
}
if (-not $PythonPath -or -not (Test-Path -LiteralPath $PythonPath)) {
	throw "A working Python executable is required; pass -PythonPath"
}

$generalValidator = Join-Path $PSScriptRoot "validate_eu4_mod.ps1"
& $generalValidator `
	-ModPath $mod `
	-GameRoot $game `
	-AllowedScriptBomPatterns "missions\jxp_00_legacy_bom_*.txt"
if ($LASTEXITCODE -ne 0) {
	throw "General EU4 validation failed with exit code $LASTEXITCODE"
}

& $PythonPath $validator --mod-root $mod --game-root $game --max-details 100
if ($LASTEXITCODE -ne 0) {
	throw "JXP validation failed with exit code $LASTEXITCODE"
}

if (-not $SkipUnitTests) {
	if (-not (Test-Path -LiteralPath $tests)) {
		throw "JXP validation tests are missing: $tests"
	}
	$oldPythonPath = $env:PYTHONPATH
	try {
		$env:PYTHONPATH = Join-Path $mod "tools"
		Push-Location $mod
		try {
			& $PythonPath -m unittest discover -s "tools\jxp_validation\tests" -v
			if ($LASTEXITCODE -ne 0) {
				throw "JXP validator unit tests failed with exit code $LASTEXITCODE"
			}
		}
		finally {
			Pop-Location
		}
	}
	finally {
		$env:PYTHONPATH = $oldPythonPath
	}
}

Write-Host "OK: JXP general, release, topology, asset, and unit validation passed."
