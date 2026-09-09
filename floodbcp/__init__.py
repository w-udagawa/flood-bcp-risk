"""floodbcp: 洪水 BCP リスク一次スクリーニングのスコアリングエンジン。

Python 3.11 標準ライブラリのみで実装する（docs/02_要件定義書.md NFR-07）。
閾値・マトリクス・重み・対策条件はコードに埋め込まず、
config/scoring_v0.1.0.json と config/measures.json から読み込む。
"""

__version__ = "0.1.0"

# docs/03_スコアリング仕様.md の score_version と一致させる。
SCORE_VERSION = "0.1.0"

__all__ = ["__version__", "SCORE_VERSION"]
