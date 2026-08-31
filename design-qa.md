# CommForge 第二轮界面重构 Design QA

## 对照目标

- 最终实现截图：
  - `docs/images/qa-dashboard.png`、`docs/images/qa-communications.png`：1440 × 880。
  - `docs/images/qa-receive-rules-wide.png`、`docs/images/qa-automation-wide.png`：1920 × 994。
  - `docs/images/qa-receive-editor-tested.png`：1280 × 760。
  - `docs/images/qa-automation-editor.png`：760 × 560。
- 密度：Windows 原生 Qt，device pixel ratio 1；截图由 `scripts/capture_redesign.py` 统一生成。
- 状态：浅色主题、示例通信与规则、自动化任务保持原始停用状态；回归脚本禁用真实端口、定时器和报文发送。

## Findings

当前没有未解决的 P0、P1 或 P2 问题。

- 字体与排版：正文使用 Microsoft YaHei UI，页面标题 21 px、区块标题 14 px、表格正文 13 px；层级、行距和字重统一，无可见裁切。所有表头均水平居中，名称及长内容保持左对齐，状态和数值居中。
- 间距与布局：表格行高统一为 52 px，按钮最小高度 34 px，行内按钮为 30 px 并垂直居中。1440 与 1920 两种宽度均无重叠、截断或操作列消失。
- 颜色与视觉令牌：背景、卡片、表头、隔行底色、主紫色以及成功/信息/警告/错误状态色已统一。指标卡使用四种独立强调色，避免页面过于单调。
- 图标与资源：总览指标卡使用真实 Qt/Windows 系统图标，通信、自动化、发送和接收不再复用同一个图标。没有自制 SVG、字符占位图或 CSS 绘图。
- 文案与内容：接收规则和自动化任务使用面向用户的中文标签；枚举值只在需要精确表达协议时保留。规则链路用“接收规则 → 发送规则”表达执行关系。
- 交互：通信和规则列表默认选中第一行；自动化新增、编辑、启停、执行和删除都有实际处理和反馈。接收规则支持列表、编辑、字段增删改、实时匹配和解析结果。

## 比较迭代记录

1. P1：表头左对齐而状态胶囊居中，造成字段视觉错位。
   - 修复：公共表格表头统一水平居中，数据列按语义分别左对齐或居中。
   - 证据：`docs/images/qa-dashboard.png`、`docs/images/qa-communications.png`。
2. P1：通信、报文规则和自动化任务的行内按钮被表格行高裁掉。
   - 修复：新增统一行内操作容器，按钮固定 30 px 高，表格行高提高到 52 px，并为操作列保留固定宽度。
   - 证据：`docs/images/qa-communications.png`、`docs/images/qa-message-rules.png`、`docs/images/qa-automation.png`。
3. P1：接收规则把列表、字段和测试堆在一个大页面中，空白多且层级不清。
   - 修复：主页面改为一行一条规则的列表；新增/编辑/测试进入三栏编辑器。
   - 证据：`docs/images/qa-receive-rules-wide.png`、`docs/images/qa-receive-editor-tested.png`。
4. P0：自动化按钮读取了没有 `QTableWidgetItem` 的启用列，导致选中任务始终为空。
   - 修复：任务编号改由实际存在的任务名称单元格承载；同时加入行内启停、执行、编辑和底部反馈。
   - 证据：`scripts/capture_redesign.py` 已验证选中、启停状态往返及模拟执行结果；`docs/images/qa-automation-wide.png` 展示最终状态。
5. P2：状态列按短表头自动计算宽度，仍可能裁掉“未启动/已停止”。
   - 修复：胶囊状态列使用语义固定宽度，不再依赖表头文本估算。
   - 证据：`docs/images/qa-communications.png`、`docs/images/qa-automation.png`。
6. P2：重复刷新时旧的单元格组件可能在窗口调整尺寸瞬间留下残影。
   - 修复：含状态胶囊和行内按钮的表格刷新前先清空行，再构建新组件。
   - 证据：最终 `docs/images/qa-receive-rules-wide.png` 与 `docs/images/qa-automation-wide.png` 无重复控件或错位。

## 交互和回归验证

- 8 个主页面逐页执行：表头居中断言、可见按钮尺寸检查、原生 Windows Qt 截图。
- 自动化任务：选中任务、启停切换、状态恢复、立即执行回调均通过；执行使用本地模拟回执，未打开端口或发送报文。
- 接收规则：`AA 55 01 03` 成功匹配 `AA 55 ?? 03`，解析 `address = 1`。
- `python -m compileall -q commforge main.py scripts`：通过。
- `pytest -q -p no:cacheprovider`：26 项全部通过。

## 可访问性与剩余 P3

- 当前可确认：文字对比度、可见焦点边框、按钮尺寸、非纯颜色状态表达和键盘可聚焦控件均保持可读。
- 截图无法证明完整屏幕阅读器语义和所有键盘顺序；这些属于后续专项验证，不影响本轮视觉与核心交互验收。
- P3：Qt 原生图标与最初概念稿的专用图标并非完全相同，但风格统一且为真实图标资源。

final result: passed
