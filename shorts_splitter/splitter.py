"""核心拆分逻辑 - 从长视频中智能截取 Shorts 片段。"""

import os
import json
import subprocess
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field

from .analyzer import AudioAnalyzer
from .video_analyzer import VideoAnalyzer
from .seo import ShortSEOGenerator


@dataclass
class ShortClip:
    """单个 Shorts 片段。"""
    index: int
    start_time: float
    end_time: float
    duration: float
    video_path: str
    cover_path: str
    seo: Dict
    status: str = "pending"  # pending, extracted, cover_ready, seo_ready


class VideoSplitter:
    """视频拆分器。"""

    def __init__(self, category: str = "blues"):
        self.audio_analyzer = AudioAnalyzer()
        self.video_analyzer = VideoAnalyzer()
        self.seo_generator = ShortSEOGenerator(category)
        self.category = category

    def split(
        self,
        video_path: str,
        count: int = 5,
        min_duration: float = 15.0,
        max_duration: float = 58.0,
        output_dir: str = "./shorts_output",
        fps: int = 30,
    ) -> List[ShortClip]:
        """从长视频中拆分出多个 Shorts。

        Args:
            video_path: 输入视频路径
            count: 期望生成的 Shorts 数量
            min_duration: 最短片段时长（秒）
            max_duration: 最长片段时长（秒）
            output_dir: 输出目录
            fps: 输出帧率

        Returns:
            ShortClip 列表
        """
        video_path = str(Path(video_path).resolve())
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        # 1. 分析视频信息
        info = self.video_analyzer.get_info(video_path)
        if not info:
            print(f"⚠️ 无法分析视频: {video_path}")
            return []

        print(f"📹 视频: {info.path}")
        print(f"   时长: {info.duration:.1f}s | 分辨率: {info.width}x{info.height}")
        print(f"   编码: {info.video_codec} + {info.audio_codec}")

        # 2. 分析音频，找最佳截取点
        cut_points = self.audio_analyzer.find_best_cut_points(
            video_path,
            target_count=count,
            min_clip_duration=min_duration,
            max_clip_duration=max_duration,
        )

        if not cut_points:
            print("⚠️ 未能找到有效截取点，使用均匀分布")
            cut_points = self._uniform_split(info.duration, count, min_duration, max_duration)

        # 3. 生成 clips
        clips = []
        for i, (start, end) in enumerate(cut_points, 1):
            clip_name = f"short_{i:02d}_{start:.0f}s_to_{end:.0f}s.mp4"
            cover_name = f"short_{i:02d}_cover.jpg"

            clip = ShortClip(
                index=i,
                start_time=start,
                end_time=end,
                duration=end - start,
                video_path=str(output_dir / clip_name),
                cover_path=str(output_dir / cover_name),
                seo={},
                status="pending",
            )
            clips.append(clip)

        # 4. 执行截取
        print(f"\n✂️ 正在截取 {len(clips)} 个 Shorts...")
        for clip in clips:
            success = self._extract_clip(video_path, clip, fps)
            clip.status = "extracted" if success else "failed"
            status_icon = "✅" if success else "❌"
            print(f"   {status_icon} Clip #{clip.index}: {clip.start_time:.1f}s - {clip.end_time:.1f}s ({clip.duration:.1f}s)")

        # 5. 提取封面
        print(f"\n🖼️ 正在提取封面...")
        for clip in clips:
            if clip.status == "failed":
                continue
            # 从截取的视频中取中间帧
            mid_time = clip.start_time + (clip.duration / 2)
            success = self.video_analyzer.extract_frame(
                clip.video_path, mid_time, clip.cover_path, width=1080
            )
            if success:
                # 转为竖屏 9:16
                self._convert_to_vertical(clip.video_path, clip.video_path)
                clip.status = "cover_ready"
            else:
                clip.status = "failed"

        # 6. 生成 SEO
        print(f"\n📝 正在生成 SEO 数据...")
        seo_results = []
        for clip in clips:
            if clip.status == "failed":
                continue
            seo = self.seo_generator.generate(
                source_video_title=os.path.basename(video_path),
                segment_index=clip.index,
                duration=clip.duration,
            )
            clip.seo = seo
            seo_results.append(seo)
            print(f"   ✅ Clip #{clip.index}: {seo['title']}")

        # 7. 保存元数据
        meta_path = output_dir / "shorts_metadata.json"
        meta_data = {
            "source_video": video_path,
            "category": self.category,
            "total_clips": len(clips),
            "successful": sum(1 for c in clips if c.status != "failed"),
            "clips": [
                {
                    "index": c.index,
                    "start": c.start_time,
                    "end": c.end_time,
                    "duration": c.duration,
                    "video": c.video_path,
                    "cover": c.cover_path,
                    "status": c.status,
                    "seo": c.seo,
                }
                for c in clips
            ],
        }
        meta_path.write_text(json.dumps(meta_data, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"\n💾 元数据已保存到: {meta_path}")

        return clips

    def _extract_clip(self, source: str, clip: ShortClip, fps: int = 30) -> bool:
        """截取单个片段。"""
        try:
            subprocess_cmd = [
                "ffmpeg", "-y",
                "-ss", str(clip.start_time),
                "-i", source,
                "-t", str(clip.duration),
                "-c:v", "libx264",
                "-preset", "fast",
                "-crf", "23",
                "-c:a", "aac",
                "-b:a", "128k",
                "-r", str(fps),
                clip.video_path,
            ]
            result = subprocess.run(subprocess_cmd, capture_output=True, timeout=120)
            return result.returncode == 0
        except Exception as e:
            print(f"   ❌ 截取失败: {e}")
            return False

    def _convert_to_vertical(self, source: str, output: str):
        """将横屏视频转为竖屏 9:16（居中裁剪）。"""
        try:
            subprocess.run([
                "ffmpeg", "-y", "-i", source,
                "-vf", "crop=min(iw\\,ih*9/16):ih*9/16:((iw-ow/2)/2):0",
                "-c:v", "libx264", "-preset", "fast",
                "-c:a", "copy",
                output
            ], capture_output=True, timeout=60)
        except Exception:
            pass

    def _uniform_split(self, total_duration: float, count: int, min_dur: float, max_dur: float) -> List[Tuple[float, float]]:
        """均匀分割（备用方案）。"""
        clips = []
        clip_duration = min(max_dur, total_duration / count)
        clip_duration = max(min_dur, clip_duration)
        used = 0

        for i in range(count):
            start = used + 2  # 2秒缓冲
            end = min(start + clip_duration, total_duration - 2)
            if end > start:
                clips.append((start, end))
                used = end

        return clips
