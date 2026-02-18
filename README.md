# Manimai - LLM 驱动的 Manim 动画生成器

<div align="center">

![](/docx/img/001.apng)

一个简单的程序 允许使用 LLM 轻松创建3B1B风格的动画

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![Manim](https://img.shields.io/badge/Manim-0.18+-orange.svg)](https://www.manim.community/)
[![PySide6](https://img.shields.io/badge/PySide6-6.6+-green.svg)](https://doc.qt.io/qtforpython/)

</div>

## 快速开始

### 环境要求

- Python 3.10+
- LaTeX 发行版（用于数学公式渲染）
- FFmpeg（用于视频处理）

### 安装步骤

1. **克隆仓库**
   ```bash
   git clone https://github.com/yourusername/manimai.git
   cd manimai
   ```

2. **安装依赖**
   ```bash
   pip install -r requirements.txt
   ```

3. **配置 AI API**
   
   在应用设置中配置你的 AI API 密钥：
   - **DeepSeek**: 需要 API Key 和 Base URL
   - **Gemini**: 需要 API Key

4. **运行应用**
   ```bash
   python main.py
   ```

## 使用指南

### 基本工作流程

1. **创建工作区** - 在"工作区"菜单中创建新的工作区
2. **输入描述** - 在文本框中描述你想要的动画效果
3. **生成动画** - 点击"生成并播放"按钮
4. **查看结果** - 动画将自动渲染并播放
5. **继续添加** - 在现有动画基础上继续添加新的场景

### 示例提示词

```
创建一个3x3矩阵，然后展示它的转置
```

## 配置说明

### 输出参数

- **分辨率**: 320x240 到 3840x2160
- **帧率**: 1-120 FPS
- **质量**: l (低) / m (中) / h (高) / k (4K)

### AI 模型配置

#### DeepSeek
- **API Key**: 从 [DeepSeek 官网](https://platform.deepseek.com/) 获取
- **API 地址**: 默认为 `https://api.deepseek.com`
- **模型名称**: 默认为 `deepseek-chat`

#### Gemini
- **API Key**: 从 [Google AI Studio](https://makersuite.google.com/) 获取
- **模型名称**: 默认为 `gemini-1.5-flash`

## 项目结构

```
manimai/
├── app/
│   ├── __init__.py
│   ├── ai_clients.py      # AI 客户端接口
│   ├── config.py          # 配置定义
│   ├── database.py        # 数据库操作
│   ├── manim_runner.py    # Manim 渲染引擎
│   ├── ui_main.py         # Qt GUI 界面
│   └── workers.py         # 后台任务线程
├── data/
│   ├── jobs/              # 工作区数据（自动生成）
│   └── manimai.db         # 数据库文件（自动生成）
├── main.py                # 应用入口
├── requirements.txt       # 依赖清单
├── .gitignore
└── README.md
```

## 技术栈

- **GUI 框架**: PySide6 (Qt for Python)
- **动画引擎**: Manim Community Edition
- **AI 接口**: OpenAI SDK, Requests, HTTPX
- **数据存储**: SQLite
- **并发处理**: QThread

## 界面预览

- **夜间主题** - 现代化深色界面，参考 IntelliJ IDEA 设计
- **三栏布局** - 输入区、播放器、设置/历史侧边栏
- **分段历史** - 可视化展示每个动画分段

## 贡献

欢迎提交 Issue 和 Pull Request！

## 许可证

MIT License

## 相关链接

- [Manim Community](https://www.manim.community/)
- [PySide6 文档](https://doc.qt.io/qtforpython/)
- [DeepSeek API](https://platform.deepseek.com/)
- [Google Gemini](https://ai.google.dev/)

---
