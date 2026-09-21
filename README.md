# workshop-kit

ワークショップ教材サイトの**共通のしくみ**。`content/` の Markdown から
`docs/` の教材サイト（スライド形式のHTML・QRコード・もくじ）を生成します。

これを使っている教材:

- [microbit-workshop](https://github.com/taikiishii/microbit-workshop) — マイクロビット 体験ワークショップ
- [uiapduino-workshop](https://github.com/taikiishii/uiapduino-workshop) — UIAPduino 体験ワークショップ

**教材ごとにちがうのは `site.toml` 1枚だけ**です。ビルドの手順・CSS・JavaScript・
HTMLテンプレート・執筆規約はここにまとめてあり、ここを直すとすべての教材に反映されます。

## 使い方

```bash
git clone https://github.com/taikiishii/workshop-kit.git
pip install -e ./workshop-kit
```

教材フォルダで:

```bash
python build.py                 # content/ → docs/
```

新しい教材・新しい章:

```bash
python -m wskit new-workshop ../rasppi --name "ラズパイ 体験ワークショップ"
python -m wskit new-chapter b1_led --section 基本編 --title "LEDを光らせよう"
```

## 教材を書く人へ

- 共通の書き方 … **[AUTHORING.md](AUTHORING.md)**
- AI（Claude Code など）に渡す共通ルール … **[CLAUDE.md](CLAUDE.md)**

その教材だけのきまり（セクション名・章フォルダ名の頭文字・使う言語・ボード固有の注意）は、
各教材リポジトリの `AUTHORING.md` にあります。

## 中身

```
wskit/
  build.py              content/ → docs/ の生成
  site.py               site.toml の読み込みと検証
  scaffold.py           new-workshop / new-chapter
  assets/               全教材に配る共通部品
    deck.css            章ページ（スライド／発表モード／印刷）のスタイル
    deck.js             埋め込みMarkdown → スライドの変換エンジン
    index.css           もくじページのスタイル
    hakase.png          博士（全身）… 長い吹き出し用
    hakase-face.png     博士（顔だけ）… 短い吹き出し用
  templates/
    chapter.html        章ページのひな形
    index.html          もくじのひな形
  files/                各教材リポジトリに配置する設定ファイル
    LICENSE.txt         → docs/LICENSE.txt
    gitignore           → .gitignore
    vscode-settings.json → .vscode/settings.json
  scaffold/
    chapter/index.md    新しい章のひな形（教材に _template があればそちらを優先）
    workshop/           新しい教材一式のひな形
```

### 教材ごとに変わるところ

共通の CSS / JS は教材ごとに書きかえません。かわりにビルドが `site.toml` から
2つのファイルを生成し、それで上書きします。

| 生成されるファイル | 何が入るか |
|---|---|
| `docs/assets/site-theme.css` | テーマ色、もくじカードの枠色、セクションの区切り線 |
| `docs/assets/site-config.js` | コードで青くする語、博士のアイコンの出しかた |

`site.toml` の書き方は `wskit/scaffold/workshop/site.toml` にコメント付きで載っています。

## 依存

Python 3.11 以上（`tomllib` を使います）、`segno`（QR生成）、`pillow`（画像の縮小）。
`pip install -e .` でまとめて入ります。

## ライセンス

MIT License — Copyright © 2026 Taiki Ishii
