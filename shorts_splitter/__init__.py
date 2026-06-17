"""ShortsSplitter - 从长视频智能拆分 YouTube Shorts。"""

__version__ = "0.1.0"

from shorts_splitter.splitter import VideoSplitter
from shorts_splitter.analyzer import AudioAnalyzer, VideoAnalyzer
from shorts_splitter.seo import ShortSEO

__all__ = ["VideoSplitter", "AudioAnalyzer", "VideoAnalyzer", "ShortSEO"]
