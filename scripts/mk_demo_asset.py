#!/usr/bin/env python3
"""把真机 exo_video_cache 的 1.json 转成工程用的压缩播放清单。

原文件 ~520 KB，888 项的 urlMap 里 URL 有超长公共前缀，直接内嵌会让 apk/ipa
白胖一倍。这里拆成 `prefix`（公共前缀）+ `tails`（每项尾部），体积约减半，
`DemoPlaylist` 里 `prefix + tails[i]` 即可无损还原。

用法：
    python scripts/mk_demo_asset.py <1.json> --title 嫁金钗 --episode 第02集 \
        --out assets/demo/ep02.json
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path


def load_url_map(src: Path) -> tuple[list[str], list[float]]:
    data = json.loads(src.read_text(encoding="utf-8"))

    url_map = data.get("urlMap")
    if not url_map:
        raise SystemExit(f"{src} 里没有 urlMap，这不像 exo_video_cache 的 1.json")

    # urlMap 的 key 是 "0" "1" ... 的字符串序号，按整数排序才能对上分片顺序
    if isinstance(url_map, dict):
        keys = sorted(url_map, key=lambda k: int(k))
        urls = [url_map[k]["url"] for k in keys]
    else:
        urls = [e["url"] for e in url_map]

    # 分片时长：优先用 segmentDurationMs 数组；没有就回退到恒定值
    durs = data.get("segmentDurationMs")
    if not durs:
        # 老版本会把时长塞进 content 的 #EXTINF 行里，这里兜底给 8 秒
        durs = [8000] * len(urls)
    if len(durs) != len(urls):
        raise SystemExit(
            f"段数不一致：urlMap {len(urls)} 项，segmentDurationMs {len(durs)} 项"
        )
    return urls, [float(d) for d in durs]


def main() -> int:
    ap = argparse.ArgumentParser(description="1.json -> assets/demo/*.json")
    ap.add_argument("src", type=Path, help="exo_video_cache 的 1.json")
    ap.add_argument("--title", required=True, help="剧名")
    ap.add_argument("--episode", required=True, help="集数标签，如 第02集")
    ap.add_argument("--id", default="", help="videoPathId，缺省用源文件父目录名")
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()

    urls, durs = load_url_map(args.src)
    # 直接用完整公共前缀（会切在路径中途，比如 `.../10/16/179215`）。
    # 4 段的一集 URL 公共部分很长，切到目录边界会白丢约 10% 体积。
    # URL 是纯 ASCII，不存在把多字节字符截半的问题。
    prefix = os.path.commonprefix(urls)
    tails = [u[len(prefix):] for u in urls]
    if any(not t for t in tails):
        raise SystemExit("公共前缀吃掉了一整个 URL（同一分片重复？）")

    vid = args.id or args.src.parent.name
    out = {
        "title": args.title,
        "episode": args.episode,
        "id": vid,
        "prefix": prefix,
        "durs": durs,
        "tails": tails,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8"
    )

    total = sum(durs) / 1000.0
    print(f"OK: {args.out}")
    print(f"  段数   {len(tails)}   时长 {total:.1f}s ({total/60:.1f} 分钟)")
    print(f"  前缀   {prefix}")
    print(f"  体积   {args.out.stat().st_size:,} B（源 {args.src.stat().st_size:,} B）")
    print(f"  首片   {prefix}{tails[0]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
