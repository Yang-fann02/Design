# Frontend CSS 维护说明

本目录使用模块化拆分 + BEM 命名规范。

## 文件职责

- `frontend.PC-Mphone.css`：入口文件，只负责按顺序 `@import`。
- `frontend.PC.tokens.css`：PC 公共设计令牌（颜色、圆角、阴影、尺寸）和全局重置。
- `frontend.PC.layout.css`：PC 页面骨架（侧边栏、头部、内容区、导航交互结构）。
- `frontend.PC.components.css`：PC 通用组件（按钮、卡片、标题、工具类）。
- `frontend.PC.dashboard.css`：PC 业务展示区（统计卡片、图表容器、表格）。
- `frontend.PC.modal.css`：PC 日期筛选弹窗与日历选择器。
- `frontend.Mphone.responsive.css`：Mphone 响应式规则（平板/手机断点覆盖）。

## 命名规范（BEM）

采用 `fd-` 前缀，避免与第三方样式冲突：

- Block：`fd-stats`
- Element：`fd-stats__card`
- Modifier：`fd-stats__card--blue`
- 状态类：`is-active` / `is-enabled` / `is-selected`

### 平台标识规则（PC / Mphone）

为便于区分平台代码，命名统一带平台标识：

- **CSS 文件**：PC 文件使用 `frontend.PC.*.css`；手机端响应式文件使用 `frontend.Mphone.*.css`。
- **DOM class**：PC 结构类使用 `fd-pc-*`（如 `fd-pc-layout__sidebar`）；移动端导航交互类使用 `fd-mphone-*`（如 `fd-mphone-nav__hamburger`）。
- **DOM id**：平台相关节点统一用 `pc-` 或 `mphone-` 前缀（如 `pc-category-chart`、`pc-date-modal`、`mphone-hamburger`）。
- **JS 命名**：PC 主逻辑函数/变量使用 `pc*` 前缀；移动端交互函数/变量使用 `mphone*` 前缀。

推荐示例：

- 文件：`frontend.PC.layout.css`、`frontend.Mphone.responsive.css`
- class：`fd-pc-sidebar__item`、`fd-mphone-nav__overlay`
- id：`pc-expense-table`、`pc-btn-date-confirm`、`mphone-sidebar-overlay`
- JS：`pcLoadStatistics()`、`pcSetupYearOptions()`、`mphoneToggleSidebar()`

建议：

- 不直接使用无前缀的通用类名（如 `card`、`title`、`active`）。
- 结构类和状态类分离：结构写在 BEM，状态用 `is-*`。

## 新增样式的推荐流程

1. 先判断归属模块（布局/组件/业务/弹窗/响应式）。
2. 在对应文件中新增 BEM 类，不跨文件堆叠。
3. 若需要全局颜色或尺寸，先加到 `frontend.PC.tokens.css` 变量。
4. 在 `frontend.html` 只使用 `fd-*` 类名。
5. 涉及交互状态时，JS 通过 `classList` 切换 `is-*` 类。

## 调整顺序建议

优先调整顺序：

1. `frontend.PC.tokens.css`（变量）
2. 模块文件（`frontend.PC.layout.css` / `frontend.PC.components.css` / `frontend.PC.dashboard.css` / `frontend.PC.modal.css`）
3. `frontend.Mphone.responsive.css`（断点覆盖）

这样可以降低样式覆盖冲突。

## 常见注意点

- 修改侧边栏宽度时，同时检查 JS 中对主区 `margin-left` 的同步逻辑。
- 新增图表容器时，复用 `fd-charts__container`，保证尺寸一致。
- 日期按钮样式与状态依赖 `fd-filter__day-btn` + `is-*`，不要改成内联样式。

## 重构检查清单

每次涉及样式/DOM/交互重构时，建议按以下清单逐项检查：

- 命名是否带平台标识：PC 使用 `PC` / `pc`，手机端使用 `Mphone` / `mphone`。
- 文件命名是否符合规则：`frontend.PC.*.css`、`frontend.Mphone.*.css`。
- class 命名是否符合规则：`fd-pc-*`、`fd-mphone-*`，并保持 BEM 结构。
- id 命名是否符合规则：平台相关节点统一使用 `pc-*`、`mphone-*`。
- JS 命名是否符合规则：PC 逻辑为 `pc*`，移动端逻辑为 `mphone*`。
- HTML、CSS、JS 引用是否全部同步（避免只改一处导致失效）。
- 旧命名是否清理干净（无残留类名、id、函数名、变量名）。
- 响应式行为是否正常（`<=768px`、`<=480px` 断点都需验证）。
- 图表、表格、弹窗交互是否正常（打开/关闭、筛选、渲染、切页）。
- 文档是否同步更新（`README.md` 中职责、命名示例、规则一致）。

