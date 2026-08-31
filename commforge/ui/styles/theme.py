"""CommForge 统一浅色主题。"""

LIGHT_THEME = r"""
* {
    font-family: "Microsoft YaHei UI", "HarmonyOS Sans SC", "Segoe UI";
    font-size: 13px;
    color: #24324a;
}
QMainWindow, QWidget#Root { background: #f2f5fa; }
QWidget#Sidebar { background: #fbfcff; border-right: 1px solid #dce3ef; }
QLabel#BrandTitle { font-size: 18px; font-weight: 700; color: #111827; }
QLabel#BrandMark { color: #7657ff; font-size: 23px; font-weight: 800; }
QLabel#Version { color: #98a2b3; font-size: 11px; }
QLabel#PageTitle { color: #101828; font-size: 21px; font-weight: 700; }
QLabel#SectionTitle { color: #17233b; font-size: 14px; font-weight: 650; }
QLabel#Muted { color: #75839a; font-size: 12px; }
QPushButton#NavButton {
    border: 0; border-radius: 7px; background: transparent; color: #344054;
    min-height: 42px; padding: 0 14px; text-align: left;
}
QPushButton#NavButton:hover { background: #f1efff; color: #5d49df; }
QPushButton#NavButton:checked { background: #ebe8ff; color: #5f45e8; font-weight: 600; border-left: 3px solid #7057f6; }
QFrame#Card, QFrame#Panel {
    background: #ffffff; border: 1px solid #dce3ed; border-radius: 10px;
}
QLabel#MetricValue { color: #111827; font-size: 27px; font-weight: 600; }
QLabel#MetricDelta { color: #45a36b; font-size: 11px; }
QPushButton {
    background: #ffffff; border: 1px solid #d2dae7; border-radius: 7px;
    min-height: 34px; padding: 0 13px; color: #34435d; font-weight: 500;
}
QPushButton:hover { border-color: #9e91ee; background: #f8f7ff; color: #5f46df; }
QPushButton:pressed { background: #ebe8ff; }
QPushButton:disabled { background:#f3f5f8; border-color:#e2e6ed; color:#a5adba; }
QPushButton#PrimaryButton { background: #6f58f6; border-color: #6f58f6; color: white; font-weight:600; }
QPushButton#PrimaryButton:hover { background: #6047e8; }
QPushButton#DangerButton { color: #e34a55; background: #fff7f7; border-color: #ffd5d8; }
QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QTextEdit, QPlainTextEdit {
    background: #ffffff; border: 1px solid #d5ddea; border-radius: 7px;
    min-height: 34px; padding: 0 10px; selection-background-color: #7560ee;
}
QTextEdit, QPlainTextEdit { padding: 8px; }
QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus,
QTextEdit:focus, QPlainTextEdit:focus { border-color: #8065f4; }
QTableWidget, QTableView, QListWidget {
    background: #ffffff; border: 0; border-radius: 7px;
    gridline-color: #e9edf3; alternate-background-color: #f8faff;
    selection-background-color: #ece9ff; selection-color: #4f36d7;
}
QHeaderView::section {
    background: #f2f5fa; color: #526078; border: 0; border-bottom: 1px solid #dce3ed;
    padding: 11px 10px; font-size: 12px; font-weight: 650;
}
QTableWidget::item { padding: 10px 12px; border-bottom: 1px solid #e9edf3; }
QTableWidget::item:selected { background: #ece9ff; color: #4f36d7; }
QListWidget::item { border-bottom: 1px solid #edf0f5; padding: 8px; }
QListWidget::item:selected { background: #f1efff; color: #593bdb; }
QTabWidget::pane { border: 0; }
QTabBar::tab { background: transparent; padding: 8px 16px; color: #667085; border-bottom: 2px solid transparent; }
QTabBar::tab:selected { color: #6948ef; border-bottom-color: #7657ff; }
QScrollBar:vertical { width: 9px; background: transparent; margin: 2px; }
QScrollBar::handle:vertical { background: #ccd3df; border-radius: 4px; min-height: 28px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QToolTip { background: #1f2937; color: #ffffff; border: 0; padding: 6px; }
QStatusBar { background: #ffffff; border-top: 1px solid #e2e7ef; color: #667085; }
QDialog { background: #f6f7fb; }
QFrame#DialogSection { background:#ffffff;border:1px solid #e1e6ef;border-radius:9px; }
QLabel#DialogTitle { color:#101828;font-size:18px;font-weight:700; }
QLabel#ProtocolTitle { color:#1d2939;font-size:14px;font-weight:650; }
QPushButton#TableAction {
    min-height:30px;max-height:30px;padding:0 10px;border-radius:6px;
    background:#ffffff;border:1px solid #d5ddea;color:#47566f;font-size:12px;
}
QPushButton#TableAction:hover { background:#f5f3ff;border-color:#b9acf9;color:#6848ef; }
QLabel#ResultSuccess { background:#eaf8ef;color:#278a50;border:1px solid #c9ead5;border-radius:7px;padding:9px 12px;font-weight:600; }
QLabel#ResultError { background:#fff1f2;color:#c93f4a;border:1px solid #ffd1d5;border-radius:7px;padding:9px 12px;font-weight:600; }
QLabel#InfoPill { background:#eef4ff;color:#3975d2;border:1px solid #d5e3ff;border-radius:7px;padding:7px 10px;font-weight:600; }
"""
