from pathlib import Path
import json
from typing import Any, Dict


class ConfigManager:
    """各Cogから独立してデータ保存・取得を行う管理クラス

    各機能(feature_name)ごとに data/{feature_name}.json としてデータを完全分離して保存します。
    """

    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)

    def _get_file_path(self, feature_name: str) -> Path:
        return self.data_dir / f"{feature_name}.json"

    def load(self, feature_name: str) -> Dict[str, Any]:
        """指定した機能(feature_name)の設定を読み込む"""
        file_path = self._get_file_path(feature_name)
        if file_path.exists():
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"❌ [{feature_name}] 設定ファイルの読み込みエラー: {e}")
                return {}
        return {}

    def save(self, feature_name: str, data: Dict[str, Any]) -> None:
        """指定した機能(feature_name)の設定を保存する"""
        file_path = self._get_file_path(feature_name)
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"❌ [{feature_name}] 設定ファイルの保存エラー: {e}")