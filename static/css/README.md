# Frontend CSS 维护说明（8 文件详版）

本目录采用「单入口 + 模块拆分 + BEM + 状态类」方式维护。  
当前实际文件数为 **8 个 CSS 文件**，由 `frontend.PC-Mphone.css` 统一串联导入。

---

## 一、样式加载顺序（必须保持）

入口文件：`frontend.PC-Mphone.css`

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

1. **tokens 先定义变量与 reset**（后续文件可直接 `var(--*)`）。
2. **layout/theme/components/dashboard/modal** 依次叠加。
3. **responsive 最后覆盖**（`@media (max-width: 768px / 480px)` 在末尾更稳）。

如果改乱顺序，常见后果：

- 变量未定义导致颜色/圆角回退异常。
- 响应式规则被桌面规则反覆盖。
- 暗色主题覆盖不完整（`html[data-theme="dark"]` 失效感）。

---

## 二、8 个文件逐项说明（按职责）

## `frontend.PC-Mphone.css`（入口总线）

定位：**只负责 import，不放业务规则**。  
维护建议：

- 新增分表时只在本文件登记，避免在 HTML 中追加多个 `<link>`。
- 导入顺序优先遵循：变量 -> 结构 -> 主题 -> 组件 -> 业务 -> 弹窗 -> 响应式。
- 若线上有缓存策略，改入口后注意版本号（如 query `?v=`）同步。

---

## `frontend.PC.tokens.css`（设计令牌 + 全局基线）

定位：全站基础变量与 reset，提供统一视觉“字典”。

主要内容：

- `:root` 中定义布局变量：
  - `--sidebar-width`、`--sidebar-inset`
  - `--radius-sm/md/lg/xl`
- 颜色变量：
  - `--color-surface`、`--color-text-*`
  - `--color-primary` / `--color-primary-hover`
  - `--color-overlay`（遮罩）
- 阴影与玻璃参数：
  - `--shadow-ink`、`--shadow-card`、`--shadow-modal`
  - `--glass-blur-md`、`--glass-saturate`、`--glass-card`
- 动效参数：
  - `--ease-spring`、`--ease-out-expo`
  - `--duration-fast/normal/slow`
- 全局 reset：
  - `* { margin: 0; padding: 0; box-sizing: border-box; }`
- `html/body` 基础背景与移动端高度：
  - `min-height: 100vh` + `min-height: 100dvh`
- 减弱动画模式：
  - `@media (prefers-reduced-motion: reduce)` 统一压缩动画/过渡时长。

维护边界：

- **任何跨模块复用的颜色、圆角、阴影、动效**先加在这里。
- 业务组件里不要硬编码重复值，优先引用变量。

---

## `frontend.PC.layout.css`（页面骨架与导航结构）

定位：PC 主结构、侧栏、顶栏、主内容区域、视图切换动画。

核心结构类：

- 侧栏：
  - `.fd-pc-layout__sidebar` 固定左侧主容器
  - `.fd-pc-sidebar__logo` 顶部品牌区
  - `.fd-pc-sidebar__menu` 菜单滚动区
  - `.fd-pc-sidebar__item` 菜单项
  - `.fd-pc-sidebar__resize` 右缘拖拽热区
- 窄屏导航辅助（在本文件定义基础态）：
  - `.fd-mphone-nav__overlay` 遮罩
  - `.fd-mphone-nav__hamburger` 汉堡按钮
- 主区与头部：
  - `.fd-pc-layout__main` 主内容外壳
  - `.fd-header` 顶栏
  - `.fd-header__row` 标题行
  - `.fd-header__toolbar` 工具条
  - `.fd-header__filters` 筛选提示区
  - `.fd-pc-layout__content` 主内容内边距
- 多视图切换：
  - `.fd-view` + `.fd-view.active`（进入动画 `fd-view-enter`）

状态与交互耦合点（JS 依赖）：

- `.fd-pc-layout__sidebar.is-resizing`：拖拽时关闭过渡。
- `.fd-pc-layout__main.is-resizing`：主区同步关闭过渡。
- `.fd-pc-sidebar__item.active`：当前路由菜单。
- `.fd-pc-sidebar__item.fd-sidebar-item--pulse`：重复点击动画。
- `.fd-mphone-nav__overlay.show`：移动遮罩显示。
- `.fd-mphone-nav__hamburger.active`：三线转 X。

