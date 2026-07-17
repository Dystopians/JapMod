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
Repository:  C:\Users\Fiber Memory\Documents\GitHub\JapMod
Game:        D:\Steam\steamapps\common\Europa Universalis IV
Daily data:  C:\Users\Fiber Memory\Documents\Paradox Interactive\Europa Universalis IV
Acceptance:  C:\JXP_Acceptance
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
  `C:\JXP_Acceptance\jxp_runtime_evidence`.
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
  `-userdir=C:\JXP_Acceptance` argument.
- `collect` runs only after all relevant processes exit. It rejects stale or
  malformed evidence, archive escape, token-spoofed saves, fake image extensions,
  changed payload/playset/pins/oracles/daily files, missing parent lineage, and
  incomplete manual assertion roles. It scans only fresh session logs for blocker
  patterns. A clean automated gate never substitutes for manual UI/engine facts.
- If a prepared session cannot be completed, use `abort-session`. Do not delete
  or hand-edit the active lock.

The execution matrix uses schema 2. Sessions, their seals, active locks, process
observations, and abort records use schema 5 so each run binds its clean
control-plane revision from `before-session` through `collect`. Configure
receipts, evidence manifests, collections and their seals, and R13 closure
records use schema 4; older or partial records fail closed.
If the control plane changes after `before-session`, `collect` refuses the run
before copying evidence. `abort-session` remains available after that drift to
authenticate the sealed session and release its active lock. Abort validates the
stored schema, seal, canonical location, and nonce without consulting the current
scenario, matrix hash, candidate, or VFS coverage, so a legitimate stale session
cannot strand the lock. Historical schema-4 sessions remain immutable history
and cannot be upgraded or reused by this helper.

## Static preparation — no launch

Run from the repository root with Python 3.11 or newer:

```powershell
$tool = 'japan_expanded_v2\tools\jxp_runtime_acceptance\runtime_acceptance.py'
$repo = 'C:\Users\Fiber Memory\Documents\GitHub\JapMod'
$game = 'D:\Steam\steamapps\common\Europa Universalis IV'
$dailyUserData = 'C:\Users\Fiber Memory\Documents\Paradox Interactive\Europa Universalis IV'
$userData = 'C:\JXP_Acceptance'
$validationPython = '<Python 3.10+ with tools\jxp_map_validation\requirements-validation.txt installed>'

New-Item -ItemType Directory -Force $userData | Out-Null
python $tool preflight --repo $repo --game-root $game --user-data $dailyUserData
```

`ready_for_safe_deploy` is true only when the control-plane worktree is clean,
the matrix candidate is an ancestor of that control-plane HEAD, and both live
runtime manifests plus the portable outer descriptors are unchanged from the
candidate. A false `current_candidate.ready` is a hard stop, even when all game
pins match. `deploy --label current` and `deploy --label current-main` repeat
this guard and require the explicit matrix candidate revision; omitting
`--revision` would resolve to control-plane commit B and is rejected.

Revalidate the recovered external R5 source before preparing any R5 session:

```powershell
python $tool verify-r5-escrow `
  --escrow-root 'C:\JXP_R5_Escrow\20260713_original_machine'
```

This command is read-only. It binds the original save, three named 0.23.x
backups, provenance JSON, hash manifest, and content-identity JSON to the
current matrix. `ADMITTED_STATIC_INPUT` means only that the source is eligible
for a future R5 session; it is not a READY collection or runtime pass.

### Forming a new immutable candidate

`runtime_scenarios.json` embeds the candidate's 40-character Git OID, so a new
candidate cannot be created by one self-referential commit. Use exactly two
stages:

1. Create **payload commit A** containing every intended runtime-whitelist byte,
   including new files and deletions. Record its exact OID. Do not deploy it yet.
2. Without changing any runtime-whitelist byte, update the matrix, ledger,
   README examples, generated oracle metadata, and other acceptance control
   files to pin commit A. Re-run all static/helper/oracle/skill gates, then create
   **control-plane commit B**.
3. From clean commit B, prove that every live runtime file is tracked and that
   `git diff --quiet <A> -- <all runtime roots>` succeeds. Deploy commit A while
   running the helper and evidence contracts from commit B.

Any runtime-byte change after commit A invalidates A. Restart both stages rather
than amending the matrix to an uncommitted tree, pointing it at commit B, or
waiving the Git-snapshot comparison. Development-only documentation and tests
may change in commit B because they are excluded from the deployed payload.

Deploy the pinned current main + map candidate, then a current main-only snapshot
for existing-save scenarios:

```powershell
python $tool deploy --label current `
  --revision 80637e065881f0bac4fd424e0c6100c19e8f5da7 `
  --user-data $userData

