param(
    [ValidateSet('Reference', 'Build', 'Validate')]
    [string]$Mode = 'Build',
    [string]$GameRoot = 'D:\Steam\steamapps\common\Europa Universalis IV'
)

$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Drawing
Add-Type -Path (Join-Path $PSScriptRoot 'JxpIconTools.cs') -ReferencedAssemblies System.Drawing

function Write-Utf8LfLines {
    param(
        [string]$Path,
        [System.Collections.Generic.IEnumerable[string]]$Lines
    )

    $text = [string]::Join("`n", $Lines) + "`n"
    [IO.File]::WriteAllText($Path, $text, [Text.UTF8Encoding]::new($false))
}

$iconRoot = Split-Path -Parent $PSScriptRoot
$previewRoot = Join-Path $PSScriptRoot 'previews'
$individualPreviewRoot = Join-Path $previewRoot 'icons'
$vanillaIconRoot = Join-Path $GameRoot 'gfx\interface\government_reform_icons'
$ddsTemplate = Join-Path $vanillaIconRoot 'daimyo.dds'

$routes = @(
    'sakoku',
    'open',
    'kirishitan',
    'confucian',
    'imperial',
    'reformed',
    'kaikyo',
    'ikko',
    'wokou'
)

$routeIcons = [ordered]@{
    sakoku = @(
        'jxp_sakoku_hostage_roads',
        'jxp_sakoku_coastal_watch',
        'jxp_sakoku_hidden_books'
    )
    open = @(
        'jxp_open_silver_scales',
        'jxp_open_artillery_contract',
        'jxp_open_chartered_factory'
    )
    kirishitan = @(
        'jxp_kirishitan_seminary_book',
        'jxp_kirishitan_hospital_bell',
        'jxp_kirishitan_nagasaki_admiralty'
    )
    confucian = @(
        'jxp_confucian_exam_tablet',
        'jxp_confucian_law_codex',
        'jxp_confucian_three_teachings'
    )
    imperial = @(
        'jxp_imperial_kokugaku_scroll',
        'jxp_imperial_governor_seal',
        'jxp_imperial_guard_banner'
    )
    reformed = @(
        'jxp_reformed_printing_press',
        'jxp_reformed_civic_oath',
        'jxp_reformed_contract_ship'
    )
    kaikyo = @(
        'jxp_kaikyo_monsoon_diwan',
        'jxp_kaikyo_waqf_granary',
        'jxp_kaikyo_spice_guard'
    )
    ikko = @(
        'jxp_ikko_somon_bell',
        'jxp_ikko_granary',
        'jxp_ikko_ashigaru_oath'
    )
    wokou = @(
        'jxp_wokou_black_tide_law',
        'jxp_wokou_freeport',
        'jxp_wokou_boarding_hooks'
    )
}

$founderKeys = @(
    'jxp_founder_house_code',
    'jxp_founder_martial_roll',
    'jxp_founder_cadaster_office',
    'jxp_founder_admiralty',
    'jxp_founder_court_council',
    'jxp_founder_trade_brokerage',
    'jxp_founder_rite_compact',
    'jxp_founder_renovated_state'
)

$japaneseTrackKeys = @(
    'jxp_daimyo_kokujin_oaths',
    'jxp_daimyo_bunkoku_law',
    'jxp_daimyo_kachu_hyojoshu',
    'jxp_japanese_fudai_service_rolls',
    'jxp_japanese_direct_investiture',
    'jxp_japanese_gundai_daikan_partition',
    'jxp_japanese_branch_castle_cadasters',
    'jxp_japanese_religious_arbitration',
    'jxp_japanese_temple_land_settlement',
    'jxp_japanese_ashigaru_muster_rolls',
    'jxp_japanese_kyuba_hatamoto',
    'jxp_japanese_castle_artillery_office',
    'jxp_japanese_funade_ura_service',
    'jxp_japanese_lordly_arbitration',
    'jxp_japanese_elder_countersignature',
    'jxp_japanese_domain_assembly',
    'jxp_japanese_court_temple_service',
    'jxp_japanese_yuhitsu_accountants',
    'jxp_japanese_fudai_magistracy',
    'jxp_japanese_public_authority',
    'jxp_japanese_townsmen_guild_charters',
    'jxp_japanese_checkpoint_red_seals',
    'jxp_japanese_rakuichi_rakuza',
    'jxp_japanese_war_provisioning',
    'jxp_japanese_coinage_edicts',
    'jxp_japanese_new_field_works',
    'jxp_japanese_overseas_settlement_office',
    'jxp_japanese_rule_by_arms',
    'jxp_japanese_general_peace',
    'jxp_japanese_service_compact',
    'jxp_japanese_quarrel_suppression',
    'jxp_japanese_common_security',
    'jxp_japanese_unitary_investiture',
    'jxp_japanese_domain_federation',
    'jxp_japanese_benevolent_government',
    'jxp_japanese_divine_law',
    'jxp_japanese_buke_laws_inspectors',
    'jxp_japanese_hyojosho_collegial_offices',
    'jxp_japanese_petition_direct_appeal'
)

