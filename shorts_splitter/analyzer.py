"""音频分析器 - 分析音频能量、静音段、高潮点。"""

import subprocess
import json
from typing import List, Tuple, Optional
from dataclasses import dataclass


@dataclass
class AudioSegment:
    """音频片段信息。"""
    start: float      # 起始时间（秒）
    end: float        # 结束时间（秒）
    duration: float   # 时长
    energy: float     # 平均能量值 (0-1)
    type: str         # "high_energy", "medium", "silence", "transition"


class AudioAnalyzer:
    """音频能量分析器。"""

    def analyze(self, video_path: str, segment_duration: float = 5.0) -> List[AudioSegment]:
        """分析视频音频，返回分段信息。

        使用 ffmpeg 的 astats 过滤器分析每段音频的能量水平。

        Args:
            video_path: 视频文件路径
            segment_duration: 每段分析的时长（秒），默认5秒

        Returns:
            AudioSegment 列表
        """
        segments = []

        # 第一步：获取视频总时长
        total_duration = self._get_duration(video_path)
        if total_duration is None:
            return segments

        # 第二步：提取音频统计信息
        stats = self._get_audio_stats(video_path, segment_duration)

        # 第三步：根据统计信息分类每段
        for stat in stats:
            start = float(stat["start"])
            rms = float(stat["rms"])  # 均方根，范围通常 -60 到 0
            energy = self._rms_to_energy(rms)

            seg_type = self._classify_segment(energy, stat.get("dc_component", 0))

            segments.append(AudioSegment(
                start=start,
                end=min(start + segment_duration, total_duration),
                duration=min(segment_duration, total_duration - start),
                energy=energy,
                type=seg_type,
            ))

        return segments

    def find_best_cut_points(
        self,
        video_path: str,
        target_count: int = 5,
        min_clip_duration: float = 15.0,
        max_clip_duration: float = 58.0,
    ) -> List[Tuple[float, float]]:
        """找到最佳的截取点。

        Args:
            video_path: 视频文件路径
            target_count: 期望的 Shorts 数量
            min_clip_duration: 最短片段时长（秒）
            max_clip_duration: 最长片段时长（秒）

        Returns:
            (start, end) 时间戳列表
        """
        total_duration = self._get_duration(video_path)
        if not total_duration or total_duration < 60:
            return []

        segments = self.analyze(video_path, segment_duration=5.0)

        if not segments:
            return []

        # 过滤掉太短或静音的片段
        usable = [s for s in segments if s.duration >= 5 and s.type != "silence"]

        if not usable:
            usable = segments

        # 按能量排序，取高能量片段
        usable.sort(key=lambda s: s.energy, reverse=True)

        # 选择均匀分布的高能量片段作为截取点
        cut_points = []
        used_ranges = []

        for seg in usable:
            if len(cut_points) >= target_count:
                break

            # 确保不重叠
            overlap = False
            for start, end in used_ranges:
                if abs(seg.start - start) < max_clip_duration:
                    overlap = True
                    break

            if not overlap:
                clip_end = min(seg.end, seg.start + max_clip_duration)
                clip_start = max(seg.start, 2.0)  # 留2秒缓冲

                if clip_end - clip_start >= min_clip_duration:
                    cut_points.append((clip_start, clip_end))
                    used_ranges.append((clip_start, clip_end))

        # 如果不够，从剩余片段补充
        if len(cut_points) < target_count:
            for seg in segments:
                if len(cut_points) >= target_count:
                    break
                overlap = False
                for start, end in used_ranges:
                    if abs(seg.start - start) < max_clip_duration:
                        overlap = True
                        break
                if not overlap and seg.duration >= min_clip_duration:
                    cut_points.append((seg.start, seg.end))
                    used_ranges.append((seg.start, seg.end))

        return cut_points[:target_count]

    def _get_duration(self, video_path: str) -> Optional[float]:
        """获取视频时长。"""
        try:
            result = subprocess.run(
                ["ffprobe", "-v", "error", "-show_entries", "format=duration",
                 "-of", "json", video_path],
                capture_output=True, text=True, timeout=30
            )
            data = json.loads(result.stdout)
            return float(data["format"]["duration"])
        except Exception:
            return None

    def _get_audio_stats(self, video_path: str, segment_duration: float) -> List[dict]:
        """使用 ffmpeg astats 获取分段音频统计。"""
        stats = []
        total = self._get_duration(video_path)
        if not total:
            return stats

        try:
            # 逐段分析音频
            num_segments = int(total / segment_duration) + 1
            for i in range(num_segments):
                start = i * segment_duration
                if start >= total:
                    break

                result = subprocess.run(
                    ["ffmpeg", "-y", "-ss", str(start), "-t", str(segment_duration),
                     "-i", video_path, "-af", "astats=metadata=1:reset=1",
                     "-f", "null", "-"],
                    capture_output=True, text=True, timeout=30
                )

                # 解析 stderr 中的 RMS 值
                rms = self._parse_rms(result.stderr)
                dc = self._parse_dc(result.stderr)

                stats.append({
                    "start": start,
                    "rms": rms,
                    "dc_component": dc,
                })
        except Exception:
            pass

        return stats

    def _parse_rms(self, stderr: str) -> float:
        """从 ffmpeg astats 输出中解析 RMS。"""
        for line in stderr.split("\n"):
            if "Overall RMS level" in line or "RMS level" in line:
                try:
                    parts = line.split(":")
                    if len(parts) >= 2:
                        return float(parts[-1].strip().rstrip("dB"))
                except (ValueError, IndexError):
                    pass
        return -30.0  # 默认中等值

    def _parse_dc(self, stderr: str) -> float:
        """解析 DC 分量。"""
        for line in stderr.split("\n"):
            if "DC offset" in line:
                try:
                    return float(line.split(":")[-1].strip())
                except ValueError:
                    pass
        return 0.0

    def _rms_to_energy(self, rms: float) -> float:
        """将 RMS dB 值转换为 0-1 能量值。"""
        # RMS 通常在 -60 到 0 之间，映射到 0-1
        energy = max(0, min(1, (rms + 60) / 60))
        return round(energy, 3)

    def _classify_segment(self, energy: float, dc: float) -> str:
        """分类片段类型。"""
        if energy < 0.05:
            return "silence"
        elif energy > 0.6:
            return "high_energy"
        elif energy > 0.3:
            return "medium"
        else:
            return "low_energy"
