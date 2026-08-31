"""将 PyInstaller 目录整理为带校验和的发布压缩包。"""

from __future__ import annotations

import argparse
import hashlib
import zipfile
from pathlib import Path


def parse_args() -> argparse.Namespace:
    """解析 CI 和本地打包共用的命令行参数。"""
    parser = argparse.ArgumentParser(description="打包 CommForge 发布目录")
    parser.add_argument("--input-dir", type=Path, default=Path("dist/CommForge"))
    parser.add_argument("--output-dir", type=Path, default=Path("artifacts"))
    parser.add_argument("--platform", required=True)
    parser.add_argument("--arch", required=True)
    parser.add_argument("--version", required=True)
    return parser.parse_args()


def sha256(path: Path) -> str:
    """分块计算文件 SHA-256，避免大压缩包一次性读入内存。"""
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def package_release(
    input_dir: Path,
    output_dir: Path,
    platform_name: str,
    architecture: str,
    version: str,
    project_root: Path | None = None,
) -> tuple[Path, Path]:
    """创建干净的 CommForge ZIP，并生成对应校验文件。"""
    if not input_dir.is_dir():
        raise FileNotFoundError(f"找不到打包目录：{input_dir}")

    output_dir.mkdir(parents=True, exist_ok=True)
    archive_name = f"CommForge-v{version}-{platform_name}-{architecture}"
    archive_path = output_dir / f"{archive_name}.zip"
    if archive_path.exists():
        archive_path.unlink()

    excluded_roots = {"data", "logs"}
    with zipfile.ZipFile(
        archive_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9
    ) as bundle:
        bundle.writestr(f"{input_dir.name}/", b"")
        for source in sorted(input_dir.rglob("*")):
            relative = source.relative_to(input_dir)
            if relative.parts and relative.parts[0].lower() in excluded_roots:
                continue
            archive_member = Path(input_dir.name) / relative
            if source.is_dir():
                bundle.writestr(archive_member.as_posix().rstrip("/") + "/", b"")
            else:
                bundle.write(source, archive_member.as_posix())

        # 文档直接放在应用目录顶层，用户无需进入 PyInstaller 的 _internal 查找。
        if project_root is not None:
            documents = {
                project_root / "README.md": Path(input_dir.name) / "README.md",
                project_root / "docs" / "USER_GUIDE.md": (
                    Path(input_dir.name) / "docs" / "USER_GUIDE.md"
                ),
            }
            for source, archive_member in documents.items():
                if source.is_file():
                    bundle.write(source, archive_member.as_posix())
    checksum_path = archive_path.with_suffix(".zip.sha256")
    checksum_path.write_text(
        f"{sha256(archive_path)}  {archive_path.name}\n", encoding="utf-8"
    )
    return archive_path, checksum_path


def main() -> int:
    """执行发布压缩并向 CI 日志输出生成路径。"""
    args = parse_args()
    archive, checksum = package_release(
        args.input_dir,
        args.output_dir,
        args.platform,
        args.arch,
        args.version,
        Path(__file__).resolve().parents[1],
    )
    print(archive.resolve())
    print(checksum.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