python $tool deploy --label current-main --main-only `
  --revision 80637e065881f0bac4fd424e0c6100c19e8f5da7 `
  --user-data $userData
```

Pinned revision deployment does not trust a `git archive` ZIP. The helper reads
only the runtime whitelist from the resolved commit with the pinned Git binary,
authenticates each bounded `cat-file --batch` body against its blob OID, writes
and re-hashes a unique staging checkout, then atomically exposes the complete
tree. A transient body mismatch gets at most three reads; malformed protocol,
oversized blobs, and development-only members fail closed. A detected staged
file hash mismatch gets at most three writes, and each refreshed authenticated
fetch gets its own three-read ceiling; a partial checkout is never exposed and
is removed on failure.

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
`disabled_dlcs`; enabled descriptors keep the declared dependency order, main
then companion map, as `mod/<descriptor filename>`. This order is not used as
evidence for exact-path precedence: any critical external provider must instead
be byte-identical to the authoritative JXP payload. R11's exact disabled entry is
`dlc/dlc066_mandate_of_heaven/dlc066.dlc`.

## Authorized runtime sequence

Static argument analysis is not a VFS proof. After the user gives explicit
permission to start EU4, run PROBE before R1-R12. With every relevant process
stopped, create a sealed schema-5 session and cite that exact authorization:

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

The isolated userdir deliberately does not inherit the daily Documents
profile. Missing language, UI-scale, display, audio, and gameplay preferences
are expected and do not mean that the Mod VFS failed to load. Prove loading
from the fresh isolated logs and the visible main menu, not from familiar
preferences. If EU4 presents its first-run language control, wait until that
control is visibly focused and click the intended choice. Do not press or
buffer `Enter`, `Space`, or another keyboard confirmation while the screen is
loading: the queued input can propagate into country selection and start a
campaign. After the main menu appears, capture it and send no further input.

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
`768462c4ce12782342cdcad3083737dec7a18d6b64f94cf2e9fbdf60bc4685d4`.
The pack seals 258 exact live-source pins (13 main, 180 map, 65 vanilla) plus the
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
  "oracle_pack_sha256": "768462c4ce12782342cdcad3083737dec7a18d6b64f94cf2e9fbdf60bc4685d4",
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
requires exactly seventeen ready parent collections, ten distinct named artifacts,
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

The seventeen parent roles are `protocol_probe_collection`, `r1_collection`,
`r2_collection`, `r3_collection`, `r4_025_collection`, `r4_027_collection`,
`r4_028_pre_political_collection`, `r4_current_collection`, `r5_collection`, `r6_new_collection`,
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
assertion-result artifact must reproduce all 72 PASS assertions from the seventeen
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
Every `cat-file --batch` response body is independently reframed and matched to
its Git object OID before its SHA-256 enters the manifest; an authenticated body
mismatch permits at most three immediate reads, while all other protocol errors
fail without retry.
Python/Windows/Git/quick-validator bytes are separately compared with the
Git-tracked `r13_external_toolchain_baseline.json`. It also checks the runtime
payload and stopped-process guard, and seals that toolchain revision/baseline,
the complete effective environment, raw stdout/stderr base64, sizes, framed
hashes, exact argv, cwd, UTC times, exit codes, and required-marker proofs.
The complete live result/toolchain proof is validated before the temporary
Python tree is removed. Post-cleanup and historical replay validation requires
that temporary root to be absent, reconstructs its expected dependency/wrapper
records from persistent approved inputs, and still rechecks every persistent
Git, external-toolchain, payload, and installed-skill input. The authoritative
validator always acquires that guard itself; only a private pure comparator may
consume an already acquired live guard inside the pre-cleanup critical section.
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
candidate, matrix, parent-lineage hash, all seventeen ordered parent collection
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

The current matrix has no declared R5 or R13 blocker because the authentic R5
source is recovered and pinned. Release closure nevertheless remains not-ready
until a complete, current-matrix R5 collection and every other exact parent
exist; missing parents fail before any closure is written. PROBE and R1-R12 must
all run under this final matrix SHA after explicit user launch permission. A
collection from an older matrix cannot be relabelled or reused across that
boundary.

## Legacy boundary

Commit `8a5962628014e696bda764bcad10bfd3faee188e` is a genuine 0.27.0 source and
can generate all ten 0.28 migration inputs. The repository's earliest complete
source is 0.25.0. R5 uses the recovered unmodified original issue
`autosave.eu4`, now pinned by filename, size, SHA-256, semantic identity, and
complete provenance. Never synthesize, flag-edit, relabel, resave, or substitute
a later save.
