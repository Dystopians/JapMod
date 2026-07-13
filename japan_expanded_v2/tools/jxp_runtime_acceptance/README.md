# JXP Runtime Acceptance Helper

This standard-library-only helper prepares reproducible EU4 runtime evidence. It
does **not** launch EU4, dowser, or Paradox Launcher, and it never edits
`launcher-v2.sqlite` or `dlc_load.json`.

`runtime_scenarios.json` is an execution/evidence matrix, not a second status
document. The only current TODO/status source is
`japan_expanded_v2/dev_logs/JXP_SHARED_DEVELOPMENT_LEDGER.md`.

## Safety contract

- The repository and game installation are read-only inputs.
- Deployments are ordinary, content-addressed directories under a dedicated
  acceptance user-data root's `mod` directory. Do not deploy into the daily
  EU4 user-data root. No junction, symbolic link, or descriptor path points at
  the Git checkout.
- Only runtime payload is copied: `common`, `decisions`, `events`, `gfx`,
  `history`, `interface`, `localisation`, `missions`, the companion `map`
  directory, `descriptor.mod`, and `thumbnail.png`.
- `tools`, `dev_logs`, `localisation_source`, `source`/`preview`/`backup*`
  subtrees, build scripts, source art, bytecode, and `AGENTS.md` are excluded.
- Deployment requires a clean committed source revision. Payload hashes are
  verified before the outer `.mod` descriptor is written. Reuse requires an
  exact marker, runtime-only manifest/file set, canonical owned paths, and a
  complete hash match; existing unrelated files are never removed or
  overwritten. Windows drive, UNC, backslash, symlink, junction, and archive
  path escapes are rejected.
- `before-session` refuses a playset unless its enabled mods exactly equal the
  descriptors supplied on the command line and those descriptors resolve to
  exact owned payload snapshots with the scenario's required components and
  versions. Current-release snapshots must also match the immutable
  `current_candidate_revision` pinned by `runtime_scenarios.json`; fixed legacy
  phases match their own pinned revisions. This prevents accidental evidence
  from the daily Chinese/GMI playset or a stale/tampered deployment.
- `collect` runs only after EU4 and Launcher have exited and scans fresh logs for
  parse/unknown-object errors, `mission.cpp:353`, and `national_idea8`. It also
  re-verifies payloads, the active playset, scenario-specific DLC log state, and
  the minimum number of distinct fresh screenshots/saves. Old explicit files
  are archived but do not satisfy those minimums. A clean log scan is not a
  manual UI pass.

## Commands

Run from the repository root with Python 3.11 or newer:

```powershell
$tool = 'japan_expanded_v2\tools\jxp_runtime_acceptance\runtime_acceptance.py'
$dailyUserData = 'C:\Users\meizhanxuan\Documents\Paradox Interactive\Europa Universalis IV'
$userData = 'C:\Users\meizhanxuan\Documents\Paradox Interactive\Europa Universalis IV - JXP Acceptance'
$game = 'D:\Steam\steamapps\common\Europa Universalis IV'

New-Item -ItemType Directory -Force $userData | Out-Null
python $tool preflight --game-root $game --user-data $dailyUserData
```

Install current main + companion snapshots without enabling or launching them:

```powershell
python $tool deploy --label current --user-data $userData
```

Install current main-only for old-save or no-map scenarios:

```powershell
python $tool deploy --label current-main --main-only --user-data $userData
```

Install the immutable 0.27.0 main-only source used to generate real 0.28
migration inputs:

```powershell
python $tool deploy --label legacy-027 --main-only `
  --revision 8a5962628014e696bda764bcad10bfd3faee188e `
  --user-data $userData
```

Install the immutable 0.25.0 main-only source used to generate genuine
pre-Toyotomi and pre-0.26 Hakko-visibility migration inputs:

```powershell
python $tool deploy --label legacy-025 --main-only `
  --revision 6e461e2e47a839a77b2e376ce61ceb317d393320 `
  --user-data $userData
```

The command returns the exact installed descriptor paths and names. Prepare the
dedicated root's own `dlc_load.json` with exactly the intended returned
descriptor(s); never edit or replace the daily root's `dlc_load.json` or
`launcher-v2.sqlite`. Do not enable Graphical Map Improvements, the Chinese
localisation mod, or any other mod. The companion map always requires a new
campaign.

Launcher 2026.6 has no verified playset/mod command-line selector. Although the
pinned EU4 executable contains a valued `userdir` option, its exact invocation
is not yet runtime-proven. After the user explicitly permits startup, the first
action must therefore be a visible, isolated `userdir` protocol probe. Accept
the protocol only if new logs/settings appear under `$userData` and the hashes
of the daily `dlc_load.json` and `launcher-v2.sqlite` remain unchanged. If the
probe fails, stop and reassess; do not silently fall back to the daily Launcher
configuration.

With EU4 and Launcher stopped and the isolated root's exact playset configured,
create the before-session evidence record. Pass the exact installed descriptor
paths:

```powershell
python $tool before-session R1 --user-data $userData `
  --descriptor "$userData\mod\jxp-acceptance-current-main-<hash>.mod" `
  --descriptor "$userData\mod\jxp-acceptance-current-map-<hash>.mod"
```

This prints a session directory. Follow the matching `R1`–`R13` matrix entry,
name test saves `JXP_ACC_*.eu4`, take the required screenshots, then fully exit
EU4 and Launcher. Collect and scan the result:

```powershell
python $tool collect '<session-directory>'
```

Use `--artifact <path>` to include an additional file located inside the EU4
user-data tree. `collection.json` records hashes and blocker matches; a clean
collection gate still does not replace the matrix's manual UI, engine, or
save/reload assertions.

Scenarios with more than one immutable input require separate evidence
sessions. For example, R4 must be recorded in all three phases:

```powershell
python $tool before-session R4 --phase legacy-025-generate --user-data $userData `
  --descriptor '<installed 0.25 main descriptor>'
python $tool before-session R4 --phase legacy-027-generate --user-data $userData `
  --descriptor '<installed 0.27 main descriptor>'
python $tool before-session R4 --phase current-migrate --user-data $userData `
  --descriptor '<installed current main descriptor>'
```

R6 likewise uses `current-map-new` and `current-main-old-save` so a companion
new campaign is never conflated with a main-only migration save.

R13 is a release-closure checklist over accepted R1-R12 evidence, not a game
session. `before-session R13` is deliberately rejected. Session schema 2 also
rejects older or incomplete records instead of treating missing snapshots as an
empty successful set.

## Legacy boundary

Commit `8a5962628014e696bda764bcad10bfd3faee188e` is a genuine 0.27.0 source and
can generate all ten 0.28 migration inputs. The repository's earliest complete
source is 0.25.0. A genuine pre-0.24.2 serialized regression fixture therefore
requires the original problem `autosave.eu4`, or a real pre-0.24.1 release and
engine-generated failing save. Do not synthesize, flag-edit, or relabel a newer
save as that evidence.
