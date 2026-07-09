"""zidou_lib
軽量なタグ検出器とメカナム足回りユーティリティを提供するライブラリ。

使い方の例:
from zidou_lib.tag_detector import TagDetector
from zidou_lib.drivetrain import mecanum_ik

det = TagDetector()
det.start()
time.sleep(1.0)
print(det.get_latest_tags())
det.stop()
"""

from .tag_detector import TagDetector
from .drivetrain import mecanum_ik, blend_commands

__all__ = ["TagDetector", "mecanum_ik", "blend_commands"]
