"""发布压缩包和冻结路径的回归测试。"""

from __future__ import annotations

import zipfile
from pathlib import Path

from commforge.app import paths
from scripts.package_release import package_release


def test_frozen_project_root_uses_executable_directory(monkeypatch) -> None:
    """冻结应用应把数据和日志保存在可执行文件旁边。"""
    executable = (Path.cwd() / "frozen-app" / "CommForge").resolve()
    monkeypatch.setattr(paths.sys, "frozen", True, raising=False)
    monkeypatch.setattr(paths.sys, "executable", str(executable))

    assert paths.resolve_project_root() == executable.parent


def test_package_release_keeps_single_application_root() -> None:
    """发布 ZIP 解压后应包含单一 CommForge 顶层目录和校验文件。"""
    input_dir = Path(__file__).parent / "fixtures" / "CommForge"
    output_dir = Path(__file__).parent / "runtime"
    archive = output_dir / "CommForge-v1.0.0-windows-x64.zip"
    checksum = archive.with_suffix(".zip.sha256")
    try:
        archive, checksum = package_release(
            input_dir,
            output_dir,
            "windows",
            "x64",
            "1.0.0",
        )

        with zipfile.ZipFile(archive) as bundle:
            assert bundle.namelist() == ["CommForge/", "CommForge/CommForge.bin"]
        assert archive.name in checksum.read_text(encoding="utf-8")
    finally:
        # 测试产物不进入仓库，成功或失败都尽量清理。
        archive.unlink(missing_ok=True)
        checksum.unlink(missing_ok=True)
