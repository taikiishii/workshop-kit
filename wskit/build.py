#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""build.py  --  content/ から docs/ の教材サイトを生成する（workshop-kit 共通）

各教材リポジトリの build.py は、これを呼ぶだけの数行のラッパー。

構成（章ごとに1フォルダ・content と docs が対称）:
    site.toml               … この教材だけのちがい（URL・セクション・色）
    content/<章>/index.md   +  content/<章>/image/*   （あなたが編集するのはここだけ）
        │  python build.py
        ▼
    docs/<章>/index.html    +  docs/<章>/image/*  +  docs/<章>/qr.svg
    docs/assets/            … 共通部品（kit からコピー）＋ site-theme.css / site-config.js
    docs/index.html         … もくじ

依存: segno（QR生成）, Pillow（画像縮小・任意）  →  pip install segno pillow
"""

import html
import json
import os
import re
import shutil
import subprocess
import sys

from . import site as site_mod

KIT_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(KIT_DIR, "assets")
TEMPLATES = os.path.join(KIT_DIR, "templates")
FILES = os.path.join(KIT_DIR, "files")

# kit が各教材に配る共通部品。教材ごとに書きかえない。
KIT_ASSETS = ["deck.css", "deck.js", "index.css", "hakase.png", "hakase-face.png"]

# 生成物の目印。手で直しても次のビルドで消えることを伝える。
GENERATED = "このファイルは build が site.toml から生成します。直接編集しないでください。"


# ---- 小さな道具 -----------------------------------------------------------

def _read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def _write_if_changed(path, text, log):
    """中身が変わるときだけ書く（OneDrive の同期を無駄に起こさないため）。"""
    data = text.encode("utf-8")
    if os.path.exists(path) and open(path, "rb").read() == data:
        return False
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "wb") as f:
        f.write(data)
    log.append(path)
    return True


def _copy_if_changed(src, dst, log):
    if os.path.exists(dst) and open(dst, "rb").read() == open(src, "rb").read():
        return False
    os.makedirs(os.path.dirname(dst) or ".", exist_ok=True)
    shutil.copy2(src, dst)
    log.append(dst)
    return True


def parse_frontmatter(text):
    """先頭の --- ... --- をフロントマター(dict)として取り出し、(meta, body) を返す。"""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    if not text.startswith("---"):
        return {}, text
    lines = text.split("\n")
    end = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end = i
            break
    if end is None:
        return {}, text
    meta = {}
    for ln in lines[1:end]:
        if not ln.strip() or ln.strip().startswith("#"):
            continue
        if ":" in ln:
            k, v = ln.split(":", 1)
            # 値のうしろの # から先は書き手むけのメモなので落とす
            v = re.sub(r"\s+#.*$", "", v)
            meta[k.strip()] = v.strip()
    body = "\n".join(lines[end + 1:]).strip("\n")
    return meta, body


def make_qr(url, out_path):
    import segno
    q = segno.make(url, error="m")
    q.save(out_path, kind="svg", dark="#123a36", light="#ffffff",
           border=4, xmldecl=False, svgns=True, nl=False)


def kit_version():
    """ビルドに使った kit のコミット。git 管理下でなければ unknown。"""
    try:
        out = subprocess.run(["git", "-C", os.path.dirname(KIT_DIR), "rev-parse", "--short", "HEAD"],
                             capture_output=True, text=True, timeout=10)
        if out.returncode == 0 and out.stdout.strip():
            return out.stdout.strip()
    except Exception:
        pass
    return "unknown"


# ---- 画像 -----------------------------------------------------------------

def _copy_or_resize(src, dst, max_width):
    try:
        from PIL import Image
        im = Image.open(src)
        if im.width > max_width:
            h = int(im.height * max_width / im.width)
            im.resize((max_width, h)).save(dst)
            return
    except Exception:
        pass
    shutil.copy2(src, dst)


def copy_images(site, chapter_dir, body, out_dir, warn):
    """body 内の相対パス画像を content/<章>/… から docs/<章>/… へコピー。
    image/ でも image/index/ でも、サブフォルダ構成を保ったままコピーする
    （VS Code で貼り付けた画像がどのフォルダに入っても壊れないように）。"""
    content = os.path.join(site.root, "content")
    for rel in sorted(set(re.findall(r"\]\(([^)]+)\)", body))):
        if rel.startswith(("http://", "https://", "/", "#", "mailto:")):
            continue
        if not re.search(r"\.(png|jpe?g|gif|svg|webp)$", rel, re.I):
            continue
        src = os.path.join(content, chapter_dir, *rel.split("/"))
        if not os.path.exists(src):
            warn("画像が見つかりません: content/%s/%s" % (chapter_dir, rel))
            continue
        dst = os.path.join(out_dir, *rel.split("/"))
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        _copy_or_resize(src, dst, site.max_img_width)


# ---- 本文の下ごしらえ -----------------------------------------------------

SLIDE_SEP = re.compile(r"(\n[ \t]*-{3,}[ \t]*\n)")
PHOTO_TODO = re.compile(r"^>[ \t]*\U0001F4F7.*$\n?", re.M)
COL_SEP = re.compile(r"^[ \t]*:::[ \t]*$\n?", re.M)


def strip_photo_todos(body):
    """`> 📷 …` は写真をあとで入れるための執筆メモ。読者には出さない。

    deck.js は ⚠ と 💪 しか特別あつかいしないので、そのまま残すと
    博士がメモを読みあげる吹き出しになってしまう。
    メモを消したことで段組みの片方が空になったら、2段組をやめて全幅にする。
    """
    out = []
    for slide in SLIDE_SEP.split(body):
        if SLIDE_SEP.fullmatch(slide):
            out.append(slide)
            continue
        slide = PHOTO_TODO.sub("", slide)
        cols = COL_SEP.split(slide)
        if len(cols) == 3 and not cols[2].strip():
            slide = cols[0].rstrip() + "\n\n" + cols[1].strip() + "\n"
        out.append(slide)
    return "".join(out)


# ---- docs/assets（共通部品と、教材ごとの色・設定） -------------------------

def site_theme_css(site):
    """site.toml の色から assets/site-theme.css を作る。

    deck.css / index.css のあとに読み込ませて上書きする。
    """
    out = ["/* %s */" % GENERATED, "",
           ":root{",
           "  --accent:%s;" % site.accent,
           "  --accent-dark:%s;" % site.accent_dark,
           "  --accent-bright:%s;" % site.accent_bright,
           "}"]

    if site.palette:
        out += ["", "/* もくじカードの枠色（frontmatter の color:） */"]
        out += [".%s{ --frame:%s; }" % (k, v) for k, v in site.palette.items()]

    if site.level_palette:
        out += ["", "/* 難易度ラベルの背景色（frontmatter の level:） */"]
        out += [".%s .level{ background:%s; }" % (k, v) for k, v in site.level_palette.items()]

    lines = [s for s in site.sections if s.line]
    if lines:
        out += ["", "/* もくじのセクションの区切り線 */"]
        for sec in lines:
            if len(sec.line) == 1:
                bg = sec.line[0]
            else:
                bg = "linear-gradient(90deg,%s)" % ",".join(sec.line)
            out.append(".%s .section-line{ background:%s; }" % (sec.cls, bg))

    return "\n".join(out) + "\n"


