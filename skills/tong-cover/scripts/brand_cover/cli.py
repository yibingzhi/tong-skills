from __future__ import annotations

import argparse
import sys

from .presets import LAYOUTS, PRESETS, RATIOS, WEEKDAY_PRESET, today_cn_date
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
    ap.add_argument("--sub", default="", help="副标题 / 补充信息")
    ap.add_argument("--kicker", default="", help="同 --sub")
    ap.add_argument("--tag", default="", help="同 --sub")
    ap.add_argument("--brand", default="橦云异梦", help="品牌名称 (默认: 橦云异梦)")
    ap.add_argument("--date", default="", help="日期 (空则自动按今天，如: 9月1日 星期二)")
    ap.add_argument("--preset", default="auto", choices=["auto"] + list(PRESETS), help="颜色预设 (auto 自动按星期选色)")
    ap.add_argument("--layout", default="auto", choices=["auto"] + list(LAYOUTS), help="版式 (feed, editorial, briefing, divider, quote, bullet, square, banner)")
    ap.add_argument("--ratio", default="4:3", help="图片比例 (16:9, 1:1, 4:3, 3:4, 9:16, 2.35:1, 4:1, 3:1)")
    ap.add_argument("--num", default="01", help="章节号 (用于 divider 分割条)")
    ap.add_argument("--quote", default="", help="金句正文 (用于 quote 金句卡)")
    ap.add_argument("--author", default="", help="金句作者 / 出处 (用于 quote 金句卡)")
    ap.add_argument("--bullets", default="", help="要闻清单分号分隔 (用于 bullet 速览清单卡)")
    ap.add_argument("--dividers", default="", help="章节列表分号分隔，如: '01:今日头条:热点速览; 02:前沿思考:深度解读'")
    ap.add_argument("--pack", default="", help="全套物料输出目录，一行生成公众号全套视觉图片")
    ap.add_argument("--out", default="out/cover.png", help="单图输出路径")
    ap.add_argument("--seed", type=int, default=42, help="随机种子")
    ap.add_argument("--list", action="store_true", help="打印所有可用预设与版式")
    return ap


def main(argv=None):
    args = build_parser().parse_args(argv)
    if args.list:
        print("presets:", ", ".join(PRESETS))
        print("layouts:", ", ".join(LAYOUTS))
        print("ratios:", ", ".join(RATIOS))
        print("weekday mapping:", ", ".join("%s=%s" % item for item in WEEKDAY_PRESET.items() if item[0] != "天"))
        from .fonts import diagnose

        print("fonts:")
        for line in diagnose():
            print(" ", line)
        return 0

    sub_text = args.sub or args.kicker or args.tag
    date_text = args.date or today_cn_date()

    # Full Pack Generation
    if args.pack:
        bullets_list = parse_bullets_arg(args.bullets)
        dividers_list = parse_dividers_arg(args.dividers)
        results = render_pack(
            out_dir=args.pack,
            date=date_text,
            brand=args.brand,
            title=args.title or "每日速览",
            sub=sub_text,
            bullets=bullets_list if bullets_list else [
                "全球前沿大模型与具身智能新突破加速涌现",
                "芯片巨头发布亮眼财报，算力基础设施需求强劲",
                "国内 AI 落地应用迎来政策红利，产业赋能提速",
            ],
            quote=args.quote or "流水不争先，争的是滔滔不绝。",
            author=args.author,
            dividers=dividers_list if dividers_list else [
                ("01", "今日头条", "前沿动向与核心大事件"),
                ("02", "行业观察", "技术落地与商业思考"),
                ("03", "深度洞察", "未来趋势与行业启示"),
            ],
            preset=args.preset,
            seed=args.seed,
        )
        print("PACK OK -> Output Directory:", args.pack)
        for k, v in results.items():
            print("  - %s: %s" % (k, v))
        return 0

    # Single Cover Generation
    bullets_list = parse_bullets_arg(args.bullets)
    brief = CoverBrief(
        title=args.title or "每日速览",
        sub=sub_text,
        kicker=sub_text,
        out=args.out,
        brand=args.brand,
        date=date_text,
        preset=args.preset,
        layout=args.layout,
        ratio=args.ratio,
        seed=args.seed,
        num=args.num,
        quote=args.quote,
        author=args.author,
        bullets=bullets_list,
    )
    info = render_cover(brief)
    print("OK:", info)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
