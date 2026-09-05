from __future__ import annotations

import argparse
import os
import sys

from .presets import COVER_THEMES, LAYOUTS, PRESETS, QUOTE_STYLES, RATIOS, WEEKDAY_PRESET, today_cn_date
from .render import CoverBrief, render_cover, render_pack


def parse_bullets_arg(val: str) -> list[str]:
    if not val:
        return []
    delimiter = ";" if ";" in val else ("\n" if "\n" in val else "||")
    parts = [p.strip() for p in val.split(delimiter) if p.strip()]
    return parts


def parse_dividers_arg(val: str) -> list[tuple[str, str, str]]:
    if not val:
        return []
    delimiter = ";" if ";" in val else "\n"
    raw_items = [p.strip() for p in val.split(delimiter) if p.strip()]
    dividers = []
    for idx, raw in enumerate(raw_items):
        parts = [p.strip() for p in raw.replace("：", ":").split(":")]
        if len(parts) == 1:
            # e.g. "今日热点" or "01 今日热点"
            p0 = parts[0]
            if len(p0) > 2 and p0[:2].isdigit() and p0[2] == " ":
                num = p0[:2]
                title = p0[3:].strip()
            else:
                num = "%02d" % (idx + 1)
                title = p0
            dividers.append((num, title, ""))
        elif len(parts) == 2:
            # e.g. "01:今日热点" or "今日热点:行业前沿"
            if parts[0].isdigit() or (len(parts[0]) == 2 and parts[0].isdigit()):
                dividers.append((parts[0], parts[1], ""))
            else:
                dividers.append(("%02d" % (idx + 1), parts[0], parts[1]))
        else:
            # e.g. "01:今日热点:行业前沿"
            dividers.append((parts[0], parts[1], parts[2]))
    return dividers


def build_parser():
    ap = argparse.ArgumentParser(description="Brand cover & article visual suite renderer")
    ap.add_argument("--title", default="每日速览", help="主标题 / 栏目名 / 章节名")
    ap.add_argument("--sub", default="", help="副标题 / 补充信息 / 金句解读")
    ap.add_argument("--kicker", default="", help="同 --sub")
    ap.add_argument("--tag", default="", help="分类标签 (如: 认知跃迁, 职场真相)")
    default_brand = os.getenv("TONG_BRAND", "橦云异梦")
    ap.add_argument("--brand", default=default_brand, help="品牌名称 (默认: %s，支持环境变量 TONG_BRAND)" % default_brand)
    ap.add_argument("--no-brand", action="store_true", help="纯净无水印模式（不显示品牌名与印章）")
    ap.add_argument("--date", default="", help="日期 (空则自动按今天，如: 9月1日 星期二)")
    ap.add_argument("--preset", default="auto", choices=["auto"] + list(PRESETS), help="颜色预设 (auto 自动按星期选色)")
    ap.add_argument("--theme", default="auto", choices=["auto"] + list(COVER_THEMES), help="封面背景主题 (celestial 云月星辰, swiss 现代瑞士网格, press 复古报刊)")
    ap.add_argument("--layout", default="auto", choices=["auto"] + list(LAYOUTS), help="版式 (feed, editorial, briefing, divider, quote, bullet, square, banner)")
    ap.add_argument("--ratio", default="auto", help="图片比例 (16:9, 1:1, 4:3, 3:4, 9:16, 2.35:1, 4:1, 3:1；auto 自动随版式)")
    ap.add_argument("--num", default="01", help="章节号 (用于 divider 分割条)")
    ap.add_argument("--quote", default="", help="金句正文 (用于 quote 金句卡，支持 ==重点词== 高亮划线语法)")
    ap.add_argument("--author", default="", help="金句作者 / 出处 (用于 quote 金句卡)")
    ap.add_argument("--source", default="", help="出处 / 来源书名 (用于 quote 金句卡，如: 《纳瓦尔宝典》)")
    ap.add_argument("--style", default="auto", choices=["auto"] + list(QUOTE_STYLES), help="金句卡视觉模板 (paper 宣纸便签, editorial 杂志高定, highlight 划线读书, dark 暗黑极客, cinema 电影台词, polaroid 拍立得, tweet 社交推文)")
    ap.add_argument("--highlight", default="", help="金句重点高亮词 (也可在 quote 中直接使用 ==词语== 语法)")
    ap.add_argument("--bullets", default="", help="要闻清单分号分隔 (用于 bullet 速览清单卡)")
    ap.add_argument("--dividers", default="", help="章节列表分号分隔，如: '01:今日头条:热点速览; 02:前沿思考:深度解读'")
    ap.add_argument("--points", nargs="*", help="轮播卡片要点，格式: 'Step|Heading|Body|Takeaway' (用于 card 轮播切片)")
    ap.add_argument("--outro", default="", help="轮播卡片末页金句/收束语 (用于 card 轮播切片)")
    ap.add_argument("--spec", default="", help="轮播卡片 JSON 规范文件路径 (用于 card 轮播切片)")
    ap.add_argument("--out-dir", default="", help="多图/卡片组输出目录 (等同于 --pack)")
    ap.add_argument("--pack", default="", help="全套物料输出目录，一行生成公众号全套视觉图片")
    ap.add_argument("--out", default="out/cover.png", help="单图输出路径")
    ap.add_argument("--seed", type=int, default=42, help="随机种子")
    ap.add_argument("--list", action="store_true", help="打印所有可用预设与版式")
    return ap