兼容兜底：

- `@supports not (backdrop-filter...)` 提供无模糊浏览器的纯色/阴影退化。

---

## `frontend.PC.theme.css`（主题切换与暗色覆盖）

定位：

1. 主题开关组件 `.fd-theme-toggle`；
2. 暗色主题 `html[data-theme="dark"]` 的系统性覆盖。

主题开关相关：

- `.fd-theme-toggle`：按钮外壳
- `.fd-theme-toggle__track`：底轨
- `.fd-theme-toggle__thumb`：滑块
- `.fd-theme-toggle__icon--sun` / `--moon`：图标
- `.fd-theme-toggle--dark`：按钮自身暗色状态（滑块右移 + 图标明暗切换）

暗色覆盖策略：

- 在 `html[data-theme="dark"]` 一次性改写全局变量（`--color-*`、`--glass-*`、`--glow-*`）。
- 再对关键容器做精修：
  - 侧栏、顶栏、菜单 hover/active
  - 弹窗遮罩与面板
  - 表单 select、日历网格、提示区
  - 移动端汉堡按钮（暗色下避免浅线贴白底）

维护建议：

- 若新增组件只使用变量，一般可自动适配暗色。
- 若视觉需要微调，再在本文件补 `html[data-theme="dark"] .新类名 { ... }`。

---

## `frontend.PC.components.css`（通用组件层）

定位：跨页面复用组件，不放某个业务页专属布局。

主要组件：

- 按钮体系：
  - `.fd-btn` 基类（过渡、排版）
  - `.fd-btn--primary` 主按钮（实色 + 光晕）
  - `.fd-btn--outline` 次按钮（线框/浅底）
- 卡片：
  - `.fd-card` 玻璃卡片容器
- 文本与工具：
  - `.fd-section-title` 章节标题下划线动画
  - `.fd-date-hint` 筛选提示文本
  - `.fd-hidden` 强制隐藏（JS 切换）

兼容兜底：

- `@supports not (backdrop-filter...)` 下组件退化为实色方案。

维护边界：

- 新增“全局可复用”的按钮/卡片/标题样式放这里。
- 若只服务某个业务块，请放 `dashboard` 或 `modal`。

---

## `frontend.PC.dashboard.css`（统计、图表、表格业务层）

定位：数据展示区专属样式。

主要区域：

- 指标卡网格：
  - `.fd-stats` 网格容器
  - `.fd-stats__card` 指标卡
  - 修饰符：`--blue` / `--green` / `--teal` / `--purple`
  - 文案：`.fd-stats__label`、`.fd-stats__value`、`.fd-stats__date-range`
- 图表区：
  - `.fd-charts`（桌面双列）
  - `.fd-charts__container`（ECharts 容器高度）
  - `.fd-card__header` / `.fd-card__body`（卡片内部结构）
- 表格区：
  - `.fd-table`（横向滚动容器）
  - `.fd-table--body-cap`（纵向限高 + sticky 表头）
  - 全局 `table/th/td/tr` 外观与 hover 行反馈

维护要点：

- 新图表容器优先复用 `.fd-charts__container` 高度约束。
- 详情表若需要“固定表头 + 内容滚动”，沿用 `.fd-table--body-cap`。

---

## `frontend.PC.modal.css`（日期筛选弹窗）

定位：日期筛选弹窗全套 UI（遮罩、面板、年月、日历、提示、按钮区）。

核心结构：

- 弹窗可见性：
  - `.fd-modal-overlay`（默认隐藏）
  - `.fd-modal-overlay.show`（显示）
  - `.fd-modal`（面板）
- 动效控制：
  - `.fd-modal-overlay--no-transition`（JS 关闭时避免卡顿）
- 面板分区：
  - `.fd-modal__header` / `__body` / `__footer`
  - `.fd-modal__close`（关闭按钮旋转反馈）
- 日期过滤模块：
  - `.fd-date-filter__section`（块容器）
  - `.fd-filter__row--ym`（年/月双列）
  - `.fd-form-select`（原生下拉统一皮肤）
  - `.fd-filter__day-grid`（7 列日历网格）
  - `.fd-filter__day-btn`（日期按钮）
  - `.fd-filter__tip-wrap` / `.fd-filter__tip`（底部提示）

