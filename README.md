# hitman-smf-zh —— HITMAN「Simple Mod Framework」Mod Manager 界面汉化

> 🤖 本仓库的代码与文档由 **AI 编写**（AI 助手「苍娜」，运行于 Hermes Agent）；人类作者负责需求、验收与发布。详见「关于本项目」。

给 [Simple Mod Framework](https://github.com/atampy25/simple-mod-framework)（HITMAN 世界三部曲的模组框架，简称 SMF）的 **Mod Manager 图形界面**做的简体中文汉化，附带一套 **SMF 更新后"重套汉化"的迁移工具**。

- 覆盖 Mod Manager 界面主要文案：**166 条翻译对**（简中约 1087 字）；
- 核心工具 `migrate_asar_translation.py`：**不重新翻译** —— 用旧汉化版与新英文版做
  difflib 对齐，自动提取/合并全部译块、重打包；
- 已在 **SMF 2.33.40 汉化 → 2.33.42 英文原版** 的跨版本迁移上实测（10 个文件、
  1087 处中文全部迁回、语法检查通过）。

## 背景：为什么需要"迁移"

SMF 的 Mod Manager 是 Electron 应用，UI 文案硬编码在
`Mod Manager/resources/app.asar`（SvelteKit 构建产物，没有 i18n 框架）。
汉化 = 直接替换 `.js` 里的字符串字面量。

**SMF 每次更新都会覆盖 app.asar，汉化被打回英文** —— 迁移工具用来把翻译套回新版。

## 用法

```bash
# 0) 依赖: Node.js（npx）+ Python 3.8+
# 1) 解包两个 app.asar（旧汉化版 + 新英文版）
npx --yes @electron/asar extract "<旧汉化 app.asar>" old/
npx --yes @electron/asar extract "<新英文 app.asar>" new/

# 2) 对齐合并（去重后的翻译对会同时导出）
python migrate_asar_translation.py old/ new/ merged/ --pairs translation_pairs.json

# 3) 语法验证 + 重打包
find merged -name "*.js" -exec node --check {} \;
npx --yes @electron/asar pack merged app.asar.new

# 4) 替换 resources/app.asar（先备份）→ 打开 Mod Manager 检查
```

细节、验证清单与陷阱：**[docs/asar-translation-migration.md](docs/asar-translation-migration.md)**；SMF↔游戏版本对照表：[docs/smf-version-map.md](docs/smf-version-map.md)。

## 为什么不提供"字符串一键替换"

对 2.33.42 英文原版做过字面替换实测（教训）：

- 166 对里有 `page.`、`Edit the` 这类**片段**，直接跑全文替换会把代码改烂：
  `s.page.subscribe` → `s.页面的置顶帖。sub`，语法直接损坏；
- 替换总计 1719 处（目标仅 ~1087 处），超量部分全是第三方 chunk 里的连带误伤
  （单文件最高 657 处）；5 个文件 `node --check` 失败。

**唯一安全路径是块级对齐（difflib opcodes）**：按位置应用翻译，天然规避标识符/属性名误伤。

## 翻译对说明

`translation_pairs.json` = `[{"en": "...", "zh": "..."}, ...]`，由旧汉化版与英文版
对齐提取 + 人工去重。SMF 新版出现新增 UI 时，合并后中文数会少于旧版 —— 对新文案
单独补译并追加进表即可。

## 许可与声明

代码以 MIT 许可开源（见 LICENSE）。本仓库**非官方汉化**：SMF 版权归
[atampy25](https://github.com/atampy25) 所有；本仓库不包含任何 SMF 或游戏本体文件。

## 关于本项目

- **本仓库代码与文档由 AI 编写**：迁移工具、文档与实测验证由 AI 助手 **苍娜**
  （运行于 Hermes Agent）完成。
- 人类作者 [@niuniujun2-ctrl](https://github.com/niuniujun2-ctrl) 负责提出需求、验收与发布。
