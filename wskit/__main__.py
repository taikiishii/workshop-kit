#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""wskit のコマンドライン

    python -m wskit build [<教材フォルダ>]
    python -m wskit new-workshop <フォルダ> [--name "教材名"]
    python -m wskit new-chapter <id>_<slug> [--section 基本編] [--title "…"]
                               [--num 3] [--color c3] [--root <教材フォルダ>]
"""

import argparse
import sys

from . import build as do_build
from .scaffold import ScaffoldError, new_chapter, new_workshop
from .site import SiteError


def main(argv=None):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    p = argparse.ArgumentParser(prog="wskit", description="ワークショップ教材サイトの共通ツール")
    sub = p.add_subparsers(dest="cmd", required=True)

    b = sub.add_parser("build", help="content/ から docs/ を生成する")
    b.add_argument("root", nargs="?", default=".", help="教材フォルダ（既定: いまのフォルダ）")

    w = sub.add_parser("new-workshop", help="新しい教材フォルダのひな形を作る")
    w.add_argument("dest", help="作るフォルダ（例: ../rasppi）")
    w.add_argument("--name", help="教材名（もくじの見出しに出る）")

    c = sub.add_parser("new-chapter", help="新しい章のひな形を作る")
    c.add_argument("dirname", help="章フォルダ名 <id>_<slug>（例: b1_led）")
    c.add_argument("--section", help="もくじのどのセクションに入れるか")
    c.add_argument("--title", help="章のタイトル")
    c.add_argument("--num", help="もくじカードの番号バッジ")
    c.add_argument("--color", help="もくじカードの枠色（site.toml の [palette] のキー）")
    c.add_argument("--root", default=".", help="教材フォルダ（既定: いまのフォルダ）")

    a = p.parse_args(argv)
    try:
        if a.cmd == "build":
            do_build(a.root)
        elif a.cmd == "new-workshop":
            new_workshop(a.dest, a.name)
        else:
            new_chapter(a.root, a.dirname, a.section, a.title, a.num, a.color)
    except (SiteError, ScaffoldError) as e:
        sys.exit("エラー: %s" % e)
    return 0


if __name__ == "__main__":
    sys.exit(main())