def site_config_js(site):
    """site.toml の設定から assets/site-config.js を作る（deck.js が読む）。"""
    cfg = {
        "namespaces": site.namespaces,
        "mascot": {
            "auto": site.mascot_auto,
            "fullMin": site.mascot_full_min,
            "full": "../assets/hakase.png",
            "face": "../assets/hakase-face.png",
        },
    }
    return ("/* %s */\nwindow.DECK = %s;\n"
            % (GENERATED, json.dumps(cfg, ensure_ascii=False, indent=2)))


def build_assets(site, docs, log):
    out = os.path.join(docs, "assets")
    os.makedirs(out, exist_ok=True)

    for name in KIT_ASSETS:
        _copy_if_changed(os.path.join(ASSETS, name), os.path.join(out, name), log)

    # 教材ごとの画像（ロゴなど）は <教材>/assets/ に置く
    own = os.path.join(site.root, "assets")
    if os.path.isdir(own):
        for name in sorted(os.listdir(own)):
            src = os.path.join(own, name)
            if os.path.isfile(src):
                _copy_if_changed(src, os.path.join(out, name), log)

    _write_if_changed(os.path.join(out, "site-theme.css"), site_theme_css(site), log)
    _write_if_changed(os.path.join(out, "site-config.js"), site_config_js(site), log)
    _write_if_changed(os.path.join(out, "KIT_VERSION.txt"), kit_version() + "\n", log)

    # もくじの QR。章の QR と同じく index.html は付けない
    # （短いほうが QR が粗くなって読みとりやすく、ページに出す文字とも合う）
    qr = os.path.join(out, "qr.svg")
    make_qr(site.base_url, qr + ".tmp")
    if os.path.exists(qr) and open(qr, "rb").read() == open(qr + ".tmp", "rb").read():
        os.remove(qr + ".tmp")
    else:
        os.replace(qr + ".tmp", qr)
        log.append(qr)


