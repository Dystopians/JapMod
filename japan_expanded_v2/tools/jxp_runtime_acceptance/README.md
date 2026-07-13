# JXP Runtime Acceptance Helper

This standard-library-only helper prepares and seals reproducible EU4 runtime
evidence. It has no launch command and does **not** start EU4, dowser, Paradox
Launcher, or an observer process. `configure-playset` may atomically replace only
the dedicated acceptance root's `dlc_load.json`; the helper never edits the daily
`dlc_load.json` or any `launcher-v2.sqlite`.

`runtime_scenarios.json` is the executable evidence contract, not a second status
document. The canonical TODO/status source remains
`japan_expanded_v2/dev_logs/JXP_SHARED_DEVELOPMENT_LEDGER.md`.

## Fixed locations and safety contract

Production runtime operations accept only these ordinary, canonical roots:

```text
Repository:  C:\Users\meizhanxuan\Documents\GitHub\JapMod
Game:        D:\Steam\steamapps\common\Europa Universalis IV
Daily data:  C:\Users\meizhanxuan\Documents\Paradox Interactive\Europa Universalis IV
Acceptance:  C:\Users\meizhanxuan\Documents\JXP_Acceptance
```

- The repository and game installation are read-only inputs. The helper resolves
  Windows Documents with `SHGetKnownFolderPath(FOLDERID_Documents)` instead of
  trusting `USERPROFILE`, `HOME`, or `HOMEDRIVE`/`HOMEPATH`. The pinned
  `launcher-settings.json` must derive the same daily data root.
- The acceptance root is an ASCII, whitespace-free ordinary directory, disjoint
  from the daily root. The former
  `...\Paradox Interactive\Europa Universalis IV - JXP Acceptance` path is
  forbidden: EU4 1.37.5 can truncate that valued option at the space before `-`
  and fall back into the daily root.
- All four roots, every traversed pin, deployment, descriptor, evidence input,
  and output must be free of symlinks, junctions, reparse indirection, drive/UNC
  escape, and non-canonical spelling.
- Session evidence is restricted to the reserved direct root
  `C:\Users\meizhanxuan\Documents\JXP_Acceptance\jxp_runtime_evidence`.
  `--evidence-root` cannot redirect it into `mod`, logs, screenshots, saves, or
  another ordinary directory. Recovery cleanup authenticates the sealed session,
  canonical location, and active nonce before removing any partial output.
- `preflight`, `deploy`, `before-session`, `collect`, and `close-release` verify
  these twelve ordered pins for EU4 v1.37.5.0 Inca (491d): `eu4.exe`, the empty
  game-root `userdir.txt`, `launcher-settings.json`,
  `missions/Japanese_Missions.txt`, `missions/DOM_Japanese_Missions.txt`,
  `missions/00_Generic_missions.txt`,
  `missions/01_Generic_European_Missions.txt`, `missions/Asian_Missions.txt`,
  `common/cb_types/00_cb_types.txt`,
  `common/wargoal_types/00_wargoal_types.txt`,
  `common/imperial_reforms/01_china.txt`, and `events/ChineseEmpire.txt`. The
  vanilla manifest is pinned at SHA-256
  `1abc720a6ee8e930f60d644a49aa6c2c231c05dac559cb4c465d6d391a05f2a9`.
  A changed install stops the protocol.
- Deployments are content-addressed ordinary copies under the acceptance root's
  `mod` directory. Their runtime manifests are rebuilt from the claimed immutable
  Git commit, then compared byte-for-byte with the installed snapshot. Marker
  metadata is never treated as an authority.
- Only runtime payload is copied: `common`, `decisions`, `events`, `gfx`,
  `history`, `interface`, `localisation`, `missions`, the companion `map`
  directory, `descriptor.mod`, and `thumbnail.png`. Development material,
  source/preview/backup trees, build scripts, source art, bytecode, `tools`,
  `dev_logs`, `localisation_source`, and `AGENTS.md` are excluded.
