# JXP Runtime Portability And R5 Static Admission

Date: `2026-07-13` (America/Los_Angeles)
Evidence class: `STATIC_PASS; ADMITTED_STATIC_INPUT`
Runtime claim: `NONE`

This immutable phase report records the current-host portability slice and the
strict static admission of the authentic R5 source. It is not a second status
page. Current TODO state, permissions, and execution order remain owned by
`JXP_SHARED_DEVELOPMENT_LEDGER.md`.

## Scope

- Ported the acceptance helper from the previous Windows profile to the
  original development machine without weakening its fixed-root contract.
- Fixed the canonical isolated EU4 user-data root at `C:\JXP_Acceptance` because
  the current Documents path contains whitespace and is unsafe for EU4 1.37.5's
  `-userdir` parser.
- Pinned the current trusted Git executable and regenerated the reviewed
  external Python/Windows/Git toolchain baseline.
- Extended R5's executable matrix contract with the authentic save's exact
  filename, size, SHA-256, header, player state, completed missions, mission
  slots, and BOM-prefixed series counts.
- Added the read-only `verify-r5-escrow` command and adversarial tests for save,
  sidecar, backup, and tamper rejection.
- Removed the obsolete R5/R13 matrix blockers. This does not create a runtime
  collection; R13 still requires all sixteen exact READY parents.

No gameplay, map, localisation, asset, descriptor, release version, or runtime
payload candidate was changed.

## Current Host Contract

- Repository: `C:\Users\Fiber Memory\Documents\GitHub\JapMod`
- Game root: `D:\Steam\steamapps\common\Europa Universalis IV` (read-only)
- Daily user-data: `C:\Users\Fiber Memory\Documents\Paradox Interactive\Europa Universalis IV`
- Isolated acceptance root: `C:\JXP_Acceptance`
- Trusted Git: `C:\Program Files\Git\mingw64\bin\git.exe`
- Trusted Git SHA-256: `C39B1B4F7A57935BBEADF246DC2466316619453A6A9DA77C4A9C6BD6D8FB21D3`
- Python: `3.12.13`, 64-bit CPython
- NumPy / Pillow / PyYAML: `2.3.5` / `12.2.0` / `6.0.3`
- External-toolchain baseline SHA-256: `366E0DE99BC3E7E1498A33168FED0FB462A17CEDE49E7C7B1AE8798E2BEFC3AF`
- External-toolchain records: `12`, records object SHA-256
  `C4CB26991A422C00AE4FFB526E957BB0D7F934A591688CC70E396CFD5ACDBD62`

The baseline matcher accepted every current file and distribution record. The
acceptance helper's canonical userdir remains ASCII, whitespace-free, ordinary,
and disjoint from the daily profile.

## R5 Static Admission

The final executable matrix SHA-256 is
`44969E94D0EF349C0554681E5B8789E12A6D0A431300C010D319DD2BB9C7A268`.
`verify-r5-escrow` returned `ADMITTED_STATIC_INPUT` for:

- `autosave.eu4`: 36,371,037 bytes, SHA-256
  `9F6DD96A60C7B9F583C22F87E7DA2F5C659E2EDC14723483A077B7AFD73A8BEF`;
- EU4 text validation: 1,794,479 lines, maximum brace depth 7;
- semantic identity object SHA-256:
  `E39CCED590778C9CFAFEB91B07F19CED8071C14723BAE95B8B1C6EF9C7224C0D`;
- provenance JSON: 2,326 bytes, SHA-256
  `03DD5ED8504E7D70A33153010CF8A411A66C9FA3BFB23294A4DD94567F0939DA`;
- hash manifest: 368 bytes, SHA-256
  `9B1018EEBDBF15B6F9101971191D43C6DFAE686CA0D92BA30EBF451E1DFAFA34`;
- content identity JSON: 2,292 bytes, SHA-256
  `BC0DCBECE19D32D85F9F50ECFF08350DE6B7A9024A044A2D30A1A8F44C85759D`;
- all three named backup ZIPs, their exact hashes, and descriptor versions
  `0.23.0`, `0.23.1`, and `0.23.1`.

The first strict run rejected a mistyped in-code hash for the third backup. The
disk file, recovery report, and ledger agreed; the constant had omitted one
hexadecimal character and was corrected. The rerun then passed. No external
file was modified.

## Static Verification

- Acceptance helper: `56/56` tests passed.
- Main release gate: `26/26` checks passed; `250/250` gameplay files parsed;
  `229/229` core tests passed.
- Combined main/map gate: `0 errors / 0 warnings` in map, history, content,
  compatibility, and asset validators; all 137,382 selectable dates and 120
  combined mission profiles passed.
- Runtime oracle: current, covering 88 provinces, 63 history states, 37 event
  options, 5 origins / 33 map missions, and 88 unification rows.
- Repository and installed `eu4-modding` skills both passed `quick_validate`;
  all `11/11` files are byte-identical.
- `git diff --check` passed.
- Two pre-existing advisory country-name-pool warnings remain for CJP and EJP;
  they are not counted as static gate failures and must be watched in fresh
  runtime logs.

## Permission And Remaining Boundary

- EU4, Launcher, dowser, bootstrapper, and observer were not started.
- Static preflight matched all `12/12` protocol/gameplay pins and found no
  related process or map conflict.
- The ordinary `C:\JXP_Acceptance` root was created. Git-derived current
  main/map snapshots have fingerprints `0D908FF8AE38...` and `9AA1589FFD69...`;
  the current main-only snapshot and all seven declared run fixtures are also
  installed.
- The exact PROBE playset is configured with only those two descriptors.
  Configure receipt SHA-256 is
  `DB5E3D7F4DC4006D7E50CC8E3790FB35D0CB699D5F09B8C1BA171B40DD410A0A`;
  isolated `dlc_load.json` is 168 bytes / SHA-256
  `B8729255CC37A01E64CB7514FB2B62D964B8B4527FCD3F82A7D559C14D7853D7`.
- Daily `dlc_load.json` remained 147 bytes / SHA-256
  `D317B6EE90457871B3B03A9A056B23935CDDCA651A7A9F85E349E7DCF207AF72`;
  daily `launcher-v2.sqlite` remained 176,128 bytes / SHA-256
  `A27BF04DDDA447A858649DCE70694996B7F0505FA04C9DF785E0ABD660D9FA30`.
- No `before-session`, PROBE session, R1-R12 collection, or R13 closure was
  created.
- `ADMITTED_STATIC_INPUT` is not `RUNTIME_PASS` and closes no migration TODO.
- A new explicit user instruction is still required before starting EU4. PROBE
  must pass before any gameplay scenario, and all scenarios must use the final
  matrix SHA above.
