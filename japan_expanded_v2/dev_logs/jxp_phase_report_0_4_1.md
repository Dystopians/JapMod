# 日轮诸道：日本扩展风味包 阶段性报告

更新时间：2026-07-09
当前版本：0.4.1
目标 Mod：`C:\Users\Fiber Memory\Documents\Paradox Interactive\Europa Universalis IV\mod\japan_expanded_v2`
游戏根目录：`D:\Steam\steamapps\common\Europa Universalis IV`

## 当前状态

0.4 主体已完成，0.4.1 增补了三大时代属性的低频纠偏事件。

已完成的全局计划模块：

- 0.1 MVP：基础 Mod 结构、三大时代属性、机制按钮、路线选择、KJP/CJP/EJP、基础理念/任务/事件。
- 0.2：政府机制界面注册、时代属性显示、长期投资、幕府政策桥接、政府界面贴图资源。
- 0.3：宗教与远海路线扩展、朱子礼制日本、吉利支丹/改革宗/海峡清真路线、东亚与太平洋方向任务。
- 0.3.5：宗教、文化和路线后续完善，避免改国体后退回通用任务树。
- 0.4：民众与海盗扩展，新增 IJP 一向净土国、WAK 倭寇联盟、一向宗灾难、倭寇联盟/海上奉行国路线、专属任务树与旗帜。
- 0.4.1：新增低频时代属性纠偏事件，使 `jxp_tenka_order`、`jxp_imperial_sanction`、`jxp_oceanic_opening` 在过高或过低时偶尔向中间回拉。

## 0.4.1 新增内容

新增文件：

- `events/jxp_balance_events.txt`
- `localisation_source/jxp_11_l_english_utf8_source.yml`
- `localisation/jxp_11_l_english.yml`
- `dev_logs/jxp_phase_report_0_4_1.md`

修改文件：

- `descriptor.mod`
- `../japan_expanded_v2.mod`
- `common/scripted_effects/jxp_debug_effects.txt`
- `C:\Users\Fiber Memory\.codex\skills\eu4-modding\references\modding-reference.md`

新增事件命名空间：

- `jxp_balance`

新增事件：

- `jxp_balance.1`：天下秩序过高时，诸藩请缓，轻微降低天下秩序。
- `jxp_balance.2`：天下秩序过低时，村法相争，轻微提高天下秩序。
- `jxp_balance.3`：天皇裁可过高时，禁里书札如雪，轻微降低天皇裁可。
- `jxp_balance.4`：天皇裁可过低时，冷落的御所，轻微提高天皇裁可。
- `jxp_balance.5`：海门外学过高时，港口异语太盛，轻微降低海门外学。
- `jxp_balance.6`：海门外学过低时，漂着之书，轻微提高海门外学。
- `jxp_balance.101-106`：隐藏冷却清除事件。

设计原则：

- 事件触发频率低，基础 MTTH 约 220-240 个月。
- 每个纠偏方向都有独立 20 年冷却 flag。
- 纠偏幅度只使用既有 `±5` scripted effects，避免冲掉玩家路线。
- 事件只调用已验证的三大属性同步 effect，继续保持变量与政府界面 power 同步。
- 文案不直接描述点数、阈值或机械消耗，机制变化由 EU4 tooltip 展示。

## 0.4 主体已完成要点

新增 tag：

- `IJP`：一向净土国
- `WAK`：倭寇联盟

核心文件：

- `common/country_tags/jxp_tags.txt`
- `common/countries/IJP - Ikko Commonwealth.txt`
- `common/countries/WAK - Wokou Confederacy.txt`
- `history/countries/IJP - Ikko Commonwealth.txt`
- `history/countries/WAK - Wokou Confederacy.txt`
- `common/ideas/jxp_route_ideas.txt`
- `common/government_reforms/jxp_japanese_reforms.txt`
- `events/jxp_ikko_events.txt`
- `events/jxp_wokou_events.txt`
- `decisions/jxp_10_popular_maritime_decisions.txt`
- `missions/jxp_10_popular_maritime_missions.txt`
- `localisation_source/jxp_10_l_english_utf8_source.yml`
- `localisation/jxp_10_l_english.yml`
- `gfx/flags/IJP.tga`
- `gfx/flags/WAK.tga`

旗帜状态：

- `IJP.tga` 与 `WAK.tga` 均为 128x128 RGB TGA。
- 高分辨率 imagegen 源和 128px 预览保存在 `gfx/flags/source/`。

## 本地化规则

不要直接编辑 `localisation/*.yml` 中的中文文本。该目录内的活跃本地化是 EU4SpecialEscape 转义文本。

正确流程：

1. 编辑 `localisation_source/*_utf8_source.yml`。
2. 用技能脚本生成活跃文件：

```powershell
& 'C:\Users\Fiber Memory\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' `
  'C:\Users\Fiber Memory\.codex\skills\eu4-modding\scripts\escape_eu4_special_localisation.py' `
  '<source_utf8_file>' `
  '<mod>\localisation\<active_file>.yml'
```

3. 检查活跃 `localisation/` 不应含原始 CJK 字符。

## 验证命令

标准校验：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File 'C:\Users\Fiber Memory\.codex\skills\eu4-modding\scripts\validate_eu4_mod.ps1' `
  -ModPath 'C:\Users\Fiber Memory\Documents\Paradox Interactive\Europa Universalis IV\mod\japan_expanded_v2' `
  -GameRoot 'D:\Steam\steamapps\common\Europa Universalis IV'
```

活跃本地化原始中文检查：

```powershell
rg -n "[\u4e00-\u9fff]" 'C:\Users\Fiber Memory\Documents\Paradox Interactive\Europa Universalis IV\mod\japan_expanded_v2\localisation'
```

## 游戏内测试建议

启用 debug 菜单：

- 点击 `调试：开启日轮诸道调试菜单`。

测试纠偏事件：

- 控制台触发 `event jxp_balance.1` 到 `event jxp_balance.6`。
- 或用 debug 数值档位把时代属性推到高/低，再等待自然触发。
- 触发后确认政府机制界面和事件 tooltip 中的数值变化一致。

测试 0.4 路线：

- 强制一向宗路线：`调试：强制路线：一向宗`
- 强制倭寇路线：`调试：强制路线：倭寇联盟`
- 检查国名、国旗、理念、政府改革、slot 11/12 任务树。

## 后续开发建议

优先分支：

- 0.4 后续：对马、濑户内、琉球专项任务进一步细化。
- 0.5：北海道/虾夷扩展，阿伊努、北前船、松前藩、北太平洋接触。
- 0.6：明朝/朝鲜互动扩展，册封、通信使、倭馆、朝鲜役替代路线。
- 0.7：后期近代化、洋式军制、财政改革、幕末危机风味。

接续开发注意事项：

- 必须使用 `eu4-modding` skill。
- 不修改 `D:\Steam\steamapps\common\Europa Universalis IV` 原版文件。
- 所有新增内容使用 `jxp_` 前缀。
- 不使用 `replace_path`，除非明确做总转或替换型大改。
- 新 route/tag 必须接入 shared trigger、route clear effect、debug cleanup、mission potential、ideas、flags、localisation。
- 继续避免在文案里直写机械消耗，保持 EU4 风格史述。