- Every state-mutating command except `observe-process` refuses to run while an
  EU4/Launcher-family process is active. `observe-process` is the sole command
  that writes while exactly one `eu4.exe` is running. The isolated playset must
  contain exactly the supplied descriptors, in contract order, with the exact
  component/version/revision/dependency/DLC mask for the selected scenario.
- `before-session` requires a non-empty reference to the user's explicit launch
  permission. It seals the exact executable argv, twelve pins, canonical roots,
  payloads, playset, daily configuration, a full daily top-level recursive VFS
  inventory, the isolated configuration/runtime-output/artifact-source surfaces,
  inputs, fixtures, parent collections, scenario contract, and (for R12) oracle.
  The daily inventory fully hashes critical configuration and small files; it
  records complete topology and metadata for `mod`, and uses bounded content
  sampling for most files above 4 MiB. Critical surfaces include `dlc_load.json`,
  `launcher-v2.sqlite`, `settings.txt`, `pdx_settings.txt`,
  `gameplaysettings.txt`, `.launcher-cache`, `cache`, `logs`, `save games`, and
  `Screenshots`.
- `observe-process` must run while the visible `eu4.exe` is alive. It records the
  real CIM executable path, creation time, PID, and Windows-parsed argv and
  accepts only the pinned executable with one lower-case, non-repeated
  `-userdir=C:\Users\meizhanxuan\Documents\JXP_Acceptance` argument.
- `collect` runs only after all relevant processes exit. It rejects stale or
  malformed evidence, archive escape, token-spoofed saves, fake image extensions,
  changed payload/playset/pins/oracles/daily files, missing parent lineage, and
  incomplete manual assertion roles. It scans only fresh session logs for blocker
  patterns. A clean automated gate never substitutes for manual UI/engine facts.
- If a prepared session cannot be completed, use `abort-session`. Do not delete
  or hand-edit the active lock.

The execution matrix uses schema 2. Configure receipts, sessions and their seals,
evidence manifests, collections and their seals, abort records, and R13 closure
records use schema 4; older or partial records fail closed.

## Static preparation — no launch

Run from the repository root with Python 3.11 or newer:

```powershell
$tool = 'japan_expanded_v2\tools\jxp_runtime_acceptance\runtime_acceptance.py'
$repo = 'C:\Users\meizhanxuan\Documents\GitHub\JapMod'
$game = 'D:\Steam\steamapps\common\Europa Universalis IV'
$dailyUserData = 'C:\Users\meizhanxuan\Documents\Paradox Interactive\Europa Universalis IV'
$userData = 'C:\Users\meizhanxuan\Documents\JXP_Acceptance'
$validationPython = '<Python 3.10+ with tools\jxp_map_validation\requirements-validation.txt installed>'

New-Item -ItemType Directory -Force $userData | Out-Null
python $tool preflight --repo $repo --game-root $game --user-data $dailyUserData
```

Deploy the pinned current main + map candidate, then a current main-only snapshot
for existing-save scenarios:

```powershell
python $tool deploy --label current `
  --revision 2bf24123e41f86324cfc6b9780b9a89cd3919c6e `
  --user-data $userData

python $tool deploy --label current-main --main-only `
  --revision 2bf24123e41f86324cfc6b9780b9a89cd3919c6e `
  --user-data $userData
```

Deploy immutable legacy main-only sources when the matrix phase requires them:

```powershell
python $tool deploy --label legacy-027 --main-only `
  --revision 8a5962628014e696bda764bcad10bfd3faee188e `
  --user-data $userData

python $tool deploy --label legacy-025 --main-only `
  --revision 6e461e2e47a839a77b2e376ce61ceb317d393320 `
  --user-data $userData
```

Install all seven verified, non-release console setup fixtures:

```powershell
python $tool install-fixtures --user-data $userData
```

