# JXP Runtime Acceptance Helper

This standard-library-only helper prepares reproducible EU4 runtime evidence. It
does **not** launch EU4, dowser, or Paradox Launcher, and it never edits
`launcher-v2.sqlite` or `dlc_load.json`.

`runtime_scenarios.json` is an execution/evidence matrix, not a second status
document. The only current TODO/status source is
`japan_expanded_v2/dev_logs/JXP_SHARED_DEVELOPMENT_LEDGER.md`.

## Safety contract

- The repository and game installation are read-only inputs.
- Deployments are ordinary, content-addressed directories under the user's EU4
  `mod` directory. No junction, symbolic link, or descriptor path points at the
  Git checkout.
- Only runtime payload is copied: `common`, `decisions`, `events`, `gfx`,
  `history`, `interface`, `localisation`, `missions`, the companion `map`
  directory, `descriptor.mod`, and `thumbnail.png`.
- `tools`, `dev_logs`, `localisation_source`, source art, backups, and
  `AGENTS.md` are excluded.
- Payload hashes are verified before the outer `.mod` descriptor is written.
  Existing unrelated files are never removed or overwritten.
- `before-session` refuses a playset unless its enabled mods exactly equal the
  descriptors supplied on the command line. This prevents accidental evidence
  from the daily Chinese/GMI playset.
- `collect` runs only after EU4 and Launcher have exited and scans fresh logs for
  parse/unknown-object errors, `mission.cpp:353`, and `national_idea8`.

## Commands

Run from the repository root with Python 3.11 or newer:

```powershell
$tool = 'japan_expanded_v2\tools\jxp_runtime_acceptance\runtime_acceptance.py'
$userData = 'C:\Users\meizhanxuan\Documents\Paradox Interactive\Europa Universalis IV'
$game = 'D:\Steam\steamapps\common\Europa Universalis IV'

python $tool preflight --game-root $game --user-data $userData
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

The command returns the exact installed descriptor paths and names. After the
user explicitly permits Launcher/EU4 startup, use the Launcher UI to create an
isolated playset containing exactly the intended returned descriptor(s). Do not
enable Graphical Map Improvements, the Chinese localisation mod, or any other
mod. The companion map always requires a new campaign.

With EU4 and Launcher stopped and the isolated playset active, create the
before-session evidence record. Pass the exact installed descriptor paths:

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
scan still does not replace the matrix's manual UI, engine, or save/reload
assertions.

## Legacy boundary

Commit `8a5962628014e696bda764bcad10bfd3faee188e` is a genuine 0.27.0 source and
can generate all ten 0.28 migration inputs. The repository's earliest complete
source is 0.25.0. A genuine pre-0.24.2 serialized regression fixture therefore
requires the original problem `autosave.eu4`, or a real pre-0.24.1 release and
engine-generated failing save. Do not synthesize, flag-edit, or relabel a newer
save as that evidence.
