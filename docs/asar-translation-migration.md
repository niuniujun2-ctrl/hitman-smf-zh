# Electron app.asar UI 汉化跨版本迁移（SMF Mod Manager 实测）

场景：SMF Release.zip 更新覆盖了 `Mod Manager/resources/app.asar`，汉化版被打回英文。
恢复思路：**不重新翻译** —— 用旧汉化版与新英文版做 difflib 对齐，自动提取
EN→CN 翻译对，合并进新版，重打包。

> 已验证：SMF 2.33.40 汉化版 → 2.33.42 英文原版：10 个文件、166 个去重翻译对、
> 1087 处中文全部迁回，语法检查通过。

## 关键事实

- Mod Manager 是 SvelteKit 应用，UI 字符串硬编码在 `_app/immutable/**/*.js`
  （无 i18n 框架）；汉化 = 直接把字符串字面量换成中文。
- 每次构建的文件名带内容 hash（`nodes/7.80f9018a.js` → `nodes/7.3c3e17cd.js`），
  但 **`nodes/N` 编号稳定对应**；chunks 按语义名对应（index / navigation / paths /
  singletons / stores / utils / …）。
- 相邻版本间 UI 代码差异极小（差异块仅 7-25 字节）。
- 版本差大时先核对结构：
  `diff <(cd old && find . -type f | sort) <(cd new && find . -type f | sort)`

## 工具

- `npx --yes @electron/asar extract <app.asar> <dir>` / `pack <dir> <app.asar.new>`
  （首次运行会下载包，国内网络慢可重试；extract 输出目录必须为空或不存在）
- `node --check <file.js>` 语法验证
- 本仓库 `migrate_asar_translation.py`（difflib 对齐，核心工具）

## 工作流

1. **盘点** `resources/`：找汉化痕迹 —— `app.asar.hanhua.old`（旧汉化版）、
   `app.asar.bak`（初始原版）、现役 `app.asar`。
2. **备份**当前英文原版：`cp app.asar app.asar.english.<版本>`（回滚用）。
3. **解包**两个 asar 到 `old/` 与 `new/`。
4. **建文件对**（工具自动）：`nodes/N.*.js` 按编号；chunks 按语义名。
5. **提取翻译对**（工具自动）：对每对文件用 `difflib.SequenceMatcher` 遍历 opcodes；
   `replace` 块中"旧版含中文、新版纯英文、两段均 <500 字符"→ 翻译对 `(new, old)`，去重入表。
6. **合并**（工具自动）：`equal`/`insert` 用新块、`delete` 丢弃、`replace`（旧含中文）用旧译块；
   **输出文件名必须用新版 hash 名**（import 引用依赖）。
7. **语法验证**：所有合并后 js 过 `node --check`。
8. **统计校验**：合并目录中文数 ≈ 旧汉化版中文数（实测旧 1091 / 新 1087；
   差 4 = 新版删掉的旧文案）。
9. **重打包替换**：`asar pack` → 拷回 `resources/app.asar`；
   回读验证（解包后 `grep -c "模组本地化" <解包目录>/_app/immutable/**/*.js` > 0）。
10. 清理解包临时目录，保留 `translation_pairs.json`。

## 为什么不能"字符串一键替换"（实测反例）

对 2.33.42 英文原版直接做 166 对的字面替换，结果：

- 替换总数 **1719 处**（目标仅 ~1087 处中文）——超量部分全是误伤：
  第三方 chunk（utils / tippy / marked）里相同片段被连带替换，单文件最高 **657 处**；
- `page.` → `页面的置顶帖。` 把 `s.page.subscribe` 改成了 `s.页面的置顶帖。sub`，
  语法直接损坏；
- 5 个文件 `node --check` 失败。

**结论：必须块级对齐（difflib opcodes），按位置应用翻译，天然规避标识符/属性名误伤。**

## 陷阱

- 合并文件必须沿用新版文件名（内容 hash 变了，import 引用会断）。
- difflib 全文对齐约 15s/文件（72KB），10 个文件 2-3 分钟，正常。
- 新版 UI 大改（新增页面/文件）时旧翻译对覆盖不全 —— 合并后中文数明显少于旧版，
  此时对新文件单独补译。
- 用 releases 页面 HTML 拿资产可能因 GitHub 前端加载失败而失败，直接走 API。