def place_managed_files(site, docs, log):
    """kit が管理する設定ファイルを教材リポジトリに置く。

    手で直しても次のビルドで戻る。直したいときは kit 側（wskit/files/）を直す。
    """
    _copy_if_changed(os.path.join(FILES, "LICENSE.txt"),
                     os.path.join(docs, "LICENSE.txt"), log)
    _copy_if_changed(os.path.join(FILES, "gitignore"),
                     os.path.join(site.root, ".gitignore"), log)
    _copy_if_changed(os.path.join(FILES, "vscode-settings.json"),
                     os.path.join(site.root, ".vscode", "settings.json"), log)
    # GitHub Pages に「Jekyll で処理しないで」と伝える空ファイル
    nojekyll = os.path.join(docs, ".nojekyll")
    if not os.path.exists(nojekyll):
        os.makedirs(docs, exist_ok=True)
        open(nojekyll, "wb").close()
        log.append(nojekyll)


# ---- 章ページ -------------------------------------------------------------

def build_chapter(site, meta, body, chapter_dir, chapter_tpl, docs, warn):
    out_dir = os.path.join(docs, chapter_dir)
    os.makedirs(out_dir, exist_ok=True)

    copy_images(site, chapter_dir, body, out_dir, warn)
    body = strip_photo_todos(body)

    # 表紙に QR を自動挿入（最初の {cover} の直後）。QRは章フォルダ内 qr.svg
    if "{cover}" in body and "{qr:" not in body:
        body = body.replace("{cover}", "{cover}\n{qr: qr.svg}", 1)
    make_qr(site.base_url + chapter_dir + "/", os.path.join(out_dir, "qr.svg"))

    suffix = site.suffix_for(meta["section"])
    out = (chapter_tpl
           .replace("{{PAGE_TITLE}}", meta["nav_title"] + suffix)
           .replace("{{NAV_TITLE}}", meta["nav_title"])
           .replace("{{BODY}}", body))
    with open(os.path.join(out_dir, "index.html"), "w", encoding="utf-8", newline="\n") as f:
        f.write(out)


# ---- もくじ ---------------------------------------------------------------

def card_html(meta, chapter_dir):
    num = html.escape(meta.get("num", ""))
    title = html.escape(meta.get("card_title", ""))
    desc = html.escape(meta.get("desc", ""))
    level = meta.get("level")
    level_html = ('<span class="level">%s</span>\n        ' % html.escape(level)) if level else ""

    # wip … まだ作りかけの章に「工事中」マークを付ける
    #   wip: true    →  🚧 工事中
    #   wip: 準備中   →  🚧 準備中（好きな文字にできる）
    wip = meta.get("wip", "").strip()
    if wip.lower() in ("", "false", "no", "0"):
        wip = ""
    label = "工事中" if wip.lower() in ("true", "yes", "1") else wip
    wip_html = ('<span class="wip">🚧 %s</span>\n        ' % html.escape(label)) if wip else ""

    cls = " ".join(c for c in (meta.get("color", ""), "wip-card" if wip else "") if c)
    return (
        '      <a class="card %s" href="%s/">\n'
        '        <div class="face"><span class="num">%s</span><span class="emoji">%s</span></div>\n'
        '        %s%s<h2>%s</h2>\n'
        '        <p>%s</p>\n'
        '      </a>'
    ) % (cls, chapter_dir, num, meta.get("emoji", ""), wip_html, level_html, title, desc)


def _partial(site, name):
    """content/_index/<name>.html があれば読む（なければ空）。

    参考リンクや第三者素材の注記のように、教材ごとに文章が違うかたまり。
    """
    path = os.path.join(site.root, "content", "_index", name + ".html")
    if not os.path.exists(path):
        return ""
    return _read(path).replace("\r\n", "\n").strip("\n")


