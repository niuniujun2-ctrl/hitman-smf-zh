#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
迁移 Electron app.asar 的 UI 汉化到新版本(无需重新翻译)。

原理: 旧汉化版与新英文版同源构建(SvelteKit/编译产物), 文件结构几乎一致。
用 difflib 对齐, replace 块中"旧版含中文 / 新版纯英文"的对就是翻译对,
把它们合并回新版文件, 再用 @electron/asar pack 重打包。

用法:
    python migrate_asar_translation.py <old_hanhua_dir> <new_english_dir> <merged_out_dir> [--pairs out_pairs.json]

    old_hanhua_dir  解包后的旧汉化版 asar 目录(含中文)
    new_english_dir 解包后的新英文版 asar 目录
    merged_out_dir  合并输出目录(结构复制 new, 翻译从 old 套入)
    --pairs         可选: 导出去重后的 EN→CN 翻译对照表 JSON

匹配规则(SvelteKit hash 文件名):
    nodes/N.*.js 按编号对应; chunks 按语义名(index/navigation/paths/singletons/stores/utils/...)
    其余文件: 同名同内容, 直接复制 new 版。
输出: 合并目录 + 中文统计。合并文件用新版文件名(import 引用依赖 hash)。

作者: AI 助手「苍娜」(Hermes Agent)｜人类监督: niuniujun2-ctrl
"""
import argparse, difflib, json, os, re, sys

CN_RE = re.compile(r'[\u4e00-\u9fff]')
MAX_BLOCK = 500  # 汉化块上限字符, 防止把大段代码差异当翻译


def collect_files(root):
    out = {}
    for dirpath, _dirs, files in os.walk(root):
        for f in files:
            if f.endswith('.js'):
                rel = os.path.relpath(os.path.join(dirpath, f), root)
                out[rel] = os.path.join(dirpath, f)
    return out


def match_pairs(old_files, new_files):
    """按 SvelteKit 规则建立 (old_rel, new_rel) 文件对。"""
    pairs = []
    new_set = set(new_files)
    old_set = set(old_files)
    # 完全同名
    for rel in sorted(old_set & new_set):
        pairs.append((rel, rel))
    # nodes/N.*.js 按编号
    for rel in sorted(old_set):
        m = re.match(r'nodes/(\d+)\.', rel)
        if m and rel not in new_set:
            cands = [r for r in new_set if re.match(r'nodes/%s\.' % m.group(1), r)]
            if cands:
                pairs.append((rel, cands[0]))
    # chunks 语义名
    for rel in sorted(old_set):
        if rel.startswith('chunks/') and rel not in new_set:
            stem = re.sub(r'\.[a-f0-9]+\.js$', '.js', rel)
            cands = [r for r in new_set if r.startswith('chunks/') and re.sub(r'\.[a-f0-9]+\.js$', '.js', r) == stem]
            if cands:
                pairs.append((rel, cands[0]))
    return pairs


def extract_and_merge(old_path, new_path):
    """返回 (翻译对列表, 合并文本, 用过的翻译块数)。"""
    old_txt = open(old_path, encoding='utf-8', errors='replace').read()
    new_txt = open(new_path, encoding='utf-8', errors='replace').read()
    sm = difflib.SequenceMatcher(None, old_txt, new_txt, autojunk=False)
    out, pairs, used = [], [], 0
    for op, i1, i2, j1, j2 in sm.get_opcodes():
        ob, nb = old_txt[i1:i2], new_txt[j1:j2]
        if op == 'equal':
            out.append(nb)
        elif op == 'insert':
            out.append(nb)           # 新版新增代码
        elif op == 'delete':
            pass                     # 旧版独有, 丢弃
        elif op == 'replace':
            if CN_RE.search(ob) and not CN_RE.search(nb) and len(ob) < MAX_BLOCK and len(nb) < MAX_BLOCK:
                out.append(ob)       # 旧版翻译块
                pairs.append((nb, ob))
                used += 1
            else:
                out.append(nb)       # 代码变更
    return pairs, ''.join(out), used


def main():
    ap = argparse.ArgumentParser(description='迁移 Electron app.asar UI 汉化到新版本')
    ap.add_argument('old_dir')
    ap.add_argument('new_dir')
    ap.add_argument('out_dir')
    ap.add_argument('--pairs', default=None, help='导出 EN→CN 翻译对照表 JSON 路径')
    args = ap.parse_args()

    old_files = collect_files(args.old_dir)
    new_files = collect_files(args.new_dir)
    file_pairs = match_pairs(old_files, new_files)

    # 复制 new 目录骨架(非 js 文件原样保留)
    if os.path.exists(args.out_dir):
        import shutil; shutil.rmtree(args.out_dir)
    for rel, src in new_files.items():
        dst = os.path.join(args.out_dir, *rel.split('/'))
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        open(dst, 'w', encoding='utf-8').write(open(src, encoding='utf-8', errors='replace').read())

    all_pairs, seen = [], {}
    total_cn_old = total_cn_new = 0
    for orel, nrel in file_pairs:
        if orel == nrel:
            continue  # 同名同内容文件已原样复制
        pairs, merged, used = extract_and_merge(old_files[orel], new_files[nrel])
        dst = os.path.join(args.out_dir, *nrel.split('/'))
        open(dst, 'w', encoding='utf-8').write(merged)
        all_pairs.extend(pairs)
        cn_old = len(CN_RE.findall(open(old_files[orel], encoding='utf-8', errors='replace').read()))
        cn_new = len(CN_RE.findall(merged))
        total_cn_old += cn_old; total_cn_new += cn_new
        print(f'{nrel}: 翻译块={used} 中文 {cn_old} -> {cn_new}')

    for en, zh in all_pairs:
        if en not in seen:
            seen[en] = zh

    print(f'\n文件对: {len(file_pairs)}, 翻译对(去重): {len(seen)}, 中文总数: {total_cn_old} -> {total_cn_new}')
    print(f'提示: 用新版文件名(import hash 引用), 语法验证: node --check 所有合并 js')

    if args.pairs:
        json.dump([{'en': en, 'zh': zh} for en, zh in seen.items()],
                  open(args.pairs, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        print(f'翻译对照表已保存: {args.pairs}')


if __name__ == '__main__':
    main()
