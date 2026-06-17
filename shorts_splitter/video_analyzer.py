"""视频分析器 - 获取视频信息、提取帧。"""

import subprocess
import json
from typing import Optional, List
from dataclasses import dataclass


@dataclass
class VideoInfo:
    """视频基本信息。"""
    path: str
    duration: float
    width: int
    height: int
    fps: float
    bitrate: int
    video_codec: str
    audio_codec: str
    format: str


class VideoAnalyzer:
    """视频信息分析器。"""

    def get_info(self, video_path: str) -> Optional[VideoInfo]:
        """获取视频详细信息。"""
        try:
            result = subprocess.run(
                ["ffprobe", "-v", "quiet", "-print_format", "json",
                 "-show_format", "-show_streams", video_path],
                capture_output=True, text=True, timeout=30
            )
            data = json.loads(result.stdout)

            duration = float(data["format"]["duration"])

            # 找到视频流和音频流
            video_stream = None
            audio_stream = None
            for stream in data["streams"]:
                if stream["codec_type"] == "video" and not video_stream:
                    video_stream = stream
                elif stream["codec_type"] == "audio" and not audio_stream:
                    audio_stream = stream

            fps = 0
            if video_stream:
                fps_str = video_stream.get("r_frame_rate", "0/1")
                if "/" in fps_str:
                    num, den = fps_str.split("/")
                    fps = float(num) / float(den) if float(den) != 0 else 0
                else:
                    fps = float(fps_str)

            return VideoInfo(
                path=video_path,
                duration=duration,
                width=int(video_stream.get("width", 0)),
                height=int(video_stream.get("height", 0)),
                fps=round(fps, 2),
                bitrate=int(data["format"].get("bit_rate", 0)),
                video_codec=video_stream["codec_name"] if video_stream else "unknown",
                audio_codec=audio_stream["codec_name"] if audio_stream else "unknown",
                format=data["format"].get("format_name", "unknown"),
            )
        except Exception:
            return None

    def extract_frame(self, video_path: str, time: float, output_path: str, width: int = 1080) -> bool:
        """从视频中提取指定时间的帧。"""
        try:
            subprocess.run(
                ["ffmpeg", "-y", "-ss", str(time), "-i", video_path,
                 "-vframes", "1", "-vf", f"scale={width}:-1",
                 output_path],
                capture_output=True, timeout=30
            )
            return True
        except Exception:
            return False

    def find_best_frame(self, video_path: str, start: float, end: float, count: int = 5) -> List[float]:
        """在时间段内找最佳帧的时间点（均匀分布）。"""
        duration = end - start
        if duration <= 0:
            return []

        # 跳过前10%和后10%，找中间最稳的帧
        margin = duration * 0.1
        points = []
        for i in range(count):
            t = start + margin + (duration - 2 * margin) * (i + 1) / (count + 1)
            points.append(round(t, 2))

        return points
