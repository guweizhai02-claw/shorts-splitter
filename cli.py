"""CLI 入口。"""

import argparse
import sys
from pathlib import Path

from shorts_splitter.splitter import VideoSplitter
from shorts_splitter.analyzer import AudioAnalyzer
from shorts_splitter.seo import ShortSEOGenerator


def cmd_split(args):
    """拆分视频为 Shorts。"""
    splitter = VideoSplitter(category=args.category or "blues")

    output_dir = args.output or f"./shorts_{Path(args.video).stem}"

    clips = splitter.split(
        video_path=args.video,
        count=args.count,
        min_duration=args.min_duration,
        max_duration=args.max_duration,
        output_dir=output_dir,
    )

    successful = sum(1 for c in clips if c.status != "failed")
    print(f"\n{'='*50}")
    print(f"✅ 完成! {successful}/{len(clips)} 个 Shorts 生成成功")
    print(f"📁 输出目录: {output_dir}")


def cmd_analyze(args):
    """分析视频音频。"""
    analyzer = AudioAnalyzer()
    segments = analyzer.analyze(args.video)

    print(f"\n📊 音频分析 ({len(segments)} 段):")
    for seg in segments:
        bar = "█" * int(seg.energy * 30)
        icon = {"high_energy": "🔥", "medium": "🟡", "silence": "⬛", "low_energy": "🟢"}.get(seg.type, "⚪")
        print(f"  {icon} [{seg.start:.1f}s-{seg.end:.1f}s] {bar} ({seg.type})")


def cmd_seo(args):
    """生成 Shorts SEO。"""
    seo = ShortSEOGenerator(category=args.category or "blues")
    result = seo.generate(
        source_video_title=args.source or "My Video",
        segment_index=args.index or 1,
        duration=args.duration or 30.0,
    )

    print(f"\n📝 Title: {result['title']}")
    print(f"\n📄 Description:")
    print(f"  {result['description']}")
    print(f"\n🏷️ Hashtags:")
    print(f"  {result['hashtags']}")


def main():
    parser = argparse.ArgumentParser(prog="shorts-splitter", description="YouTube Shorts 自动拆分工具")
    subparsers = parser.add_subparsers(dest="command")

    # split
    p_split = subparsers.add_parser("split", help="拆分视频为 Shorts")
    p_split.add_argument("video", help="输入视频路径")
    p_split.add_argument("-c", "--count", type=int, default=5, help="生成数量")
    p_split.add_argument("--min-duration", type=float, default=15.0, help="最短时长(秒)")
    p_split.add_argument("--max-duration", type=float, default=58.0, help="最长时长(秒)")
    p_split.add_argument("-o", "--output", help="输出目录")
    p_split.add_argument("--category", default="blues", help="分类")

    # analyze
    p_analyze = subparsers.add_parser("analyze", help="分析视频音频")
    p_analyze.add_argument("video", help="输入视频路径")

    # seo
    p_seo = subparsers.add_parser("seo", help="生成 SEO 数据")
    p_seo.add_argument("--source", default="My Video", help="源视频标题")
    p_seo.add_argument("--index", type=int, default=1, help="片段序号")
    p_seo.add_argument("--duration", type=float, default=30.0, help="片段时长")
    p_seo.add_argument("--category", default="blues", help="分类")

    args = parser.parse_args()

    if args.command == "split":
        cmd_split(args)
    elif args.command == "analyze":
        cmd_analyze(args)
    elif args.command == "seo":
        cmd_seo(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
