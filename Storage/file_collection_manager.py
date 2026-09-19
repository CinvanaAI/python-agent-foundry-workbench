import re
import shutil
from pathlib import Path
from typing import List, Optional


class FileCollectionManager:
    def __init__(
        self,
        base_dir: str,
        folder_name: str,
        file_extension: str = ".json",
        use_item_subfolder: bool = False,
        explicit_storage_dir: Optional[str] = None,
    ) -> None:
        self.base_dir = self._normalize_base_dir(base_dir)
        self.folder_name = folder_name
        self.file_extension = self._normalize_file_extension(file_extension)
        self.use_item_subfolder = use_item_subfolder

        self.storage_home = self.base_dir / "Storage"
        self.storage_root = self.storage_home / "Generated Artifacts"

        if explicit_storage_dir is not None and str(explicit_storage_dir).strip():
            self.storage_dir = Path(explicit_storage_dir).expanduser().resolve()
        else:
            self.storage_dir = self.storage_root / self.folder_name

        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def _normalize_base_dir(self, base_dir: str) -> Path:
        path = Path(base_dir).resolve()
        lower_name = path.name.lower()

        if lower_name == "storage":
            return path.parent

        if lower_name == "generated artifacts" and path.parent.name.lower() == "storage":
            return path.parent.parent

        return path

    def _normalize_file_extension(self, file_extension: str) -> str:
        ext = str(file_extension).strip()
        if not ext:
            raise ValueError("File extension is required.")

        if not ext.startswith("."):
            ext = f".{ext}"

        return ext

    def sanitize_name(self, raw_name: str) -> str:
        name = raw_name.strip()
        name = re.sub(r"\s+", "_", name)
        name = re.sub(r"[^A-Za-z0-9_]", "", name)
        return name

    def _get_item_directory(self, item_name: str) -> Path:
        safe_name = self.sanitize_name(item_name)
        if not safe_name:
            raise ValueError("Invalid name.")

        if self.use_item_subfolder:
            return self.storage_dir / safe_name

        return self.storage_dir

    def get_item_path(self, item_name: str) -> str:
        safe_name = self.sanitize_name(item_name)
        if not safe_name:
            raise ValueError("Invalid name.")

        item_dir = self._get_item_directory(safe_name)
        return str(item_dir / f"{safe_name}{self.file_extension}")

    def list_items(self) -> List[str]:
        items: List[str] = []

        if not self.storage_dir.exists():
            return items

        if self.use_item_subfolder:
            for path in self.storage_dir.iterdir():
                if not path.is_dir():
                    continue

                candidate = path / f"{path.name}{self.file_extension}"
                if candidate.is_file():
                    items.append(path.name)
        else:
            for path in self.storage_dir.iterdir():
                if path.is_file() and path.name.endswith(self.file_extension):
                    items.append(path.name[: -len(self.file_extension)])

        items.sort(key=str.lower)
        return items

    def item_exists(self, item_name: str) -> bool:
        try:
            path = Path(self.get_item_path(item_name))
        except ValueError:
            return False

        return path.exists()

    def save_item(self, item_name: str, content: str) -> str:
        if not item_name or not item_name.strip():
            raise ValueError("Name is required.")

        if not content or not content.strip():
            raise ValueError("Content is required.")

        file_path = Path(self.get_item_path(item_name))
        file_path.parent.mkdir(parents=True, exist_ok=True)

        new_text = content.rstrip() + "\n"
        file_path.write_text(new_text, encoding="utf-8")

        return str(file_path)

    def load_item(self, item_name: str) -> str:
        file_path = Path(self.get_item_path(item_name))

        if not file_path.exists():
            raise FileNotFoundError(f"Item not found: {file_path}")

        return file_path.read_text(encoding="utf-8")

    def delete_item(self, item_name: str) -> str:
        file_path = Path(self.get_item_path(item_name))

        if not file_path.exists():
            raise FileNotFoundError(f"Item not found: {file_path}")

        deleted_path = str(file_path)

        if self.use_item_subfolder:
            item_dir = file_path.parent
            shutil.rmtree(item_dir)
            return deleted_path

        file_path.unlink()
        return deleted_path