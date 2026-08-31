"""PyInstaller 的 CommForge 多平台目录打包配置。"""

import sys
from pathlib import Path


PROJECT_ROOT = Path(SPECPATH).resolve()

analysis = Analysis(
    [str(PROJECT_ROOT / "main.py")],
    pathex=[str(PROJECT_ROOT)],
    binaries=[],
    datas=[],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)


def is_external_windows_icu(entry: tuple[str, str, str]) -> bool:
    """识别被 PATH 污染收集、且并非 PySide6 自带的 Windows ICU。"""
    destination = Path(entry[0]).name.lower()
    source = str(entry[1]).lower()
    is_icu = destination == "icuuc.dll" or destination.startswith("icudt")
    return is_icu and "pyside6" not in source


if sys.platform == "win32":
    # Windows 自带 Qt 需要的系统 ICU；过滤 Poppler/Conda 等 PATH 中的同名不兼容 DLL。
    analysis.binaries = [
        entry for entry in analysis.binaries if not is_external_windows_icu(entry)
    ]

pyz = PYZ(analysis.pure)

executable = EXE(
    pyz,
    analysis.scripts,
    [],
    exclude_binaries=True,
    name="CommForge",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

bundle = COLLECT(
    executable,
    analysis.binaries,
    analysis.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="CommForge",
)