function Get-ExpectedKeys {
    $keys = New-Object System.Collections.Generic.List[string]
    foreach ($route in $routes) {
        foreach ($key in $routeIcons[$route]) {
            $keys.Add($key)
        }
    }
    foreach ($key in $founderKeys) {
        $keys.Add($key)
    }
    foreach ($key in $japaneseTrackKeys) {
        $keys.Add($key)
    }
    return $keys.ToArray()
}

function Write-ValidationReport {
    param([string[]]$Keys)

    $lines = New-Object System.Collections.Generic.List[string]
    $lines.Add('JXP government reform icon validation')
    $lines.Add(('Generated: {0:yyyy-MM-dd HH:mm:ss zzz}' -f (Get-Date)))
    $lines.Add("Expected icons: $($Keys.Count)")
    $actualFiles = @(Get-ChildItem -LiteralPath $iconRoot -File -Filter '*.dds')
    $unexpected = @($actualFiles | Where-Object { $_.BaseName -notin $Keys })
    if ($actualFiles.Count -ne $Keys.Count -or $unexpected.Count -gt 0) {
        throw "Final DDS inventory mismatch: expected $($Keys.Count), found $($actualFiles.Count), unexpected $($unexpected.Name -join ', ')"
    }
    foreach ($key in $Keys) {
        $path = Join-Path $iconRoot ($key + '.dds')
        if (-not (Test-Path -LiteralPath $path)) {
            throw "Missing DDS: $path"
        }
        $inspection = [JxpIconTools]::InspectDds($path)
        if ($inspection -notmatch '\|57x57\|RGBA32\|' -or
            $inspection -notmatch 'masks=00FF0000/0000FF00/000000FF/FF000000' -or
            $inspection -notmatch '\|bytes=13124\|' -or
            $inspection -match '\|nonzero=0\|' -or
            $inspection -match '\|color_energy=0$') {
            throw "DDS validation failed: $inspection"
        }
        $lines.Add($inspection)
    }
    Write-Utf8LfLines `
        -Path (Join-Path $PSScriptRoot 'validation_report.txt') `
        -Lines $lines.ToArray()
}

if ($Mode -eq 'Reference') {
    $relativePaths = @(
        'daimyo.dds',
        'samurai.dds',
        'shogunate.dds',
        'merchant.dds',
        'merchant_ship.dds',
        'monks.dds',
        'judge.dds',
        'crown.dds',
        'king.dds',
        'dlc\domination\strengthen_bakuhan_system_reform.dds',
        'dlc\domination\reform_the_samurai_reform.dds',
        'dlc\lions_of_the_north\pirate_council.dds',
        'dlc\lions_of_the_north\pirate_ship.dds',
        'dlc\lions_of_the_north\royal_court.dds',
        'dlc\lions_of_the_north\national_assembly.dds'
    )
    $labels = @(
        'daimyo',
        'samurai',
        'shogunate',
        'merchant',
        'merchant ship',
        'monks',
        'judge',
        'crown',
        'king',
        'bakuhan system',
        'reform samurai',
        'pirate council',
        'pirate ship',
        'royal court',
        'national assembly'
    )
    $paths = $relativePaths | ForEach-Object { Join-Path $vanillaIconRoot $_ }
    [JxpIconTools]::CreateDdsContactSheet(
        $paths,
        $labels,
        5,
        'EU4 v1.37.5 government reform icon references',
        (Join-Path $PSScriptRoot 'vanilla_reference_contact_sheet.png'))
    return
}