The installer validates `run_fixtures/manifest.json`, UTF-8/no-BOM encoding,
ordinary-file identity, and exact hashes before an atomic no-clobber commit. The
fixtures are `DEBUG_FIXTURE_SETUP` evidence only:

- `JXP_ACC_R4_025_emperor_only.txt`
- `JXP_ACC_R6_protected_targets.txt`
- `JXP_ACC_R8_no_heartland.txt`
- `JXP_ACC_R8_restore_heartland.txt`
- `JXP_ACC_R8_missing_church.txt`
- `JXP_ACC_R8_missing_burghers.txt`
- `JXP_ACC_R10_foreign_emperor_same_unlock.txt`

Use only the fixture named by the selected matrix contract. Record its console
screenshot and before/after save roles in the generated evidence manifest. These
files cannot prove natural history, event cadence, production mission rewards,
normal state formation, or a missing legacy serialization regression.
The two missing-estate negatives must be separate forks of the same saved parent
whose other R8 conditions are already proven eligible. Reload that common parent
after each negative; never stack the two fixture effects.

Configure the isolated root for a scenario with the exact descriptor paths
printed by `deploy`:

```powershell
python $tool configure-playset PROBE --user-data $userData `
  --descriptor "$userData\mod\jxp-acceptance-current-main-<hash>.mod" `
  --descriptor "$userData\mod\jxp-acceptance-current-map-<hash>.mod"
```

Do not enable Graphical Map Improvements, the Chinese localisation mod, or any
unrelated mod. Companion map sessions always start a new campaign. R11 alone
uses the matrix-pinned Mandate of Heaven disabled mask; other phases use their
declared DLC state. The written JSON keys are exactly `enabled_mods` followed by
`disabled_dlcs`; enabled descriptors are ordered main then map as
`mod/<descriptor filename>`. R11's exact disabled entry is
`dlc/dlc066_mandate_of_heaven/dlc066.dlc`.

## Authorized runtime sequence

Static argument analysis is not a VFS proof. After the user gives explicit
permission to start EU4, run PROBE before R1-R12. With every relevant process
stopped, create a sealed schema-4 session and cite that exact authorization:

```powershell
$permission = '<message/thread reference containing explicit launch permission>'
$main = "$userData\mod\jxp-acceptance-current-main-<hash>.mod"
$map = "$userData\mod\jxp-acceptance-current-map-<hash>.mod"

python $tool before-session PROBE --repo $repo --game-root $game `
  --user-data $userData --daily-user-data $dailyUserData `
  --permission-reference $permission `
  --descriptor $main --descriptor $map
```

The command prints the session directory and creates its canonical
`evidence_manifest.json`. Only after that succeeds, start the pinned executable
visibly with exactly one argument:

```powershell
& "$game\eu4.exe" "-userdir=$userData"
```

At the main menu, while `eu4.exe` is still running, bind the observed process:

```powershell
python $tool observe-process '<session-directory>'
```

For PROBE, capture the main menu and exit without starting or loading a campaign.
For R1-R12, follow the selected matrix phase, use `JXP_ACC_*` save names, and
collect every named artifact role. Fully exit EU4 and Launcher before collection.

Complete the generated manifest rather than inventing a new one:

- Fill each operator artifact `paths` entry, or every exact `cases` path for a
  screenshot set. Automatic log/settings/process/VFS roles remain helper-bound.
- Change an assertion from `PENDING` only after it is actually observed. A
  terminal assertion needs `status`, a substantive `note`, reviewer `attestor`,
  timezone-aware `attested_at` (UTC recommended), and the **exact complete** set
  of supporting artifact roles. Terminal status is only `PASS`, `FAIL`, or
  `BLOCKED`.
- Fill every declared fixture use with its console screenshot and before/after
  save role plus an honest note.
- Do not copy old screenshots or saves into a new session. Artifacts must be new
  or changed since the sealed before-session inventory.

Then collect with the canonical manifest path:

```powershell
python $tool collect '<session-directory>' `
  --evidence-manifest '<session-directory>\evidence_manifest.json'
```

