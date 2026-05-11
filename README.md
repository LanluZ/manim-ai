# Manimai - AI 多Agent驱动的 Manim 动画生成器

<div align="center">

![](/assets/img/001.apng)

**多Agent协作系统**，通过 Planner → Coder → Reviewer → Renderer 自主生成3B1B风格的数学动画

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![Manim](https://img.shields.io/badge/Manim-0.18+-orange.svg)](https://www.manim.community/)
[![PySide6](https://img.shields.io/badge/PySide6-6.6+-green.svg)](https://doc.qt.io/qtforpython/)

</div>

## 快速开始

### 环境要求

- Python 3.10+
- LaTeX 发行版（用于数学公式渲染）
- FFmpeg（用于视频处理）

### 安装

```bash
git clone https://github.com/yourusername/manimai.git
cd manimai
pip install -r requirements.txt
```

### 运行

**GUI 模式（默认）：**
```bash
python main.py
```

**CLI 模式：**
```bash
python main.py --cli "创建一个旋转的立方体"
```

## 多Agent架构

```
用户输入
    │
    ▼
┌─────────────┐
│   Planner   │  分析需求，分解任务
└──────┬──────┘
       │ PLAN_CREATED
       ▼
┌─────────────┐
│    Coder    │  生成 Manim 代码
└──────┬──────┘
       │ CODE_GENERATED
       ▼
┌─────────────┐
│   Reviewer  │  审查代码质量
└──────┬──────┘
       │ CODE_APPROVED ──┐
       │                 │
       │ CODE_NEEDS_FIX  │ (循环修复)
       ▼                 │
┌─────────────┐           │
│    Coder    │◄──────────┘
└─────────────┘
       │ CODE_APPROVED
       ▼
┌─────────────┐
│   Renderer  │  渲染视频
└──────┬──────┘
       │ RENDER_COMPLETED
       ▼
    输出视频
```

## 项目结构

```
manimai/
├── src/
│   ├── core/                  # 核心框架
│   │   ├── events.py          # 事件定义
│   │   ├── message_bus.py     # 异步事件总线
│   │   ├── agent.py           # Agent 基类
│   │   ├── context.py         # 任务上下文
│   │   └── coordinator.py     # 中心协调器
│   ├── agents/                # Agent 实现
│   │   ├── planner.py         # 需求分析 Agent
│   │   ├── coder.py           # 代码生成 Agent
│   │   ├── reviewer.py        # 代码审查 Agent
│   │   └── renderer.py        # 渲染执行 Agent
│   ├── services/              # 服务层
│   │   ├── ai_clients.py      # AI 客户端（DeepSeek/Gemini）
│   │   ├── config.py          # 配置定义
│   │   ├── database.py        # 数据库操作
│   │   └── manim_runner.py    # Manim 渲染引擎
│   ├── gui/                   # GUI 界面
│   │   ├── main.py            # GUI 入口
│   │   ├── main_window.py     # 主窗口
│   │   └── workers.py         # 后台线程
│   └── cli/                   # CLI 界面
│       └── main.py            # CLI 入口
├── tests/                     # 单元测试
├── data/                      # 运行时数据
│   ├── jobs/                  # 工作区数据
│   └── manimai.db             # SQLite 数据库
├── assets/                    # 静态资源
├── main.py                    # 统一入口
└── requirements.txt           # 依赖清单
```

## 技术栈

| 组件 | 技术 |
|------|------|
| **GUI 框架** | PySide6 (Qt for Python) |
| **动画引擎** | Manim Community Edition |
| **AI 接口** | DeepSeek, Gemini (OpenAI SDK 兼容) |
| **异步框架** | asyncio |
| **数据存储** | SQLite |
| **事件驱动** | EventBus |

## Agent 说明

| Agent | 职责 | 输入事件 | 输出事件 |
|-------|------|----------|----------|
| **Planner** | 分析需求，分解为任务列表 | TASK_RECEIVED | PLAN_CREATED |
| **Coder** | 生成或修复 Manim 代码 | PLAN_CREATED, CODE_NEEDS_FIX | CODE_GENERATED |
| **Reviewer** | 静态检查 + AI 审查代码 | CODE_GENERATED | CODE_APPROVED, CODE_NEEDS_FIX |
| **Renderer** | 执行 Manim 渲染 | CODE_APPROVED | RENDER_COMPLETED, CODE_NEEDS_FIX |

## 配置

### AI 模型

在 GUI 设置或通过数据库配置：

```python
# DeepSeek
deepseek_api_key = "your-api-key"
deepseek_base_url = "https://api.deepseek.com"
deepseek_model = "deepseek-chat"

# Gemini
gemini_api_key = "your-api-key"
gemini_model = "gemini-1.5-flash"
```

### 输出参数

- **分辨率**: 320x240 ~ 3840x2160
- **帧率**: 1-120 FPS
- **质量**: `l` (低) / `m` (中) / `h` (高) / `k` (4K)

## 示例

```bash
# CLI 模式生成动画
python main.py --cli "创建一个3x3矩阵，展示它的转置过程"

# 指定输出参数
python main.py --cli --width 1280 --height 720 --fps 30 "旋转的球体"
```

## 评测与可靠性验证

项目内置数学动画 prompt 评测集，位于 `data/evaluation/math_animation_prompts.json`。当前包含 40 条 prompt，覆盖函数图像、几何、线性代数、概率统计、微积分、数论、离散数学等类型。

评测 runner 会输出 JSON 和 CSV 报告，统计以下指标：

- 首次渲染成功率
- 自动修复后最终成功率
- 平均修复轮数
- 平均端到端耗时
- 平均 API 成本估算
- Provider 调用序列与失败类型

本地可先使用 fake provider / fake render 验证评测链路，不消耗真实 API：

```bash
python -m src.evaluation.runner --fake-providers --fake-render --limit 2 --variant baseline --variant deepseek_timeout
```

真实评测需要配置真实 API key，并使用 Manim 实际渲染：

```bash
python -m src.evaluation.runner --limit 40 --deepseek-key <key> --gemini-key <key>
```

评测完成后，将真实跑批结果回填到下表。不要填写 fake provider 或未实际测量的数据。

| 实验变体 | Prompt 数 | 首次渲染成功率 | 自动修复后成功率 | 平均修复轮数 | 平均端到端耗时 | 平均 API 成本 |
|----------|-----------|----------------|------------------|--------------|----------------|---------------|
| baseline | 待测 | 待测 | 待测 | 待测 | 待测 | 待测 |
| no_reviewer | 待测 | 待测 | 待测 | 待测 | 待测 | 待测 |
| no_static_review | 待测 | 待测 | 待测 | 待测 | 待测 | 待测 |
| no_auto_fix | 待测 | 待测 | 待测 | 待测 | 待测 | 待测 |
| deepseek_timeout | 待测 | 待测 | 待测 | 待测 | 待测 | 待测 |
| gemini_error | 待测 | 待测 | 待测 | 待测 | 待测 | 待测 |

## 工程质量

CI 使用 GitHub Actions 执行 lint、type check 和 pytest。对应命令：

```bash
ruff check src tests
mypy src tests
pytest -q
```

## 许可证

MIT License

## 相关链接

- [Manim Community](https://www.manim.community/)
- [DeepSeek API](https://platform.deepseek.com/)
- [Google Gemini](https://ai.google.dev/)
