# CSS 分层体系维护手册

本目录采用**单入口 + 模块拆分 + BEM + 状态类**方式维护，共 **8 个 CSS 文件**，由 `frontend.PC-Mphone.css` 统一串联导入。

---

## 目录

1. [文件清单与职责速查](#1-文件清单与职责速查)
2. [加载顺序（必须保持）](#2-加载顺序必须保持)
3. [各文件详细说明](#3-各文件详细说明)
4. [命名规则与状态类约定](#4-命名规则与状态类约定)
5. [新增或修改样式的推荐流程](#5-新增或修改样式的推荐流程)
6. [常见改动风险点](#6-常见改动风险点)
7. [提交前检查清单](#7-提交前检查清单)

---

## 1. 文件清单与职责速查

| 文件 | 职责 | 典型修改场景 |
|------|------|-------------|
| `frontend.PC-Mphone.css` | 总入口，只做 `@import` | 新增分层文件时在此登记 |
| `frontend.PC.tokens.css` | 设计令牌、全局变量、reset | 新增颜色/圆角/动效变量 |
| `frontend.PC.layout.css` | 页面骨架、侧栏、顶栏、视图动画 | 调整侧栏宽度、顶栏结构 |
| `frontend.PC.theme.css` | 主题切换组件 + 暗色覆盖 | 新增组件的暗色适配 |
| `frontend.PC.components.css` | 跨页面通用组件（按钮、卡片等） | 新增全局复用组件 |
| `frontend.PC.dashboard.css` | 指标卡、图表容器、明细表 | 调整图表高度、指标卡颜色 |
| `frontend.PC.modal.css` | 日期筛选弹窗全套 UI | 修改弹窗结构或日历样式 |
| `frontend.Mphone.responsive.css` | `≤768px` / `≤480px` 覆盖 | 移动端布局调整 |

---

## 2. 加载顺序（必须保持）

入口文件 `frontend.PC-Mphone.css` 的导入顺序：

```css
@import url("/static/css/frontend.PC.tokens.css");
@import url("/static/css/frontend.PC.layout.css");
@import url("/static/css/frontend.PC.theme.css");
@import url("/static/css/frontend.PC.components.css");
@import url("/static/css/frontend.PC.dashboard.css");
@import url("/static/css/frontend.PC.modal.css");
@import url("/static/css/frontend.Mphone.responsive.css");
```

顺序含义：

1. **tokens 先行**：后续所有文件可直接使用 `var(--*)` 变量
2. **layout/theme/components/dashboard/modal** 依次叠加业务层
3. **responsive 最后**：`@media` 覆盖规则放在末尾，避免被桌面规则反覆盖

**打乱顺序的常见后果：**

- 变量未定义 → 颜色/圆角/阴影回退为浏览器默认值
- 响应式规则被桌面规则覆盖 → 移动端布局异常
- 暗色主题 `html[data-theme="dark"]` 覆盖不完整

---

## 3. 各文件详细说明

### `frontend.PC-Mphone.css`（入口总线）

**定位**：只负责 `@import`，不放任何业务规则。

维护规范：

- 新增分层文件时，只在本文件追加导入，不要在 HTML 中额外添加 `<link>`
- 遵循导入顺序：变量 → 结构 → 主题 → 组件 → 业务 → 弹窗 → 响应式
- 线上有缓存策略时，修改后同步提升 query `?v=` 版本号

---

### `frontend.PC.tokens.css`（设计令牌 + 全局基线）

**定位**：全站基础变量与 reset，提供统一视觉字典。

#### 布局变量（`:root`）

| 变量 | 含义 |
|------|------|
| `--sidebar-width` | 侧栏默认宽度 |
| `--sidebar-inset` | 移动端侧栏与屏幕边缘的间距 |
| `--radius-sm/md/lg/xl` | 圆角阶梯 |

#### 颜色变量

| 变量组 | 含义 |
|--------|------|
| `--color-surface` | 页面底色 |
| `--color-text` / `--color-text-muted` | 正文 / 次要文字 |
| `--color-primary` / `--color-primary-hover` | 品牌主色 |
| `--color-border` | 通用边框色 |
| `--color-overlay` | 遮罩颜色 |

#### 阴影与玻璃参数

| 变量 | 含义 |
|------|------|
| `--shadow-card` | 卡片阴影 |
| `--shadow-modal` | 弹窗阴影 |
| `--glass-blur-md` | 玻璃模糊半径 |
| `--glass-saturate` | 玻璃饱和度增强 |
| `--glass-card` | 卡片玻璃背景色 |

#### 动效参数

| 变量 | 含义 |
|------|------|
| `--ease-spring` | 弹簧缓动曲线 |
| `--ease-out-expo` | 指数缓出曲线 |
| `--duration-fast/normal/slow` | 动画时长阶梯 |

#### 全局 reset

```css
* { margin: 0; padding: 0; box-sizing: border-box; }
```

`html/body` 设置基础背景色与 `min-height: 100dvh`（兼容移动端视口高度）。

减弱动画模式：`@media (prefers-reduced-motion: reduce)` 统一压缩动画与过渡时长。

**维护边界**：任何跨模块复用的颜色、圆角、阴影、动效先加在这里，组件内优先引用变量，不要硬编码。

---

### `frontend.PC.layout.css`（页面骨架与导航结构）

**定位**：PC 主结构、侧栏、顶栏、主内容区域、视图切换动画。

#### 核心结构类

**侧栏：**

| 类名 | 说明 |
|------|------|
| `.fd-pc-layout__sidebar` | 固定左侧主容器 |
| `.fd-pc-sidebar__logo` | 顶部品牌区 |
| `.fd-pc-sidebar__menu` | 菜单滚动区 |
| `.fd-pc-sidebar__item` | 菜单项 |
| `.fd-pc-sidebar__resize` | 右缘拖拽热区（宽度拖拽功能） |

**移动端导航辅助（基础态在此定义）：**

| 类名 | 说明 |
|------|------|
| `.fd-mphone-nav__overlay` | 侧栏遮罩 |
| `.fd-mphone-nav__hamburger` | 汉堡按钮（桌面端 `display:none`） |

**主区与头部：**

| 类名 | 说明 |
|------|------|
| `.fd-pc-layout__main` | 主内容外壳（含 `margin-left` 让出侧栏） |
| `.fd-header` | 顶部标题栏 |
| `.fd-header__row` | 标题行（标题 + 工具条） |
| `.fd-header__toolbar` | 右侧工具条 |
| `.fd-header__filters` | 筛选条件提示区 |
| `.fd-pc-layout__content` | 主内容内边距容器 |

**多视图切换：**

| 类名 | 说明 |
|------|------|
| `.fd-view` | 视图容器基础态（`display:none`） |
| `.fd-view.active` | 当前激活视图，进入动画 `fd-view-enter` |

#### JS 强依赖状态类

| 状态类 | 触发时机 |
|--------|---------|
| `.fd-pc-layout__sidebar.is-resizing` | 拖拽侧栏宽度时（关闭过渡动效） |
| `.fd-pc-layout__main.is-resizing` | 同上，主区同步 |
| `.fd-pc-sidebar__item.active` | 当前激活路由 |
| `.fd-pc-sidebar__item.fd-sidebar-item--pulse` | 重复点击当前菜单时的抖动动画 |
| `.fd-mphone-nav__overlay.show` | 移动端侧栏展开时遮罩可见 |
| `.fd-mphone-nav__hamburger.active` | 汉堡三线变 ×（侧栏展开态） |

**兼容兜底**：`@supports not (backdrop-filter: blur(1px))` 下提供纯色/阴影退化方案。

---

### `frontend.PC.theme.css`（主题切换与暗色覆盖）

**定位**：主题切换组件样式 + `html[data-theme="dark"]` 系统性覆盖。

#### 主题切换组件类

| 类名 | 说明 |
|------|------|
| `.fd-theme-toggle` | 开关按钮外壳 |
| `.fd-theme-toggle__track` | 底部轨道 |
| `.fd-theme-toggle__thumb` | 滑块 |
| `.fd-theme-toggle__icon--sun` | 太阳图标 |
| `.fd-theme-toggle__icon--moon` | 月亮图标 |
| `.fd-theme-toggle--dark` | 暗色态（滑块右移 + 图标切换） |

#### 暗色覆盖策略

1. 在 `html[data-theme="dark"]` 一次性重写全局 CSS 变量（`--color-*`、`--glass-*`）
2. 对视觉需要精修的容器补充精确覆盖：
   - 侧栏、顶栏、菜单 hover / active 态
   - 弹窗遮罩与面板
   - 表单 `<select>`、日历网格、提示区
   - 移动端汉堡按钮（避免深色线条贴白底）

**维护建议**：若新增组件完全使用 CSS 变量，一般可自动适配暗色；若有视觉差异，在本文件追加 `html[data-theme="dark"] .新类名 { ... }` 覆盖。

---

### `frontend.PC.components.css`（通用组件层）

**定位**：跨页面复用的通用组件，不放某个业务页专属布局。

#### 主要组件

**按钮体系：**

| 类名 | 说明 |
|------|------|
| `.fd-btn` | 基类（过渡、字体、光标） |
| `.fd-btn--primary` | 主按钮（实色背景 + 光晕效果） |
| `.fd-btn--outline` | 次要按钮（线框 / 浅底） |

**卡片：**

| 类名 | 说明 |
|------|------|
| `.fd-card` | 玻璃效果卡片容器 |

**文本与工具类：**

| 类名 | 说明 |
|------|------|
| `.fd-section-title` | 章节标题（下划线进入动画） |
| `.fd-date-hint` | 当前筛选条件提示文本 |
| `.fd-hidden` | 强制隐藏（JS 切换用） |

**兼容兜底**：`@supports not (backdrop-filter...)` 下组件退化为实色方案。

**维护边界**：新增"全局可复用"样式放这里；若只服务某个业务块，请放 `dashboard` 或 `modal`。

---

### `frontend.PC.dashboard.css`（统计、图表、表格业务层）

**定位**：数据展示区专属样式，仅在 dashboard 类视图内使用。

#### 指标卡网格

| 类名 | 说明 |
|------|------|
| `.fd-stats` | 四列网格容器 |
| `.fd-stats__card` | 单个指标卡 |
| `.fd-stats__card--blue/green/teal/purple` | 颜色修饰符 |
| `.fd-stats__label` | 指标标签文字 |
| `.fd-stats__value` | 指标数值（大字） |
| `.fd-stats__date-range` | 数据时间范围提示 |

#### 图表区

| 类名 | 说明 |
|------|------|
| `.fd-charts` | 双列图表网格 |
| `.fd-charts__container` | ECharts 容器（`width:100%`，`height:350px`） |
| `#pc-category-chart, #pc-category-chart2` | 饼图容器覆盖高度（`420px`，留足外侧标签空间） |
| `.fd-card__header` | 卡片标题行 |
| `.fd-card__body` | 卡片内容区（内边距容器） |

#### 表格区

| 类名 | 说明 |
|------|------|
| `.fd-table` | 横向滚动容器 |
| `.fd-table--body-cap` | 纵向限高 + sticky 表头（约 10 行高） |

全局 `table/th/td/tr` 外观与行 hover 反馈也在本文件定义。

**维护要点**：

- 新图表容器优先复用 `.fd-charts__container`
- 需要"固定表头 + 内容滚动"的表格沿用 `.fd-table--body-cap`

---

### `frontend.PC.modal.css`（日期筛选弹窗）

**定位**：日期筛选弹窗全套 UI（遮罩 → 面板 → 年月选择 → 日历网格 → 底部提示与按钮）。

#### 核心结构

| 类名 | 说明 |
|------|------|
| `.fd-modal-overlay` | 全屏遮罩（默认隐藏） |
| `.fd-modal-overlay.show` | 弹窗可见态 |
| `.fd-modal` | 弹窗面板 |
| `.fd-modal-overlay--no-transition` | JS 关闭时临时禁用过渡，避免卡顿 |
| `.fd-modal__header/body/footer` | 面板三区 |
| `.fd-modal__close` | 关闭按钮（hover 旋转反馈） |

#### 日期过滤模块

| 类名 | 说明 |
|------|------|
| `.fd-date-filter__section` | 块容器 |
| `.fd-filter__row--ym` | 年/月双列 flexbox 行 |
| `.fd-form-select` | 原生 `<select>` 统一皮肤 |
| `.fd-filter__day-grid` | 7 列日历网格 |
| `.fd-filter__day-btn` | 单个日期按钮 |
| `.fd-filter__tip-wrap` | 底部提示容器 |
| `.fd-filter__tip` | 提示文字 |

#### JS 强依赖状态类

| 状态类 | 说明 |
|--------|------|
| `.fd-filter__day-btn.is-disabled` | 该日无数据，不可选 |
| `.fd-filter__day-btn.is-enabled` | 该日有数据，可点击 |
| `.fd-filter__day-btn.is-selected` | 当前已选中日期 |
| `.fd-filter__day-grid:empty` | 无年月数据时隐藏空网格 |

**兼容兜底**：无 `backdrop-filter` 时遮罩与面板切为纯色 + 普通阴影。

---

### `frontend.Mphone.responsive.css`（窄屏覆盖层）

**定位**：`≤768px` 与 `≤480px` 的响应式覆盖，确保移动端可用性。

#### `@media (max-width: 768px)` 关键变更

| 规则 | 说明 |
|------|------|
| `.fd-pc-layout__main { margin-left: 0; width: 100% }` | 主区全宽（侧栏已 fixed 移出文档流） |
| `.fd-pc-layout__sidebar` transform | 默认移出屏幕左侧 |
| `.fd-pc-layout__sidebar.active` | 侧栏滑入（JS 添加 `.active`） |
| `.fd-mphone-nav__hamburger { display: flex }` | 显示汉堡按钮 |
| `.fd-header` 内边距 | 左侧预留汉堡按钮空间 |
| `.fd-header__row { flex-wrap: wrap }` | 标题独占一行，工具条换行靠右 |
| `.fd-stats { grid-template-columns: repeat(2, 1fr) }` | 指标卡改 2 列 |
| `.fd-charts { grid-template-columns: minmax(0,1fr) }` | 图表改单列 |
| `.fd-charts__container { height: 280px }` | 图表容器高度降低 |
| `#pc-category-chart, #pc-category-chart2 { height: 420px }` | 饼图保持较高（顶部图例占空间） |
| 表格字号 / 内边距 / 最大高度 | 适配小屏触摸操作 |

#### `@media (max-width: 480px)` 进一步收敛

| 规则 | 说明 |
|------|------|
| `.fd-stats { grid-template-columns: 1fr }` | 指标卡改单列 |
| `.fd-header__title { font-size: 16px }` | 标题字号再降 |
| `.fd-btn` 内边距 / 字号 | 按钮更紧凑 |

---

## 4. 命名规则与状态类约定

### BEM 命名

```
.fd-{block}__{element}--{modifier}
```

- **统一前缀**：`fd-`（Frontend Dashboard）
- **平台语义**：PC 结构用 `fd-pc-*`，移动端导航用 `fd-mphone-*`
- **修饰符**：颜色变体用 `--blue/green/teal/purple` 等语义名

### 状态类约定

| 类型 | 类名模式 | 示例 |
|------|----------|------|
| 通用显隐 | `.active` / `.show` / `.fd-hidden` | 视图激活、弹窗显示 |
| 交互状态 | `.is-*` | `.is-resizing` `.is-selected` `.is-disabled` |
| 主题状态 | `html[data-theme="dark"]` | 暗色模式全局覆盖 |
| 组件自身状态 | `--dark` 修饰符 | `.fd-theme-toggle--dark` |

**重要**：状态类只由 JS 切换，不要在 CSS 内通过其他选择器模拟状态逻辑。

---

## 5. 新增或修改样式的推荐流程

### 第一步：判断层级

```
变量改动  → tokens
结构改动  → layout
暗色精修  → theme
新通用组件 → components
业务展示  → dashboard
弹窗相关  → modal
移动端覆盖 → responsive
```

### 第二步：先变量后组件

新颜色 / 阴影 / 动画优先加到 `tokens` 的 `:root`，组件内消费变量，避免硬编码。

### 第三步：先桌面后移动

在桌面文件完成默认样式，再到 `responsive` 做覆盖。不要从移动端反向改桌面文件。

### 第四步：状态由 JS 切类

尤其是侧栏开关、弹窗显示、日期按钮选中态，不要用内联 style 覆盖。

### 第五步：同步暗色与兼容兜底

新增频繁使用的组件时至少补：

1. 暗色覆盖（`html[data-theme="dark"] .新类名 { ... }` 在 `theme.css`）
2. 无 blur 兜底（`@supports not (backdrop-filter...)` 在对应文件）

### 第六步：验证三个场景

- 桌面亮色
- 桌面暗色
- 窄屏 ≤768px 与 ≤480px

---

## 6. 常见改动风险点

| 改动点 | 风险 | 应对措施 |
|--------|------|---------|
| 修改 `--sidebar-width` | 主区宽度与侧栏拖拽逻辑不同步 | 同步检查 `layout.css` 中 `calc` 与 JS 中的 `pcApplyResizeWidth` |
| 改顶栏结构 | 窄屏标题被压成竖排断字 | 确认 `.fd-header__title { white-space: normal; flex: 1 1 100% }` 在 `responsive` 中生效 |
| 调整图表卡片尺寸 | ECharts 容器高度与重绘逻辑不一致 | 同步修改 `dashboard.css` 中容器高度，并检查移动端覆盖 |
| 修改日期弹窗 | `.is-enabled/.is-selected` 被意外覆盖 | 确保状态类样式优先级足够，不要用 `!important` 掩盖问题 |
| 新增玻璃效果 | 不支持 `backdrop-filter` 的浏览器样式崩 | 补充 `@supports not` 退化方案 |
| 调整 `@import` 顺序 | 全局样式层叠逻辑混乱 | 严格遵循第 2 节规定的顺序 |

---

## 7. 提交前检查清单

- [ ] 8 个文件职责仍清晰，无跨层乱放
- [ ] `frontend.PC-Mphone.css` 的 `@import` 顺序正确
- [ ] 新增颜色/圆角/阴影已提取为 CSS 变量，避免硬编码
- [ ] 暗色 `html[data-theme="dark"]` 已覆盖新增组件
- [ ] 无 `backdrop-filter` 的退化样式已补充
- [ ] `≤768px` 与 `≤480px` 均已测试
- [ ] JS 依赖的状态类（`active/show/is-*`）命名保持不变
- [ ] 本文档（README.md）已与实现保持同步
