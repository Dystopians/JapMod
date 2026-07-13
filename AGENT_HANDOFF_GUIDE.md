# JapMod Agent Handoff Guide

This repository is the portable development source for **Japan Expanded V2 / 日轮诸道** and its
**Japan 88-province companion map**. It intentionally excludes the proprietary EU4 installation,
Steam Workshop content, saves, launcher databases, runtime logs, and local backups.

This guide explains how to enter and leave the project safely. It is not a second status page:
always read `japan_expanded_v2/dev_logs/JXP_SHARED_DEVELOPMENT_LEDGER.md` for the current versions,
open TODOs, risks, validation evidence, and newest update journal.

## Repository Layout

| Path | Purpose |
| --- | --- |
| `japan_expanded_v2/` | Main gameplay mod and canonical shared ledger |
| `japan_expanded_v2_map/` | Mandatory 88-province companion map and executable compatibility contract |
| `japan_expanded_v2.mod` | Portable launcher descriptor for the main mod |
| `japan_expanded_v2_map.mod` | Portable launcher descriptor for the companion map |
| `skills/eu4-modding/` | Repository-pinned Codex skill, references, and validation scripts |
| `AGENTS.md` | Repository-wide agent entry point |

The two top-level `.mod` files use `path="mod/..."` so they can be copied into the EU4 user-data
`mod` directory. If the repository is kept elsewhere, generate local descriptor copies with absolute
paths to the two repository subdirectories; do not commit host-specific paths.

## First Ten Minutes

1. Read, in order:
   - `skills/eu4-modding/SKILL.md`
   - root `AGENTS.md`
   - `japan_expanded_v2/AGENTS.md`
   - `japan_expanded_v2/dev_logs/JXP_SHARED_DEVELOPMENT_LEDGER.md`
   - the phase report named by the relevant ledger entry
2. For map or cross-mod work, additionally read:
   - `japan_expanded_v2_map/AGENTS.md`
   - `japan_expanded_v2_map/dev_logs/BASELINE_LOCK.txt`
   - `japan_expanded_v2_map/tools/jxp_map_validation/main_compatibility_contract.json`
3. Confirm the installed game is the pinned EU4 version recorded by the ledger and keep the game root read-only.
4. Run the smallest relevant static baseline before editing.
5. Claim an existing ledger TODO, set one owner, and add a `STARTED` journal entry. Add a new stable TODO ID only when no existing item covers the work.

## Local Setup

Keep the Git checkout outside the Steam installation. A typical checkout is:

```text
<Documents>/GitHub/JapMod/
```

For launcher use, either copy the two mod directories into:

```text
<Documents>/Paradox Interactive/Europa Universalis IV/mod/
```

or keep the Git checkout in place and create local, uncommitted launcher descriptors whose `path`
values point to the checkout subdirectories. Never commit a username-specific absolute path.

The companion map requires the main mod, a new campaign, and the compatibility boundaries recorded
in `BASELINE_LOCK.txt`. Do not combine it with another overhaul of Japanese map bitmaps, areas,
province history, or the Nippon trade node.

## Development Rules

- Preserve user changes and edit generator sources when a generated file has an established owner.
- Main gameplay changes must remain compatible with the companion map in the same development slice.
- Do not hard-reference optional companion tags, province IDs, areas, or missions from the main mod.
- Mission, route, idea, reform, tag, and map changes require migration analysis or an explicit new-campaign boundary.
- Active Chinese localisation follows the existing UTF-8 BOM and EU4SpecialEscape pipeline; Markdown remains ordinary UTF-8.
- Do not describe static validation as an in-game result.
- Do not launch EU4, the launcher, or an observer game without explicit user permission.

## Required Static Gates

From the repository root, set the host-specific game path and run:

```powershell
$repo = (Get-Location).Path
$game = 'D:\Steam\steamapps\common\Europa Universalis IV'

powershell.exe -NoProfile -ExecutionPolicy Bypass -File `
  "$repo\skills\eu4-modding\scripts\validate_jxp_mod.ps1" `
  -ModPath "$repo\japan_expanded_v2" `
  -GameRoot $game

powershell.exe -NoProfile -ExecutionPolicy Bypass -File `
  "$repo\japan_expanded_v2_map\tools\validate_all.ps1" `
  -GameRoot $game `
  -MainMod "$repo\japan_expanded_v2"
```

If the embedded skill changes, also run the Codex skill validator available on the host. Record the
exact command and result in the shared ledger. Runtime acceptance remains pending until the user
explicitly authorizes a current-version game run.

## Git Workflow

1. Work on a focused branch or worktree; do not develop directly on `main`.
2. Keep unrelated changes out of the commit.
3. Run both static gates before publishing.
4. Update the shared ledger in the same slice with files touched, evidence class, remaining risks, and next TODO.
5. Review `git diff --check`, the staged diff, and large-file limits before pushing.
6. Open a draft pull request unless the user explicitly requests otherwise.

## Handoff Checklist

Before giving the project to another agent, state:

- branch, commit, and pull-request link;
- exact files and systems changed;
- what was deliberately not changed;
- main, combined, and skill validation results;
- whether evidence is `STATIC_PASS`, `RUNTIME_PASS`, `USER_OBSERVED`, or `PENDING_RUNTIME`;
- the stable ledger TODO that should be taken next;
- any required new-campaign, migration, DLC, or compatibility constraints.

## Copy-Paste Continuation Prompt

The block below is a portable task prompt for continuing on the original development machine. It is
not a second status page: the receiving agent must derive current versions, TODOs, blockers, hashes,
and evidence from the fetched Git HEAD and canonical ledger.

