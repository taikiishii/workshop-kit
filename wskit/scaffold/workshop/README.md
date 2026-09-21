# {{NAME}}

（ここに、だれ向けの・なにをするワークショップかを2〜3行で書く）

## 公開ページ

**https://example.github.io/{{SLUG}}/**

- パソコン・スマホ・タブレットのブラウザでそのまま読めます。
- 各ページ上部の「▶ 発表モード」で全画面プレゼン、「印刷 / PDF」でスライド形式の配布資料になります。
- コードブロックは、パソコンなら右上の「📋 コピー」でワンクリックコピーできます。

## 教材を書く・直す

`content/` に Markdown を書いて `python build.py` を実行するだけで、HTML・QRコード・もくじが自動生成されます。

- 共通の書き方 … [workshop-kit の AUTHORING.md](https://github.com/taikiishii/workshop-kit/blob/main/AUTHORING.md)
- この教材だけのきまり … [AUTHORING.md](AUTHORING.md)

はじめての1回だけ、しくみを入れます。

```bash
git clone https://github.com/taikiishii/workshop-kit.git ../workshop-kit
pip install -e ../workshop-kit
```

## フォルダの見かた

- `site.toml` … **この教材だけの設定**（公開URL・セクション・色）。共通のしくみは workshop-kit 側
- `content/<章>/` … 各章の **`index.md`（編集するのはここ）** と `image/index/`（写真・画面キャプチャ）
- `content/_index/` … もくじページに足す任意のブロック（`refs.html` / `license.html`）
- `assets/` … この教材だけの画像（ロゴなど）。ビルドで `docs/assets/` に入る
- `docs/` … `build.py` が生成する公開ファイル（GitHub Pages 配信元。**直接編集しない**）

## ライセンス

文章・レイアウト・プログラム（HTML / CSS / JavaScript）は **MIT ライセンス**です。
第三者が権利を持つ素材（画面キャプチャ・イラスト・写真）は、それぞれの提供元の利用規約に従います。

Copyright © 2026 Your Name
