from __future__ import annotations

import io
import json
import shutil
import sqlite3
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath


class BackupService:
    def __init__(self, data_path: Path):
        self.data_path = data_path
        self.access_path = data_path / "access.sqlite"

    def export(self) -> bytes:
        output = io.BytesIO()
        with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive, tempfile.TemporaryDirectory() as directory:
            snapshot = Path(directory) / "access.sqlite"
            source, target = sqlite3.connect(self.access_path), sqlite3.connect(snapshot)
            try:
                source.backup(target)
            finally:
                target.close()
                source.close()
            archive.writestr("backup.json", json.dumps({"format": "contract-check-agent-backup", "version": 1, "created_at": datetime.now(timezone.utc).isoformat()}))
            archive.write(snapshot, "access.sqlite")
            self._write_directory(archive, "reports", {".json", ".md"})
            self._write_directory(archive, "generations", {".json", ".md", ".docx"})
            self._write_directory(archive, "knowledge_sources", {".yaml", ".txt"})
        return output.getvalue()

    def restore(self, content: bytes) -> None:
        if len(content) > 500 * 1024 * 1024:
            raise ValueError("备份文件不能超过 500MB")
        try:
            archive = zipfile.ZipFile(io.BytesIO(content))
        except zipfile.BadZipFile as exc:
            raise ValueError("请选择有效的 ZIP 备份文件") from exc
        with archive, tempfile.TemporaryDirectory() as directory:
            destination = Path(directory)
            entries = [entry for entry in archive.infolist() if not entry.is_dir()]
            if len(entries) > 10000 or sum(entry.file_size for entry in entries) > 1024 * 1024 * 1024:
                raise ValueError("备份文件内容过大")
            names = {entry.filename for entry in entries}
            if "backup.json" not in names or "access.sqlite" not in names:
                raise ValueError("备份文件缺少必要数据")
            for entry in entries:
                if not self._allowed(entry.filename):
                    raise ValueError("备份文件包含不支持的数据")
                target = destination / PurePosixPath(entry.filename)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(archive.read(entry))
            try:
                manifest = json.loads((destination / "backup.json").read_text("utf-8"))
            except (OSError, ValueError) as exc:
                raise ValueError("备份说明文件无效") from exc
            if manifest.get("format") != "contract-check-agent-backup" or manifest.get("version") != 1:
                raise ValueError("备份文件版本不受支持")
            try:
                connection = sqlite3.connect(destination / "access.sqlite")
                try:
                    connection.execute("SELECT employee_id FROM employees LIMIT 1").fetchone()
                finally:
                    connection.close()
            except sqlite3.DatabaseError as exc:
                raise ValueError("备份中的访问数据库无效") from exc
            self.data_path.mkdir(parents=True, exist_ok=True)
            shutil.copy2(destination / "access.sqlite", self.access_path)
            for name in ("reports", "generations", "knowledge_sources", "qdrant"):
                target = self.data_path / name
                if target.exists():
                    shutil.rmtree(target)
            for name in ("reports", "generations", "knowledge_sources"):
                source = destination / name
                target = self.data_path / name
                if source.exists():
                    shutil.copytree(source, target)
                else:
                    target.mkdir(parents=True, exist_ok=True)

    def _write_directory(self, archive: zipfile.ZipFile, name: str, suffixes: set[str]) -> None:
        directory = self.data_path / name
        if not directory.exists():
            return
        for path in directory.rglob("*"):
            if path.is_file() and path.suffix.lower() in suffixes:
                archive.write(path, path.relative_to(self.data_path).as_posix())

    @staticmethod
    def _allowed(name: str) -> bool:
        path = PurePosixPath(name)
        if path.is_absolute() or ".." in path.parts:
            return False
        if name in {"backup.json", "access.sqlite"}:
            return True
        if path.parts[:1] == ("reports",):
            return path.suffix in {".json", ".md"}
        if path.parts[:1] == ("generations",):
            return path.suffix in {".json", ".md", ".docx"}
        return path.parts[:1] == ("knowledge_sources",) and path.suffix in {".yaml", ".txt"}
