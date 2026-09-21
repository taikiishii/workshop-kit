#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""wskit  --  ワークショップ教材サイトの共通のしくみ（workshop-kit）

すべてのワークショップ（microbit / UIAPduino / これから増えるもの）が
同じ build・同じ CSS/JS・同じ記法を使うための1か所。
教材ごとのちがいは、それぞれの site.toml に書く。

    import wskit
    wskit.build("<教材フォルダ>")
"""

from .build import build
from .scaffold import new_chapter, new_workshop
from .site import Site, SiteError, load as load_site

__all__ = ["build", "new_chapter", "new_workshop", "load_site", "Site", "SiteError"]
__version__ = "1.0.0"
