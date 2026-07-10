param(
	[Parameter(Mandatory=$true)]
	[string]$ModPath,

	[string]$GameRoot = (Get-Location).Path,

	[string[]]$AllowedScriptBomPatterns = @(),

	[switch]$Strict
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$issues = New-Object System.Collections.Generic.List[object]

function Add-Issue {
	param(
		[string]$Severity,
		[string]$File,
		[string]$Message
	)
	$issues.Add([PSCustomObject]@{
		Severity = $Severity
		File = $File
		Message = $Message
	}) | Out-Null
}

function Test-NameInGfx {
	param([string]$Name)
	$interfaceRoots = @(
		(Join-Path $ModPath "interface"),
		(Join-Path $GameRoot "interface")
	)
	foreach ($interfaceRoot in $interfaceRoots) {
		if (-not (Test-Path -LiteralPath $interfaceRoot)) {
			continue
		}
		$gfxFiles = Get-ChildItem -LiteralPath $interfaceRoot -Recurse -Filter "*.gfx" -File -ErrorAction SilentlyContinue
		foreach ($file in $gfxFiles) {
			$pattern = "^\s*name\s*=\s*`"$([regex]::Escape($Name))`""
			if (Select-String -LiteralPath $file.FullName -Pattern $pattern -Quiet) {
				return $true
			}
		}
	}
	return $false
}

function Test-Eu4FlagTga {
	param(
		[string]$Path,
		[string]$RelativePath
	)
	$bytes = [System.IO.File]::ReadAllBytes($Path)
	if ($bytes.Length -lt 18) {
		Add-Issue "ERROR" $RelativePath "TGA flag is too short to contain a valid header."
		return
	}
	$idLength = $bytes[0]
	$colorMapType = $bytes[1]
	$imageType = $bytes[2]
	$width = [BitConverter]::ToUInt16($bytes, 12)
	$height = [BitConverter]::ToUInt16($bytes, 14)
	$pixelDepth = $bytes[16]
	$alphaBits = $bytes[17] -band 0x0F
	if (
		($idLength -ne 0) -or
		($colorMapType -ne 0) -or
		(($imageType -ne 2) -and ($imageType -ne 10)) -or
		($width -ne 128) -or
		($height -ne 128) -or
		($pixelDepth -ne 24) -or
		($alphaBits -ne 0)
	) {
		Add-Issue "ERROR" $RelativePath "Flag should be a vanilla-compatible TGA: 128x128, 24-bit RGB, no color map, no alpha, image type 2 or 10. Found id=$idLength colorMap=$colorMapType type=$imageType size=${width}x${height} depth=$pixelDepth alphaBits=$alphaBits."
	}
}

$ModPath = (Resolve-Path -LiteralPath $ModPath).Path
$modName = Split-Path -Leaf $ModPath
$outerDescriptor = Join-Path (Split-Path -Parent $ModPath) "$modName.mod"
$innerDescriptor = Join-Path $ModPath "descriptor.mod"

if (-not (Test-Path -LiteralPath $innerDescriptor)) {
	Add-Issue "ERROR" "descriptor.mod" "Missing inner descriptor."
}
if (-not (Test-Path -LiteralPath $outerDescriptor)) {
	Add-Issue "ERROR" "$modName.mod" "Missing outer descriptor beside the mod folder."
}
else {
	$outerText = Get-Content -Raw -LiteralPath $outerDescriptor
	$expectedRelative = "mod/$modName"
	$expectedAbsolute = ($ModPath -replace "\\", "/")
	if (($outerText -notmatch "path\s*=\s*`"$([regex]::Escape($expectedRelative))`"") -and
		($outerText -notmatch "path\s*=\s*`"$([regex]::Escape($expectedAbsolute))`"")) {
		Add-Issue "WARN" "$modName.mod" "Outer descriptor path is neither path=`"$expectedRelative`" nor the absolute mod path."
	}
}

$scriptFiles = Get-ChildItem -Recurse -File -LiteralPath $ModPath -ErrorAction SilentlyContinue | Where-Object { $_.Extension -in ".txt",".mod" }
foreach ($file in $scriptFiles) {
	if ($file.Extension -eq ".txt") {
		$relativePath = $file.FullName.Substring($ModPath.Length + 1)
		$prefix = Get-Content -Encoding Byte -TotalCount 3 -LiteralPath $file.FullName
		if (($prefix -join " ") -eq "239 187 191") {
			$allowed = $false
			foreach ($pattern in $AllowedScriptBomPatterns) {
				if ($relativePath -like $pattern) {
					$allowed = $true
					break
				}
			}
			if (-not $allowed) {
				Add-Issue "ERROR" $relativePath "EU4 script .txt files must be UTF-8 without BOM; a BOM can corrupt the first top-level token."
			}
		}
	}
	$text = Get-Content -Raw -LiteralPath $file.FullName
	$open = ([regex]::Matches($text, "\{")).Count
	$close = ([regex]::Matches($text, "\}")).Count
	if ($open -ne $close) {
		Add-Issue "ERROR" $file.FullName.Substring($ModPath.Length + 1) "Brace mismatch: {=$open }=$close."
	}
}

$locFiles = Get-ChildItem -Recurse -File -LiteralPath (Join-Path $ModPath "localisation") -Filter "*.yml" -ErrorAction SilentlyContinue
foreach ($file in $locFiles) {
	$rel = $file.FullName.Substring($ModPath.Length + 1)
	$bytes = Get-Content -Encoding Byte -TotalCount 3 -LiteralPath $file.FullName
	if (($bytes -join " ") -ne "239 187 191") {
		Add-Issue "WARN" $rel "Localisation file should be UTF-8 BOM."
	}
	$firstLine = Get-Content -LiteralPath $file.FullName -TotalCount 1
	if ($firstLine -notmatch "^l_[a-z_]+:") {
		Add-Issue "ERROR" $rel "First line should be a language header such as l_english:."
	}
}

$tagFiles = Get-ChildItem -Recurse -File -LiteralPath (Join-Path $ModPath "common\country_tags") -Filter "*.txt" -ErrorAction SilentlyContinue
foreach ($file in $tagFiles) {
	$matches = Select-String -LiteralPath $file.FullName -Pattern '^\s*([A-Z0-9]{3})\s*=\s*"countries/(.+?)"\s*$'
	foreach ($match in $matches) {
		$tag = $match.Matches[0].Groups[1].Value
		$countryFile = $match.Matches[0].Groups[2].Value
		if (-not (Test-Path -LiteralPath (Join-Path $ModPath "common\countries\$countryFile"))) {
			Add-Issue "ERROR" $file.FullName.Substring($ModPath.Length + 1) "Tag $tag points to missing common/countries/$countryFile."
		}
		$flagPath = Join-Path $ModPath "gfx\flags\$tag.tga"
		if (-not (Test-Path -LiteralPath $flagPath)) {
			Add-Issue "WARN" "gfx\flags\$tag.tga" "Missing TGA flag for tag $tag."
		}
		else {
			Test-Eu4FlagTga -Path $flagPath -RelativePath "gfx\flags\$tag.tga"
		}
		$historyMatch = Get-ChildItem -File -LiteralPath (Join-Path $ModPath "history\countries") -ErrorAction SilentlyContinue | Where-Object { $_.Name -like "$tag - *.txt" } | Select-Object -First 1
		if (-not $historyMatch) {
			Add-Issue "WARN" "history\countries" "No history country file found for $tag."
		}
	}
}

$countryFiles = Get-ChildItem -Recurse -File -LiteralPath (Join-Path $ModPath "common\countries") -Filter "*.txt" -ErrorAction SilentlyContinue
foreach ($file in $countryFiles) {
	$text = Get-Content -Raw -LiteralPath $file.FullName
	foreach ($listName in @("leader_names", "ship_names")) {
		$listMatch = [regex]::Match($text, "(?ms)^\s*$listName\s*=\s*\{(?<body>.*?)\}")
		if ($listMatch.Success) {
			$bodyWithoutComments = [regex]::Replace($listMatch.Groups["body"].Value, "(?m)#.*$", "")
			$entryCount = [regex]::Matches($bodyWithoutComments, '"[^"]+"|[^\s]+').Count
			if ($entryCount -lt 10) {
				Add-Issue "WARN" $file.FullName.Substring($ModPath.Length + 1) "$listName has $entryCount entries; EU4 logs a countrydatabase error when a custom country has fewer than 10."
			}
		}
	}
	$blocks = [regex]::Matches($text, "historical_units\s*=\s*\{(?<body>[\s\S]*?)\}", "Multiline")
	foreach ($block in $blocks) {
		$unitNames = [regex]::Matches($block.Groups["body"].Value, "^\s*([a-z0-9_]+)\s*$", "Multiline")
		foreach ($unit in $unitNames) {
			$name = $unit.Groups[1].Value
			if (-not (Test-Path -LiteralPath (Join-Path $GameRoot "common\units\$name.txt"))) {
				Add-Issue "ERROR" $file.FullName.Substring($ModPath.Length + 1) "Historical unit '$name' not found in vanilla common/units."
			}
		}
	}
}

$missionFiles = Get-ChildItem -Recurse -File -LiteralPath (Join-Path $ModPath "missions") -Filter "*.txt" -ErrorAction SilentlyContinue
foreach ($file in $missionFiles) {
	$icons = Select-String -LiteralPath $file.FullName -Pattern '^\s*icon\s*=\s*([A-Za-z0-9_]+)'
	foreach ($icon in $icons) {
		$name = $icon.Matches[0].Groups[1].Value
		if (-not (Test-NameInGfx $name)) {
			Add-Issue "WARN" $file.FullName.Substring($ModPath.Length + 1) "Mission icon '$name' was not found in mod or vanilla interface .gfx files."
		}
	}
}

$eventFiles = Get-ChildItem -Recurse -File -LiteralPath (Join-Path $ModPath "events") -Filter "*.txt" -ErrorAction SilentlyContinue
foreach ($file in $eventFiles) {
	$pictures = Select-String -LiteralPath $file.FullName -Pattern '^\s*picture\s*=\s*([A-Za-z0-9_]+)'
	foreach ($picture in $pictures) {
		$name = $picture.Matches[0].Groups[1].Value
		if (-not (Test-NameInGfx $name)) {
			Add-Issue "WARN" $file.FullName.Substring($ModPath.Length + 1) "Event picture '$name' was not found in mod or vanilla interface .gfx files."
		}
	}
}

if ($issues.Count -eq 0) {
	Write-Output "OK: No issues found in $ModPath"
	exit 0
}

$issues | Sort-Object Severity,File | Format-Table -AutoSize
$errorCount = @($issues | Where-Object { $_.Severity -eq "ERROR" }).Count
$warnCount = @($issues | Where-Object { $_.Severity -eq "WARN" }).Count
if ($errorCount -gt 0) {
	exit 1
}
if ($Strict -and ($warnCount -gt 0)) {
	exit 1
}
exit 0
