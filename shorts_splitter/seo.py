"""Shorts SEO 生成器 - 为每个 Shorts 自动生成标题、描述、标签。"""

import random
from typing import List, Optional, Dict
from dataclasses import dataclass


@dataclass
class ShortSEO:
    """Shorts SEO 数据。"""
    title: str
    description: str
    hashtags: str
    suggested_timecodes: List[str]


class ShortSEOGenerator:
    """Shorts SEO 生成器。"""

    def __init__(self, category: str = "blues"):
        self.category = category
        self.templates = self._get_templates()

    def generate(
        self,
        source_video_title: str,
        segment_index: int,
        duration: float,
        mood: Optional[str] = None,
        scene: Optional[str] = None,
    ) -> Dict:
        """生成单个 Shorts 的 SEO 数据。

        Args:
            source_video_title: 原始长视频标题
            segment_index: 片段序号（从1开始）
            duration: 片段时长（秒）
            mood: 情绪词
            scene: 场景词

        Returns:
            SEO 数据字典
        """
        mood = mood or "relaxing"
        scene = scene or "chill"

        # Shorts 标题要短、抓眼球
        titles = self._generate_titles(source_video_title, segment_index, duration, mood, scene)
        best_title = titles[0]

        # Shorts 描述要极简
        description = self._generate_description(source_video_title, segment_index, mood, scene)

        # Shorts 标签主要是 hashtag
        hashtags = self._generate_hashtags(mood, scene)

        return {
            "title": best_title,
            "titles": titles,
            "description": description,
            "hashtags": hashtags,
            "segment_index": segment_index,
        }

    def _get_templates(self) -> dict:
        return {
            "blues": {
                "title_patterns": [
                    "Wait for it... 🎸 {mood} blues moment",
                    "This {scene} blues hit different 🌙",
                    "POV: It's {scene} and you hear this 🎵",
                    "The most {mood} blues guitar you'll hear today",
                    "When the {scene} vibes hit just right 🎸",
                    "{mood} blues in 60 seconds or less",
                ],
                "hashtags": [
                    "#blues", "#bluesguitar", "#shorts", "#bluesmusic",
                    "#instrumentalblues", "#bluesshorts", "#guitar",
                    "#relaxingblues", "#slowblues", "#bluesvibes",
                ],
            },
            "default": {
                "title_patterns": [
                    "Wait for it... 🎵 {mood} moment",
                    "This {scene} vibe is everything",
                    "POV: Perfect {scene} music 🎶",
                    "The most {mood} {category} moment",
                ],
                "hashtags": ["#shorts", "#viral", "#trending", "#music"],
            },
        }

    def _generate_titles(self, source_title: str, index: int, duration: float, mood: str, scene: str) -> List[str]:
        """生成 Shorts 标题。"""
        pool = self.templates.get(self.category, self.templates["default"])
        patterns = pool["title_patterns"]

        titles = []
        for pattern in patterns:
            try:
                title = pattern.format(mood=mood, scene=scene, category=self.category)
                # Shorts 标题要短
                title = title[:60]
                if title not in titles:
                    titles.append(title)
            except KeyError:
                continue

        # 补充通用标题
        extras = [
            f"Best {mood} {self.category} 🎵",
            f"{scene.title()} {self.category} vibes",
            f"This {mood} moment 🎸",
        ]
        for e in extras:
            if e not in titles:
                titles.append(e)
            if len(titles) >= 6:
                break

        return titles[:6]

    def _generate_description(self, source_title: str, index: int, mood: str, scene: str) -> str:
        """生成 Shorts 描述。"""
        return (
            f"Part {index} of our {self.category} series 🎵\n"
            f"Full video: [Link to original]\n"
            f"Mood: {mood} | Scene: {scene}\n"
            f"Subscribe for more {self.category} music!"
        )

    def _generate_hashtags(self, mood: str, scene: str) -> str:
        """生成 hashtag 字符串。"""
        pool = self.templates.get(self.category, self.templates["default"])
        hashtags = pool["hashtags"]

        # 取 5-8 个
        selected = random.sample(hashtags, min(8, len(hashtags)))
        return " ".join(selected)