def main(argv=None):
    args = build_parser().parse_args(argv)
    if args.list:
        print("presets:", ", ".join(PRESETS))
        print("cover themes:", ", ".join(COVER_THEMES))
        print("layouts:", ", ".join(LAYOUTS))
        print("quote styles:", ", ".join(QUOTE_STYLES))
        print("ratios:", ", ".join(RATIOS))
        print("weekday mapping:", ", ".join("%s=%s" % item for item in WEEKDAY_PRESET.items() if item[0] != "天"))
        from .fonts import diagnose

        print("fonts:")
        for line in diagnose():
            print(" ", line)
        return 0

    sub_text = args.sub or args.kicker or args.tag
    date_text = args.date or today_cn_date()
    brand_text = "" if args.no_brand or (args.brand and args.brand.strip().lower() in ("none", "null", "false", "clean", "off")) else (args.brand or "")

    # Full Pack Generation
    if args.pack:
        bullets_list = parse_bullets_arg(args.bullets)
        dividers_list = parse_dividers_arg(args.dividers)
        results = render_pack(
            out_dir=args.pack,
            date=date_text,
            brand=brand_text,
            title=args.title or "每日速览",
            sub=sub_text,
            bullets=bullets_list if bullets_list else [
                "全球前沿大模型与具身智能新突破加速涌现",
                "芯片巨头发布亮眼财报，算力基础设施需求强劲",
                "国内 AI 落地应用迎来政策红利，产业赋能提速",
            ],
            quote=args.quote or "流水不争先，争的是滔滔不绝。",
            author=args.author,
            source=args.source,
            style=args.style,
            highlight=args.highlight,
            dividers=dividers_list if dividers_list else [
                ("01", "今日头条", "前沿动向与核心大事件"),
                ("02", "行业观察", "技术落地与商业思考"),
                ("03", "深度洞察", "未来趋势与行业启示"),
            ],
            preset=args.preset,
            theme=args.theme,
            seed=args.seed,
        )
        print("PACK OK -> Output Directory:", args.pack)
        for k, v in results.items():
            print("  - %s: %s" % (k, v))
        return 0

    # Multi-card Carousel Generation
    if args.layout in ("card", "carousel") or args.spec or args.points:
        import json
        from pathlib import Path
        from .cards import render_card_suite

        out_dir = Path(args.out_dir or args.pack or (args.out if not args.out.endswith(".png") else "out/cards"))
        parsed_points = []
        card_style = args.style if args.style in ("warm", "dark", "editorial") else "warm"

        if args.spec:
            with open(args.spec, "r", encoding="utf-8") as f:
                data = json.load(f)
            t = data.get("title", args.title or "未命名主题")
            s = data.get("subtitle", sub_text)
            tg = data.get("tag", args.tag or "精选")
            au = data.get("author", args.author)
            br = data.get("brand", brand_text)
            st = data.get("style", card_style)
            ou = data.get("outro", args.outro or args.quote)
            for p in data.get("points", []):
                parsed_points.append((
                    p.get("step", "01"),
                    p.get("heading", ""),
                    p.get("body", ""),
                    p.get("takeaway", ""),
                ))
        else:
            t = args.title or "未命名主题"
            s = sub_text
            tg = args.tag or "精选"
            au = args.author
            br = brand_text
            st = card_style
            ou = args.outro or args.quote or "好文章不是堆出来的，是剪出来的。"
            if args.points:
                for item in args.points:
                    parts = item.split("|")
                    step = parts[0] if len(parts) > 0 else "01"
                    h = parts[1] if len(parts) > 1 else ""
                    b = parts[2] if len(parts) > 2 else ""
                    take = parts[3] if len(parts) > 3 else ""
                    parsed_points.append((step, h, b, take))
            elif bullets_list:
                for idx, b in enumerate(bullets_list, 1):
                    parsed_points.append(("%02d" % idx, b, "", ""))

        saved = render_card_suite(
            title=t,
            subtitle=s,
            tag=tg,
            points=parsed_points,
            outro=ou,
            author=au,
            brand=br,
            out_dir=out_dir,
            style=st,
        )
        print("CARDS OK -> Output Directory:", str(out_dir))
        for p in saved:
            print("  -", p.name)
        return 0

    # Single Cover Generation
    bullets_list = parse_bullets_arg(args.bullets)
    brief = CoverBrief(
        title=args.title or "每日速览",
        sub=sub_text,
        kicker=sub_text,
        out=args.out,
        brand=brand_text,
        date=date_text,
        preset=args.preset,
        theme=args.theme,
        layout=args.layout,
        ratio=args.ratio,
        seed=args.seed,
        num=args.num,
        quote=args.quote,
        author=args.author,
        source=args.source,
        style=args.style,
        highlight=args.highlight,
        tags=[args.tag] if args.tag else [],
        bullets=bullets_list,
    )
    info = render_cover(brief)
    print("OK:", info)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