def build_index(site, chapters, index_tpl, docs):
    blocks = []
    for sec in site.sections:
        items = [(m, d) for (m, d) in chapters if m.get("section") == sec.name]
        if not items:
            continue
        items.sort(key=lambda t: t[0].get("id", t[1]))
        cards = "\n\n".join(card_html(m, d) for m, d in items)
        blocks.append(
            '  <!-- ============ %s ============ -->\n'
            '  <section class="section %s">\n'
            '    <div class="section-head">\n'
            '      <span class="stitle">%s</span>\n'
            '      <span class="ssub">%s</span>\n'
            '    </div>\n'
            '    <div class="section-line"></div>\n\n'
            '    <div class="grid">\n%s\n    </div>\n'
            '  </section>'
            % (sec.name, sec.cls, sec.title, sec.sub, cards)
        )

    if site.logo:
        header = ('<img class="logo" src="assets/%s" alt="">%s'
                  % (html.escape(site.logo), html.escape(site.header)))
    else:
        header = html.escape(site.header)

    refs = _partial(site, "refs")
    refs = ("\n" + refs + "\n") if refs else ""
    lic_extra = _partial(site, "license")
    lic_extra = (lic_extra + "\n") if lic_extra else ""

    out = (index_tpl
           .replace("{{CHAPTERS}}", "\n\n".join(blocks))
           .replace("{{SITE_TITLE}}", html.escape(site.name))
           .replace("{{HEADER}}", header)
           .replace("{{SITE_URL}}", html.escape(site.base_url))
           .replace("{{ACCENT}}", html.escape(site.accent))
           .replace("{{REFS}}", refs)
           .replace("{{LICENSE_EXTRA}}", lic_extra)
           .replace("{{COPYRIGHT}}", html.escape(site.copyright)))
    with open(os.path.join(docs, "index.html"), "w", encoding="utf-8", newline="\n") as f:
        f.write(out)


# ---- 入口 -----------------------------------------------------------------

def build(root):
    """<root>/site.toml を読んで <root>/docs を作りなおす。"""
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    root = os.path.abspath(root)
    site = site_mod.load(root)
    content = os.path.join(root, "content")
    docs = os.path.join(root, "docs")
    if not os.path.isdir(content):
        raise site_mod.SiteError("content/ がありません: %s" % content)

    warnings = []

    def warn(msg):
        warnings.append(msg)
        print("  [!] " + msg)

    chapter_tpl = _read(os.path.join(TEMPLATES, "chapter.html"))
    index_tpl = _read(os.path.join(TEMPLATES, "index.html"))

    placed = []
    place_managed_files(site, docs, placed)
    build_assets(site, docs, placed)

    section_map = site.section_map
    dirs = sorted(d for d in os.listdir(content)
                  if os.path.isdir(os.path.join(content, d)) and not d.startswith("_"))
    chapters = []
    for d in dirs:
        mdpath = os.path.join(content, d, "index.md")
        if not os.path.exists(mdpath):
            warn("%s に index.md がありません（スキップ）" % d)
            continue
        meta, body = parse_frontmatter(_read(mdpath))
        missing = [k for k in ("section", "nav_title", "card_title") if k not in meta]
        if missing:
            warn("%s: フロントマター不足 %s（スキップ）" % (d, missing))
            continue
        if meta["section"] not in section_map:
            warn("%s: 未知の section '%s'（site.toml の [[sections]] にありません。スキップ）"
                 % (d, meta["section"]))
            continue
        color = meta.get("color", "")
        if color and color not in site.palette:
            warn("%s: 未知の color '%s'（site.toml の [palette] にありません。枠色は既定になります）"
                 % (d, color))
        if meta.get("level") and color not in site.level_palette:
            warn("%s: level: があるのに [palette.level] に '%s' がありません（ラベルが白地になります）"
                 % (d, color))
        build_chapter(site, meta, body, d, chapter_tpl, docs, warn)
        chapters.append((meta, d))
        print("  ✓ content/%-18s → docs/%s/" % (d, d))

    build_index(site, chapters, index_tpl, docs)
    print("  ✓ もくじ                        → docs/index.html（%d章）" % len(chapters))

    if placed:
        print("  ✓ 共通部品を更新（%d ファイル）:" % len(placed))
        for p in placed:
            print("      " + os.path.relpath(p, root).replace("\\", "/"))

    if warnings:
        print("完了。ただし %d 件の警告があります（上を見てください）。" % len(warnings))
    else:
        print("完了。")
    return len(warnings)