`collection.json` and `collection.seal.json` are immutable schema-4 results. Only
`READY_FOR_LEAD_REVIEW` with all automated checks and manual assertions passing
is an eligible parent. It is still not a scenario-pass declaration by itself.
Repeated `--artifact <path>` arguments create hashed appendix records only; they
cannot satisfy any named evidence role.

If the run is interrupted or invalid:

```powershell
python $tool abort-session '<session-directory>' --reason '<specific reason>'
```

Abort requires every relevant process to be stopped and a non-empty reason. It
writes a sealed `abort.json`, retires the nonce-bound active lock, and preserves
the session directory for audit; it does not delete the session.

Multi-phase scenarios need separate sessions and exact parent/input edges. R4
uses `legacy-025-generate`, `legacy-027-generate`, and `current-migrate`; R6 uses
`current-map-new` and `current-main-old-save`. Pass every matrix-declared
`ROLE=PATH` through repeated `--parent-collection` and `--input-save` arguments.

## R12 exact oracle evidence

R12 is pinned to
`japan_expanded_v2_map/tools/jxp_map_validation/generated/runtime_oracle_pack.json`
with schema `jxp_runtime_oracle_pack/v1` and SHA-256
`8a2141cd4c1cc94d729d539d47f01db5e636fb1c206b2393fe9aaf253973ad22`.
The pack seals 258 exact live-source pins (12 main, 180 map, 66 vanilla) plus the
semantic matrix SHA-256
`730bf1c7f0ec03b7be0827a5ddb641254cc8d2bc3881cf279c58610625cadcd5`.
Its 282 typed cases are 88 rendering rows, 12 bookmark states, 45 history
boundaries, 6 non-boundary sliders, 37 event-option results, 5 origin profiles,
88 unification provinces, and 1 annual lifecycle. They expand to 697 exact
bindings across 19 evidence roles.

`before-session R12` verifies all live source pins, cross-checks the deployable
runtime-member subset against the candidate Git snapshots, then copies the pack
into the session. `collect` repeats those checks and rejects any changed pointer,
expected object, binding, or oracle byte. Five checklist roles must be strict JSON
with this identity:

```json
{
  "schema": "jxp_runtime_typed_case_evidence/v1",
  "scenario_id": "R12",
  "role": "<exact checklist role>",
  "oracle_pack_sha256": "8a2141cd4c1cc94d729d539d47f01db5e636fb1c206b2393fe9aaf253973ad22",
  "cases": {
    "<exact case id>": {
      "status": "PASS",
      "note": "<specific observation>",
      "attestor": "<reviewer>",
      "attested_at": "<UTC ISO-8601 timestamp>",
      "oracle_pointer": "<exact case pointer>",
      "oracle_object_sha256": "<exact expected object hash>",
      "observed": {"<measured field>": "<measured value>"}
    }
  }
}
```

Each checklist must contain exactly the cases bound to its role. The helper
expands the accepted result into all 697 sealed evidence bindings; aggregate
notes or a screenshot count cannot replace this typed evidence.

The five strict checklist cardinalities are:

- `r12_ports_straits_positions_checklist`: 88
- `r12_history_state_checklist`: 63
- `r12_event_option_checklist`: 37
- `r12_origin_identity_checklist`: 5
- `r12_unification_88_province_checklist`: 89 (88 provinces plus lifecycle)

Regenerate/check the pack only through the committed generator:

```powershell
& $validationPython japan_expanded_v2_map\tools\jxp_map_validation\build_runtime_oracles.py `
  --game-root $game --main-mod "$repo\japan_expanded_v2" --check