状态类（JS 强依赖）：

- `.fd-filter__day-btn.is-disabled`：不可选占位
- `.fd-filter__day-btn.is-enabled`：可选日期
- `.fd-filter__day-btn.is-selected`：当前选中日期
- `.fd-filter__day-grid:empty`：无年月数据时隐藏空网格

兼容兜底：

- 无 `backdrop-filter` 时遮罩与弹窗切为纯色+普通阴影。

---

## `frontend.Mphone.responsive.css`（窄屏覆盖层）

定位：`<=768px` 与 `<=480px` 的覆盖规则，确保移动端可用性。

`@media (max-width: 768px)` 关键行为：

- 主区全宽化：
  - `.fd-pc-layout__main { margin-left: 0; width: 100%; }`
- 侧栏改抽屉：
  - `.fd-pc-layout__sidebar` 默认移出屏幕
  - `.fd-pc-layout__sidebar.active` 滑入
- 汉堡按钮启用：
  - `.fd-mphone-nav__hamburger { display: flex; }`
- 顶栏重排：
  - 标题独占一行，工具栏换行并靠右
- 内容区与业务区压缩：
  - `.fd-pc-layout__content` 收紧内边距
  - `.fd-stats` 改 2 列
  - `.fd-charts` 改单列
  - `.fd-charts__container` 高度降到 `280px`
  - 表格字号、内边距、滚动高度同步调整

`@media (max-width: 480px)` 进一步收敛：

- `.fd-stats` 改单列
- 标题字号再降
- `.fd-btn` 内边距与字号减小

---

## 三、命名规则与状态管理（当前实现）

前缀与结构：

- 统一前缀：`fd-`
- BEM：`block__element--modifier`
- 平台语义：
  - PC 结构常见 `fd-pc-*`
  - 移动导航常见 `fd-mphone-*`

状态类约定（不要和结构类混写）：

- 通用状态：`.active` / `.show` / `.fd-hidden`
- 交互状态：`.is-resizing` / `.is-disabled` / `.is-enabled` / `.is-selected`
- 主题状态：`html[data-theme="dark"]`、`.fd-theme-toggle--dark`

---

## 四、新增或修改样式的推荐流程（实操版）

1. **先判断层级**  
   令牌改动进 `tokens`；结构进 `layout`；通用控件进 `components`；业务展示进 `dashboard`；筛选弹窗进 `modal`；窄屏覆盖进 `responsive`；暗色补丁进 `theme`。

2. **先变量后组件**  
   新颜色/阴影/动画优先进 `:root`，组件只消费变量。

3. **先桌面后移动**  
   在桌面文件完成默认样式，再到 `frontend.Mphone.responsive.css` 做覆盖，不要反向写。

4. **状态由 JS 切类，不写内联样式**  
   尤其是侧栏开关、弹窗显示、日期按钮选中态。

5. **同步暗色与兼容兜底**  
   新增高频组件时，至少补：
   - 暗色覆盖（`html[data-theme="dark"]`）
   - 无 blur 兜底（`@supports not (backdrop-filter...)`）

6. **验证 3 个场景**  
   桌面亮色、桌面暗色、窄屏（<=768 和 <=480）。

---

## 五、常见改动的风险点

- 改 `--sidebar-width` 后，确认主区宽度与拖拽逻辑同步（`layout` + JS）。
- 改顶栏结构时，确认窄屏标题不会被压成“竖排断字”。
- 调整图表卡片尺寸时，确认 ECharts 容器高度和重绘逻辑一致。
- 调整日期筛选时，确认 `.is-enabled/.is-selected` 仍由 JS 正确切换。
- 引入新玻璃效果时，确认 `@supports not` 下仍可读可点。

---

## 六、重构检查清单（提交前）

- 8 个文件职责是否仍清晰，无跨层乱放。
- 入口 `frontend.PC-Mphone.css` 的 import 顺序是否正确。
- 是否复用变量，避免重复硬编码色值/阴影。
- 暗色 `html[data-theme="dark"]` 是否补齐新增组件。
- 无 blur 浏览器的退化样式是否可用。
- `<=768px` 与 `<=480px` 是否都测试通过。
- JS 依赖状态类（`active/show/is-*`）是否保持不变。
- 文档与实现是否一致（本 README 是否同步更新）。
