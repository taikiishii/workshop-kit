#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""scaffold.py  --  新しいワークショップ／新しい章のひな形を作る

    python -m wskit new-workshop ../rasppi --name "ラズパイ 体験ワークショップ"
    python -m wskit new-chapter b1_led --section 基本編 --title "LEDを光らせよう"
"""

import os
import re
import shutil

from . import site as site_mod

KIT_DIR = os.path.dirname(os.path.abspath(__file__))
SCAFFOLD = os.path.join(KIT_DIR, "scaffold")


class ScaffoldError(Exception):
    pass


def _fill(text, values):
    for k, v in values.items():
        text = text.replace("{{%s}}" % k, v)
    return text


def _write(path, text):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    print("  ✓ " + path)


def new_workshop(dest, name=None):
    """新しい教材フォルダを、すぐビルドできる状態で作る。"""
    dest = os.path.abspath(dest)
    if os.path.exists(dest) and os.listdir(dest):
        raise ScaffoldError("すでに中身のあるフォルダです: %s" % dest)

    slug = os.path.basename(dest.rstrip(os.sep))
    name = name or slug
    values = {"NAME": name, "SLUG": slug}

    src = os.path.join(SCAFFOLD, "workshop")
    for fn in ("site.toml", "build.py", "README.md"):
        with open(os.path.join(src, fn), encoding="utf-8") as f:
            _write(os.path.join(dest, fn), _fill(f.read(), values))

    # 章のひな形は、その教材で手でコピーして使えるように置いておく
    shutil.copytree(os.path.join(SCAFFOLD, "chapter"),
                    os.path.join(dest, "content", "_template"), dirs_exist_ok=True)
    print("  ✓ " + os.path.join(dest, "content", "_template", "index.md"))
    os.makedirs(os.path.join(dest, "content", "_index"), exist_ok=True)
    os.makedirs(os.path.join(dest, "assets"), exist_ok=True)

    print("\n作成しました: %s" % dest)
    print("つぎにやること:")
    print("  1. site.toml の base_url・セクション・色を直す")
    print("  2. cd %s && python build.py" % dest)
    print("  3. python -m wskit new-chapter b1_xxx --section 基本編 --title \"…\"")
    return dest


def new_chapter(root, dirname, section=None, title=None, num=None, color=None):
    """content/<dirname>/index.md をひな形から作る。

    その教材に content/_template/index.md があればそれを使い、
    無ければ kit の汎用ひな形を使う。
    """
    root = os.path.abspath(root)
    site = site_mod.load(root)

    if not re.match(r"^[A-Za-z]+\d+_[A-Za-z0-9_]+$", dirname):
        raise ScaffoldError(
            "章フォルダ名は <id>_<slug> の形にしてください（例: b1_led, mq3_linetracer）: %s" % dirname)
    out_dir = os.path.join(root, "content", dirname)
    if os.path.exists(out_dir):
        raise ScaffoldError("すでにあります: %s" % out_dir)

    chap_id, slug = dirname.split("_", 1)

    names = [s.name for s in site.sections]
    if section is None:
        section = names[0]
    if section not in names:
        raise ScaffoldError("section '%s' は site.toml にありません。使えるのは: %s"
                            % (section, " / ".join(names)))

    if color is None:
        color = next(iter(site.palette), "")
    if num is None:
        num = re.sub(r"^[A-Za-z]+", "", chap_id) or "1"
    title = title or "あたらしい章のタイトル"

    own = os.path.join(root, "content", "_template", "index.md")
    tpl_path = own if os.path.exists(own) else os.path.join(SCAFFOLD, "chapter", "index.md")
    with open(tpl_path, encoding="utf-8") as f:
        text = f.read()

    text = _fill(text, {
        "ID": chap_id, "SLUG": slug, "SECTION": section, "NUM": str(num),
        "COLOR": color, "NAV_TITLE": title, "CARD_TITLE": title,
        "SITE_NAME": site.name,
    })
    if tpl_path == own:
        # 教材の _template は固定の値で書かれているので、頭だけ差し替える
        text = _retarget_frontmatter(text, chap_id, slug, section, num, color, title)

    _write(os.path.join(out_dir, "index.md"), text)
    os.makedirs(os.path.join(out_dir, "image", "index"), exist_ok=True)
    print("\n書けたら python build.py で docs/%s/ ができます。" % dirname)
    return out_dir


def _retarget_frontmatter(text, chap_id, slug, section, num, color, title):
    """教材ごとの _template のフロントマターを、新しい章の値に書きかえる。"""
    repl = {"id": chap_id, "slug": slug, "section": section,
            "num": str(num), "color": color,
            "nav_title": title, "card_title": title}
    out, in_fm, done = [], False, False
    for i, line in enumerate(text.split("\n")):
        if line.strip() == "---" and not done:
            if not in_fm and i == 0:
                in_fm = True
            elif in_fm:
                in_fm, done = False, True
            out.append(line)
            continue
        if in_fm:
            m = re.match(r"^([A-Za-z_]+)\s*:", line)
            if m and m.group(1) in repl:
                line = "%s: %s" % (m.group(1), repl[m.group(1)])
        out.append(line)
    return "\n".join(out)