```

## R13 finite release closure

R13 is not a game session; `before-session R13` is rejected. `close-release`
requires exactly sixteen ready parent collections, ten distinct named artifacts,
and a separate strict assertion manifest. Supply every entry as the exact
`ROLE=PATH` declared by `runtime_scenarios.json`:

```powershell
python $tool close-release --repo $repo --game-root $game `
  --daily-user-data $dailyUserData --user-data $userData `
  --parent-collection '<role>=<collection.json>' `
  --artifact '<role>=<artifact path>' `
  --assertion-manifest '<R13 assertion manifest.json>' `
  --output-root "$userData\jxp_release_closure"
```

Repeat both role arguments until the declared sets are exact. The command never
creates a game session or active lock and is retry/idempotence safe. It seals a
finite `closure.json`; the output defaults to `jxp_release_closure` and must be an
ordinary direct child of the canonical acceptance root. There must be no active
session or process. If the R13 contract still contains any matrix blocker, the
command fails before parent sealing or static gates and emits no blocked closure.
It does not close open-ended maintenance obligations.
Invoke it with the same Python 3.11+ validation environment required by
`japan_expanded_v2_map/tools/requirements-validation.txt` (NumPy, Pillow, and
PyYAML); the R13 skill gate deliberately refuses an incomplete interpreter.

The sixteen parent roles are `protocol_probe_collection`, `r1_collection`,
`r2_collection`, `r3_collection`, `r4_025_collection`, `r4_027_collection`,
`r4_current_collection`, `r5_collection`, `r6_new_collection`,
`r6_old_collection`, `r7_collection`, `r8_collection`, `r9_collection`,
`r10_collection`, `r11_collection`, and `r12_collection`.

The ten artifact roles are `r13_assertion_result_manifest`,
`r13_evidence_lineage_index`, `r13_main_static_gate_output`,
`r13_combined_static_gate_output`, `r13_mandate_vanilla_manifest_output`,
`r13_ideas_shape_and_mutation_output`, `r13_ledger_validation_output`,
`r13_skill_validation_output_if_changed`,
`r13_daily_configuration_final_hashes`, and `r13_canonical_ledger_update`.
The artifact named `r13_assertion_result_manifest` and the separate
`--assertion-manifest` must be different files with different bytes.