$allKeys = Get-ExpectedKeys
if ($Mode -eq 'Validate') {
    Write-ValidationReport -Keys $allKeys
    return
}

New-Item -ItemType Directory -Force -Path $previewRoot, $individualPreviewRoot | Out-Null
$cropReports = New-Object System.Collections.Generic.List[string]
$masterPngs = New-Object System.Collections.Generic.List[string]
$masterLabels = New-Object System.Collections.Generic.List[string]

foreach ($route in $routes) {
    $sourcePath = Join-Path $PSScriptRoot ("jxp_${route}_source.png")
    if (-not (Test-Path -LiteralPath $sourcePath)) {
        throw "Missing route source sheet: $sourcePath"
    }

    $keys = $routeIcons[$route]
    $previewPaths = $keys | ForEach-Object { Join-Path $individualPreviewRoot ($_ + '.png') }
    $ddsPaths = $keys | ForEach-Object { Join-Path $iconRoot ($_ + '.dds') }
    $report = [JxpIconTools]::ProcessSheet($sourcePath, $previewPaths, $ddsPaths, 2, 2, $ddsTemplate)
    $cropReports.Add("[$route]")
    $cropReports.Add($report)

    [JxpIconTools]::CreatePngContactSheet(
        $previewPaths,
        $keys,
        3,
        ("JXP {0} route" -f $route),
        (Join-Path $previewRoot ("jxp_${route}_preview.png")))

    for ($i = 0; $i -lt $keys.Count; $i++) {
        $masterPngs.Add($previewPaths[$i])
        $masterLabels.Add($keys[$i])
    }
}

$founderSource = Join-Path $PSScriptRoot 'jxp_founder_source.png'
if (-not (Test-Path -LiteralPath $founderSource)) {
    throw "Missing founder source sheet: $founderSource"
}
$founderPngs = $founderKeys | ForEach-Object { Join-Path $individualPreviewRoot ($_ + '.png') }
$founderDds = $founderKeys | ForEach-Object { Join-Path $iconRoot ($_ + '.dds') }
$founderReport = [JxpIconTools]::ProcessSheet($founderSource, $founderPngs, $founderDds, 3, 3, $ddsTemplate)
$cropReports.Add('[founders]')
$cropReports.Add($founderReport)

[JxpIconTools]::CreatePngContactSheet(
    $founderPngs,
    $founderKeys,
    4,
    'JXP founder family icons',
    (Join-Path $previewRoot 'jxp_founder_preview.png'))

$japaneseTrackPngs = New-Object System.Collections.Generic.List[string]
$japaneseTrackLabels = New-Object System.Collections.Generic.List[string]
foreach ($key in $japaneseTrackKeys) {
    $sourcePath = Join-Path (Join-Path $PSScriptRoot 'japanese_track') ($key + '.png')
    if (-not (Test-Path -LiteralPath $sourcePath)) {
        throw "Missing Japanese track source icon: $sourcePath"
    }
    $previewPath = Join-Path $individualPreviewRoot ($key + '.png')
    $ddsPath = Join-Path $iconRoot ($key + '.dds')
    $report = [JxpIconTools]::ProcessSheet(
        $sourcePath,
        @($previewPath),
        @($ddsPath),
        1,
        1,
        $ddsTemplate)
    $cropReports.Add("[$key]")
    $cropReports.Add($report)
    $japaneseTrackPngs.Add($previewPath)
    $japaneseTrackLabels.Add($key)
}

[JxpIconTools]::CreatePngContactSheet(
    $japaneseTrackPngs.ToArray(),
    $japaneseTrackLabels.ToArray(),
    8,
    'JXP Japanese government reform track',
    (Join-Path $previewRoot 'jxp_japanese_track_preview.png'))

[JxpIconTools]::CreatePngContactSheet(
    $masterPngs.ToArray(),
    $masterLabels.ToArray(),
    9,
    'JXP route government reform icons',
    (Join-Path $previewRoot 'jxp_all_routes_preview.png'))

Write-Utf8LfLines `
    -Path (Join-Path $PSScriptRoot 'crop_report.txt') `
    -Lines $cropReports.ToArray()
Write-ValidationReport -Keys $allKeys