```text
你正在原开发机上继续 Dystopians/JapMod。完整目标是完成 canonical ledger 中的全部 TODO；不得缩小目标，不得把 STATIC_PASS、旧版本反馈或不完整场景写成 RUNTIME_PASS。

一、取得完整交接历史

仓库：https://github.com/Dystopians/JapMod.git
草稿 PR：https://github.com/Dystopians/JapMod/pull/1

在 Steam/EU4 安装目录之外操作。若本机已有 checkout，先检查 remote、HEAD、tracked/untracked/ignored 状态；保存所有用户改动，不得 reset、覆盖或清理。工作树不干净时使用新的 clone 或独立 worktree。

新 clone 的建议命令：

git clone https://github.com/Dystopians/JapMod.git <Documents>\GitHub\JapMod
cd <Documents>\GitHub\JapMod
git fetch origin pull/1/head:handoff/pr-1
git switch -c codex/original-machine-runtime handoff/pr-1
git status --short --branch
git rev-parse HEAD
git ls-remote origin refs/pull/1/head

本地 HEAD 必须与实时 refs/pull/1/head OID 完全相同；不同时立即停止并报告交接 ref 漂移。不得退回 origin/main、相近 commit、手工复制文件或未经验证的 archive。版本、TODO、blocker、schema、角色数和 hash 一律从该 HEAD 的 canonical ledger、runtime README 与 executable matrix 重新读取，不把本 prompt 中的流程概述当成状态证据。

二、先完整阅读并安装仓库固定 skill

按顺序完整读取：

1. skills/eu4-modding/SKILL.md
2. skills/eu4-modding/references/modding-reference.md 中的 Isolated Runtime Userdir Contract
3. AGENT_HANDOFF_GUIDE.md
4. 根 AGENTS.md
5. japan_expanded_v2/AGENTS.md
6. japan_expanded_v2/dev_logs/JXP_SHARED_DEVELOPMENT_LEDGER.md 全文
7. japan_expanded_v2_map/AGENTS.md
8. japan_expanded_v2_map/dev_logs/BASELINE_LOCK.txt
9. japan_expanded_v2_map/tools/jxp_map_validation/main_compatibility_contract.json
10. japan_expanded_v2/tools/jxp_runtime_acceptance/README.md
11. japan_expanded_v2/tools/jxp_runtime_acceptance/runtime_scenarios.json
12. 与当前 TODO 和 R5 直接相关的阶段报告。

先读取本机 skill-installer 的 SKILL.md，再把 checkout 中的 skills/eu4-modding 安装或更新为 %CODEX_HOME%\skills\eu4-modding 的精确镜像。repo skill 与 installed skill 必须逐文件同字节并分别通过 quick_validate；不要独立手改 installed copy。只有 lead agent 写 canonical ledger，subagent 只提交证据与摘要；不得创建第二份 current TODO/status 文档。

三、原机器首先只读找回真实 R5 原件

优先检查未修改的原问题 autosave.eu4，以及以下三个历史备份；<original-user-profile> 表示由 Windows 现场解析并核验的原用户 profile 根，不是应原样输入的目录名：

<original-user-profile>\Documents\Paradox Interactive\Europa Universalis IV\save games\autosave.eu4
<original-user-profile>\Documents\Paradox Interactive\Europa Universalis IV\mod\_jxp_backups\japan_expanded_v2_before_mission_layout_hotfix_20260709_154614.zip
<original-user-profile>\Documents\Paradox Interactive\Europa Universalis IV\mod\_jxp_backups\japan_expanded_v2_before_series_consolidation_20260709_161217.zip
<original-user-profile>\Documents\Paradox Interactive\Europa Universalis IV\mod\_jxp_backups\japan_expanded_v2_before_reform_visibility_hotfix_20260709_164900.zip

不得在原目录解压、改名、载入、重存、覆盖或清理。路径或文件名命中只产生 candidate，不证明它仍是旧档。先记录每个候选的绝对路径、文件名、size、SHA-256、创建/修改 UTC、ordinary/reparse 状态、机器/保管人和取得过程；再 no-clobber 地复制到 repo/game/daily/acceptance/runtime roots 之外、整条祖先链无 reparse 的普通 evidence escrow，并复核原件与副本 hash 完全相同。

R5 provenance 必须使用 matrix 当前声明的 exact keys；当前合同包括 source_machine_or_custodian、source_path_or_archive_name、original_filename、acquired_at_utc、chain_of_custody、size_bytes、sha256、eu4_version_if_known、jxp_version_or_release_evidence、original_failure_description、unaltered_bytes_attestation。若 matrix 已变化，以 executable contract 为准，不自行改字段名或省略字段。

原问题 autosave candidate 还必须只读核对已知内容身份：JAP、jxp_path_open_trade、DOM 与 JXP 同时存在于 country_missions、completed_missions 保留 JXP，以及六个 BOM-prefixed 历史 series key，并有可信证据把它绑定到 JXP 0.24.1 或更早和原故障。任一指纹或版本链不符即拒绝；其他 pre-0.24.2 candidate 也必须证明等价的真实引擎 serialization 与 bug-specific provenance。

禁止合成、flag-edit、mission serialization 编辑、重命名较新存档或用报告/截图/ZIP 文件名代替真实来源。只找到 ZIP 时先封存并由 lead review；它不自动等于可接受的 R5 save。不要把存档、ZIP、日志或本机备份提交到 GitHub。

四、原机器必须先完成 host-portability 审计，不能直接运行当前 helper

当前 runtime helper、README 和 matrix 固定的是交接机器上的 repo/game/daily/acceptance roots。原 Windows profile 路径含空格，因此其 Documents 下的 JXP_Acceptance 不满足 EU4 1.37.5 的 ASCII/no-whitespace userdir 合同。不得把当前硬编码路径直接搬过去，也不得使用旧的 Europa Universalis IV - JXP Acceptance 路径。

若正式 PROBE/R1-R13 将在原机器执行，先建立一个受审查的 portability 开发切片：

- 只读确认实际 EU4 v1.37.5.0 Inca (491d)、launcher-settings.json、gameDataPath、空 game-root userdir.txt 与所有 vanilla pins。
- 选择一个 ASCII、无空格、无引号、普通且整条祖先链无 reparse 的独立 acceptance root；C:\JXP_Acceptance 仅是候选，必须现场验证后才能固定。
- repo、game、daily、acceptance 四根必须互不包含；游戏根始终只读，daily 根仍由 Windows Known Folder 与 pinned launcher 双向证明。
- 修改 production guard 时仍须限制为一个明确、受审查的 canonical host contract；不得用环境变量、任意 CLI 路径、junction 或宽松 fallback 弱化 fail-closed 约束。
- 同步更新 helper、README、runtime_scenarios.json 的 exact argv、测试、必要的 external-toolchain baseline、canonical ledger 和所有受影响收据合同。
- portability 或 R5 blocker 变更会改变 matrix/toolchain hash；旧 matrix 的 session/collection 不得重标或复用，PROBE 与 R1-R12 必须在最终矩阵下全部重跑。

在 portability 切片通过主门禁、联合门禁、acceptance-helper tests、oracle --check、repo/installed skill validation 和 git diff --check 之前，不得运行 EU4。

五、权限与运行顺序

本 prompt 不构成启动 EU4、Launcher、dowser、bootstrapper 或 observer 的许可。正式运行前必须在当前任务中取得用户明确许可，并把该消息引用传给 before-session。不得通过 Launcher 启动；实际 argv 只能是 pinned eu4.exe 加恰好一个小写、非重复、无引号的 -userdir=<reviewed-canonical-root> 参数。运行中必须执行 observe-process，退出所有相关进程后才能 collect。

先取得并审查真实 R5 原件，再通过 reviewed matrix change 更新 R5 与 R13 blocker；不要在最终 matrix SHA 固定前提前跑场景。之后严格按 runtime README 与 runtime_scenarios.json 当时声明的拓扑顺序、全部 phase、exact parent/input edges、artifact roles 和 assertions 执行；PROBE 必须最先通过，R13 close-release 必须最后且不是游戏 session。每个 phase 都要生成当前合同要求的完整 sealed evidence，只有 matrix 当前定义为可供 lead review 的 collection 才可作为 parent；不得凭一个场景的部分角色提前关闭任何 TODO。

始终保持：游戏安装目录只读；不写 daily dlc_load.json、launcher-v2.sqlite 或 playset；不启用中文补丁、Graphical Map Improvements 或无关 Mod；companion map 场景只用新战役；不使用 symlink/junction/reparse、partial checkout、git archive payload、旧截图/存档或另一 matrix SHA 的证据；中断时只用 abort-session，不手删 active lock。

六、完成标准

只有真实 R5 bytes/provenance 通过、最终 matrix 固定、PROBE 与 R1-R12 的全部 matrix-declared phase 完成、R13 要求的 exact parent set 全部满足当前 schema/seal/readiness 合同、全部 assertion 有实际观察与完整 supporting roles、fresh logs/daily hashes/payload/playset/DLC/lineage 均无漂移，并且 R13 closure 与受控静态 gates 成功后，才可按 scenario-to-TODO 合同关闭对应 TODO。JXP-016 是持续维护义务；R13 只关闭当前 release slice，不得凭一次 closure 自动宣称永久 DONE。

最后由 lead agent只更新 canonical ledger 的 Current Snapshot、TODO evidence、Known Risks、newest-first Update Journal 和必要的 Historical Report Index；报告 exact branch/commit、runtime candidate、R5 path/size/hash/provenance、所有 collection/closure seal、静态与运行时结果、daily hashes及任何未完成项。未经用户另行授权，不 push、不上传 R5 原件、不改外部系统。
```

The repository was first imported to GitHub on 2026-07-10. The authoritative import record and all
subsequent project history belong in the ledger's newest-first Update Journal.