All ten role artifacts are strict semantic JSON, not free-form claims. The
assertion-result artifact must reproduce all 65 PASS assertions from the sixteen
parents; the lineage artifact must reproduce every collection/session/contract,
artifact, assertion, snapshot, input, upstream-parent, fixture, and R12 oracle
hash edge. Each gate declaration uses `jxp_r13_static_gate_output/v3` and must
name the helper's exact fixed argv, zero exit-code vector, role-specific PASS
checks, and canonical summary. It is not trusted by itself: on the first
`close-release`, the helper runs seven controlled static processes with
`shell=False` (main, combined, Mandate, idea/mutation, ledger, and
repo/installed skill validation), rejects `eu4.exe`, Launcher, dowser,
bootstrapper, `-userdir`, and `-SkipMainModValidation`. Windows and System32 are
resolved through WinAPI rather than environment variables; nested PowerShell is
an explicit absolute path. Each process receives a complete minimal environment
instead of the caller's environment. Python children run through the fixed
`-I -S -B` R13 runner: the approved standard library remains first, repository
validator roots follow it, and only exact NumPy/Pillow/PyYAML distribution files
copied into a temporary isolated site are appended last. `PYTHONSAFEPATH=1` is
also explicit; the caller's site, `.pth`, `sitecustomize`, cwd, and `PYTHONPATH`
cannot supply imports. The combined gate may execute only the exact
Git-verified `skills/eu4-modding/scripts/check_mission_series_overlap.py` skill
entrypoint; that canonical file is an execution capability, while its directory
is never appended to `sys.path`. Before and after every command, the helper requires all
repository toolchain inputs—including ignored/untracked files—to equal one exact
Git HEAD and requires the installed skill to equal that Git-derived skill tree.
Python/Windows/Git/quick-validator bytes are separately compared with the
Git-tracked `r13_external_toolchain_baseline.json`. It also checks the runtime
payload and stopped-process guard, and seals that toolchain revision/baseline,
the complete effective environment, raw stdout/stderr base64, sizes, framed
hashes, exact argv, cwd, UTC times, exit codes, and required-marker proofs.
Per-process raw output is bounded while both pipes are being drained at 1 MiB,
and aggregate raw output is bounded at 4 MiB. The eleven caller-controlled
closure inputs share an 8 MiB pre-parse/copy budget; the complete staged or
replayed closure tree, including its serialized JSON, is capped at 32 MiB. Every idempotent replay reruns all seven
controlled gates as current authorization, verifies the historical sealed
record separately, and never overwrites the closure. The daily-state receipt binds the complete final daily
configuration and VFS hashes. The ledger receipt uses
`jxp_r13_ledger_update/v2`: its entry id must select one unique
`### YYYY-MM-DD - ENTRY-ID - title` section under the unique
`## Update Journal`, containing exactly one strict
`jxp-r13-journal-json` fenced block. That object binds the release status,
candidate, matrix, parent-lineage hash, all sixteen ordered parent collection
hashes, blockers, no-game/no-overclaim booleans, and UTC update time; the
receipt also binds its `entry_sha256` and the canonical ledger file hash. Only
headings and the exact JSON fence outside real Markdown code fences count. LF,
CRLF, and CR are the only line boundaries; control/Unicode pseudo-separators,
reserved-info aliases, fenced examples, nested fake headings, duplicate blocks,
unclosed fences, and raw HTML blocks fail closed. Tokens scattered through other journal entries do not count. R13 records
twelve computed automated checks (parent lineage + ten artifacts + manual
manifest) and cannot set `automated_checks_passed` independently.

The separate schema-4 assertion manifest has `scenario_id` `R13`, phase
`closure`, and all six ordered assertions at `PASS` with non-empty note,
attestor, UTC timestamp, and their exact supporting roles:

- `r13_all_assertions_resolved`:
  `[r13_assertion_result_manifest, r13_evidence_lineage_index]`
- `r13_no_overclaim`:
  `[r13_assertion_result_manifest, r13_canonical_ledger_update]`
- `r13_payload_and_lineage_recorded`: `[r13_evidence_lineage_index]`
- `r13_static_gates_exact_payload`:
  `[r13_main_static_gate_output, r13_combined_static_gate_output,
  r13_mandate_vanilla_manifest_output, r13_ideas_shape_and_mutation_output,
  r13_ledger_validation_output, r13_skill_validation_output_if_changed]`
- `r13_logs_and_daily_configuration_clean`:
  `[r13_daily_configuration_final_hashes]`
- `r13_process_scope_honest`: `[r13_canonical_ledger_update]`

The current matrix's only R13 blocker is
`r13_authentic_r5_collection_missing`; closure remains not-ready until an
authentic ready R5 parent exists. In the currently pinned matrix, the R5 and R13
blockers record that this external source is not yet available and therefore
intentionally prevent a READY R5 parent. `close-release` therefore refuses the
current contract and does not create a `MATRIX_CONTRACT_BLOCKED` R13 artifact.
Once the authentic source is acquired,
update both blocker records through a reviewed matrix change, then rerun PROBE
and R1-R12 under the new matrix SHA before attempting R13. A collection from the
old matrix cannot be relabelled or reused across that boundary.

## Legacy boundary

Commit `8a5962628014e696bda764bcad10bfd3faee188e` is a genuine 0.27.0 source and
can generate all ten 0.28 migration inputs. The repository's earliest complete
source is 0.25.0. R5 therefore requires the unmodified original issue
`autosave.eu4`, or a real pre-0.24.2 engine-generated failing save (0.24.1 or
earlier) with complete provenance. Never synthesize, flag-edit, relabel, or
substitute a later save.
