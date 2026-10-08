#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""site.py  --  各ワークショップの site.toml を読み込む

site.toml は「その教材だけのちがい」を集めた1枚の設定ファイル。
共通のしくみ（build の手順・CSS・JS・テンプレート）は workshop-kit 側にあり、
教材ごとに書きかえない。

    site = load(教材フォルダ)

書き方は wskit/scaffold/workshop/site.toml を見るのが早い。
"""

import os
import tomllib
from dataclasses import dataclass, field


class SiteError(Exception):
    """site.toml の書きかたが足りない・まちがっているとき。"""


# [theme] に書ける項目。値の形（色1つ／色の並び）と、並びの長さ。
#   None … 1つ以上いくつでも
THEME_KEYS = {
    "bg":           ("color", None),   # 画面の背景色（もくじ・章ページ）
    "bg_dots":      ("list", 2),       # 背景の水玉 2色（rgba で うすく書く）
    "rainbow":      ("list", None),    # ページ上部・もくじの終わりの虹色の線
    "slide_frames": ("list", None),    # 章ページのスライドの枠色（順にくり返す）
    "cover_glow":   ("list", 2),       # 表紙スライドのやわらかい光 2色（左上・右下）
    "hint_bg":      ("color", None),   # 博士の吹き出しの背景色
    "qr_frame":     ("color", None),   # もくじの QR コードの枠色
    "qr_dark":      ("color", None),   # QR コードの点の色（白地で読める濃い色にする）
}


def _load_theme(data):
    theme = dict(data.get("theme", {}))
    for k, v in theme.items():
        if k not in THEME_KEYS:
            raise SiteError("site.toml の [theme] に %s は書けません。使えるのは: %s"
                            % (k, " / ".join(THEME_KEYS)))
        kind, n = THEME_KEYS[k]
        if kind == "color":
            if not isinstance(v, str) or not v:
                raise SiteError("site.toml の [theme] の %s は色の文字列にしてください" % k)
        else:
            if not isinstance(v, list) or not v or not all(isinstance(x, str) and x for x in v):
                raise SiteError("site.toml の [theme] の %s は色の文字列の並び [ … ] にしてください" % k)
            if n is not None and len(v) != n:
                raise SiteError("site.toml の [theme] の %s は %d 色にしてください（いま %d 色）"
                                % (k, n, len(v)))
    return theme


@dataclass
class Section:
    """もくじのひとかたまり（基礎編・発展編…）。並び順は site.toml の順。"""
    name: str                       # frontmatter の section: と突き合わせる名前
    cls: str                        # CSS クラス（s-basic など）
    title: str                      # もくじに出す見出し
    sub: str = ""                   # 見出しのよこの説明
    suffix: str = ""                # 章ページの <title> の接尾辞（空なら site 側の既定）
    line: list = field(default_factory=list)   # 区切り線のグラデーション（色の並び）


@dataclass
class Site:
    root: str                       # 教材フォルダ（site.toml があるところ）
    name: str                       # もくじの <title> に使う教材名
    base_url: str                   # 公開URL（末尾スラッシュ）
    header: str                     # もくじの h1 の文字
    title_suffix: str = ""          # 章ページの <title> の既定の接尾辞
    logo: str = ""                  # h1 の頭に置く画像（assets/ からの相対）
    accent: str = "#00a99d"
    accent_dark: str = "#007c74"
    accent_bright: str = "#00b5a8"  # ヘッダーのグラデーションの明るいほう
    palette: dict = field(default_factory=dict)        # color: → カードの枠色
    level_palette: dict = field(default_factory=dict)  # color: → 難易度ラベルの背景色
    theme: dict = field(default_factory=dict)          # [theme] … 共通部品の飾りの色（書いた項目だけ上書き）
    sections: list = field(default_factory=list)
    namespaces: list = field(default_factory=list)     # コードで青くする語
    mascot_auto: bool = True        # 短い吹き出しを顔アイコンにする
    mascot_full_min: int = 60       # この文字数以上なら全身
    copyright: str = ""
    max_img_width: int = 1400       # これより横が大きい画像は縮小してコピー

    @property
    def section_map(self):
        return {s.name: s for s in self.sections}

    def suffix_for(self, section_name):
        """章ページの <title> の接尾辞。セクション個別の指定があればそれを使う。"""
        sec = self.section_map.get(section_name)
        if sec and sec.suffix:
            return sec.suffix
        return self.title_suffix


def load(root):
    """<root>/site.toml を読んで Site を返す。"""
    path = os.path.join(root, "site.toml")
    if not os.path.exists(path):
        raise SiteError(
            "site.toml が見つかりません: %s\n"
            "  新しい教材なら  python -m wskit new-workshop <フォルダ>  で作れます。" % path)
    with open(path, "rb") as f:
        data = tomllib.load(f)

    s = data.get("site", {})
    for key in ("name", "base_url", "header"):
        if not s.get(key):
            raise SiteError("site.toml の [site] に %s がありません" % key)

    base_url = s["base_url"]
    if not base_url.endswith("/"):
        raise SiteError("site.toml の base_url は / で終わらせてください: %s" % base_url)

    sections = []
    for i, sec in enumerate(data.get("sections", [])):
        for key in ("name", "cls", "title"):
            if not sec.get(key):
                raise SiteError("site.toml の %d 個目の [[sections]] に %s がありません" % (i + 1, key))
        sections.append(Section(
            name=sec["name"], cls=sec["cls"], title=sec["title"],
            sub=sec.get("sub", ""), suffix=sec.get("suffix", ""),
            line=list(sec.get("line", [])),
        ))
    if not sections:
        raise SiteError("site.toml に [[sections]] がひとつもありません")

    names = [x.name for x in sections]
    dup = [n for n in names if names.count(n) > 1]
    if dup:
        raise SiteError("site.toml の [[sections]] に同じ name があります: %s" % sorted(set(dup))[0])

    palette = dict(data.get("palette", {}))
    level_palette = dict(palette.pop("level", {}))
    bad = [k for k, v in palette.items() if not isinstance(v, str)]
    if bad:
        raise SiteError("site.toml の [palette] の %s は色の文字列にしてください" % bad[0])

    code = data.get("code", {})
    mascot = data.get("mascot", {})
    lic = data.get("license", {})

    return Site(
        root=root,
        name=s["name"],
        base_url=base_url,
        header=s["header"],
        title_suffix=s.get("title_suffix", ""),
        logo=s.get("logo", ""),
        accent=s.get("accent", "#00a99d"),
        accent_dark=s.get("accent_dark", "#007c74"),
        accent_bright=s.get("accent_bright", s.get("accent", "#00b5a8")),
        palette=palette,
        level_palette=level_palette,
        theme=_load_theme(data),
        sections=sections,
        namespaces=list(code.get("namespaces", [])),
        mascot_auto=bool(mascot.get("auto", True)),
        mascot_full_min=int(mascot.get("full_min", 60)),
        copyright=lic.get("copyright", ""),
        max_img_width=int(s.get("max_img_width", 1400)),
    )
