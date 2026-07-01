# PROJECT_CONTEXT — note-ai-workflow

> **一句话**：基于 Claude Code + CCSwitch 的 PDF 学习助手，实现「PDF 论文/课件 → AI 理解 → 截图翻译 → 结构化笔记」的自动化。
>
> **仓库**：[github.com/cloudgowindstop/note-ai-workflow-skill](https://github.com/cloudgowindstop/note-ai-workflow-skill)
>
> **状态**：📋 设计阶段，代码未创建

---

## 1. 项目描述

### 解决的问题

阅读英文论文/课件时，手动截图 + 翻译 + 整理笔记流程繁琐。本项目让用户用自然语言对 PDF 提问，AI 自动完成：定位相关页面 → 截图 → 翻译讲解 → 输出带图片的 Markdown 笔记。

### 核心设计原则

| 原则 | 说明 |
|------|------|
| **MCP 不做 AI 推理** | MCP Server 只负责数据获取（提取文本、截图），生成内容由 Claude Code 完成 |
| **Skill 定义流程** | Skill 是 SOP（标准作业流程），告诉 Claude Code "遇到 PDF 问题时怎么干活" |
| **CCSwitch 统一管理** | Skill 和 MCP 通过 CCSwitch 配置，跨项目、跨课程自动复用 |

### 架构概览

```
用户提问（任意课程目录）
       │
       ▼
Claude Code ──激活 Skill──→ 获取 SOP 流程
       │
       ├──→ pdf_extract（MCP）──→ 提取 PDF 文本
       │                                    │
       ├──→ pdf_screenshot（MCP）──→ 截图  │ Claude Code
       │                                    │ 语义理解 + 定位
       ▼                                    ▼
   生成笔记 ←── Claude Code 自己翻译/讲解/排版
       │
       ▼
  ./notes/{pdf名称}/study_notes.md
```

---

## 2. 技术栈

| 层 | 技术 | 用途 |
|------|------|------|
| **编排** | Claude Code | 理解问题、决策、生成内容 |
| **流程规范** | Skill（SKILL.md） | 定义触发条件、工作步骤、输出模板 |
| **数据获取** | MCP Server（Python） | pdf_extract + pdf_screenshot 两个工具 |
| **PDF 解析** | pdfplumber | 提取文本，自动处理双栏排版和表格 |
| **页面渲染** | pdf2image + poppler | 将 PDF 页面渲染为 PNG 截图 |
| **配置管理** | CCSwitch | 管理 Skill 仓库和 MCP Server 的安装/同步 |

### 依赖清单

```toml
# Python（mcp-server/pyproject.toml）
dependencies = [
    "mcp>=1.0.0",        # MCP 协议 SDK
    "pdfplumber>=0.10.0", # PDF 文本提取
    "pdf2image>=1.16.0",  # PDF → 图片
    "Pillow>=10.0.0",     # 图像处理（pdf2image 依赖）
]

# 系统依赖
# poppler（Windows：下载后加入 PATH）
```

---

## 3. 目录结构

```
note-ai-workflow-skill/          ← GitHub 仓库
│
├── skills/
│   └── pdf-note-assistant/      ← Skill：一个目录一个技能
│       └── SKILL.md             ← 核心文件（name + description + 工作流）
│
├── mcp-server/                  ← MCP Server：独立子目录
│   ├── server.py                ← 主程序（~60 行，2 个工具）
│   ├── pyproject.toml           ← 包配置入口
│   └── README.md
│
├── docs/
│   └── PROJECT_CONTEXT.md       ← 本文件
│
└── README.md                    ← 项目总览（TODO）
```

### 本地运行时目录结构（课程项目）

```
任意课程目录/                     ← 如 ~/courses/ml-basics/
├── papers/                      ← 放 PDF 文件
│   └── lecture1.pdf
└── notes/                       ← 自动生成的笔记
    └── lecture1/
        ├── screenshots/
        │   ├── page_3.png
        │   └── page_5.png
        └── study_notes.md
```

---

## 4. 当前状态

### 已完成

- [x] 架构设计文档（[pdf-note-ai-workflow.md](../pdf-note-ai-workflow.md)）
- [x] 技术选型确认
- [x] 架构简化（去除 MCP 内嵌 AI 调用）

### 待完成

- [ ] 创建 GitHub 仓库并推送
- [ ] 编写 [skills/pdf-note-assistant/SKILL.md](../skills/pdf-note-assistant/SKILL.md)
- [ ] 编写 [mcp-server/server.py](../mcp-server/server.py)
- [ ] 编写 [mcp-server/pyproject.toml](../mcp-server/pyproject.toml)
- [ ] 安装 poppler（Windows 系统依赖）
- [ ] 在 CCSwitch 中配置 Skill 仓库 + MCP Server
- [ ] 用真实 PDF 端到端测试

### 关键简化决策（与原设计文档的区别）

| 决策 | 原方案 | 采用方案 | 理由 |
|------|--------|---------|------|
| MCP 工具数 | 4 个（含 generate_note, full_workflow） | 2 个（pdf_extract, pdf_screenshot） | Claude Code 自己做生成，避免双重 AI 调用 |
| MCP 内嵌 API | 调用 Claude API | 不调任何 AI | 省钱、减延迟、少一个 API Key |
| Skill 文件名 | prompt.md | SKILL.md | 对齐 CCSwitch 规范 |
| Skill 元数据 | 无 | YAML front matter | CCSwitch 解析需要 name + description |
| 搜索方式 | Python 关键词匹配 | Claude Code 语义理解 | AI 理解比关键词准确 |

---

## 5. MCP 工具定义

### pdf_extract

| 项 | 内容 |
|------|------|
| **输入** | `pdf_path`：PDF 文件路径 |
| **输出** | 所有页的文本内容（页码 → 文字） |
| **实现** | `pdfplumber.open().pages[i].extract_text()` |

### pdf_screenshot

| 项 | 内容 |
|------|------|
| **输入** | `pdf_path`、`page_num`、`output_dir`（可选，默认 `./screenshots`） |
| **输出** | 截图保存路径 + PNG 图片数据 |
| **实现** | `pdf2image.convert_from_path(first_page, last_page, dpi=200)` |

---

## 6. CCSwitch 配置方式

### Skill 仓库

| 字段 | 值 |
|------|-----|
| Owner | `cloudgowindstop` |
| Name | `note-ai-workflow-skill` |
| Branch | `main` |
| Subdirectory | `skills/` |

### MCP Server

| 字段 | 值 |
|------|-----|
| 服务器 ID | `pdf-note-mcp` |
| 传输类型 | `stdio` |
| 命令 | `uvx` |
| 参数 | `--from git+https://github.com/cloudgowindstop/note-ai-workflow-skill.git#subdirectory=mcp-server pdf-note-mcp` |
| 绑定应用 | Claude Code ✓ |

---

## 7. 运行方式

```bash
# 前置：已安装 CCSwitch 并完成上述配置

cd ~/courses/ml-basics/          # 任意课程目录
mv ~/Downloads/lecture1.pdf ./papers/

claude                           # 启动 Claude Code

# 自然语言提问，Skill 自动激活
> 这篇 lecture1.pdf 里讲的正则化方法有哪些？帮我整理笔记
```

### 输出示例

```markdown
# lecture1 学习笔记

> 问题: 正则化方法有哪些
> 日期: 2026-07-01

## 第 5 页 — Regularization Techniques

![page_5](screenshots/page_5.png)

### 翻译
...（中文翻译，保留 L1/L2/dropout 等术语英文）...

### 讲解
...（通俗解释 + 公式符号说明）...

### 重点提炼
- L1 产生稀疏权重，L2 产生小权重
- Dropout 是一种隐式集成方法
- 早停（Early Stopping）是另一种隐式正则化
```

---

## 8. 已知问题 & 限制

| 问题 | 影响 | 计划 |
|------|------|------|
| **poppler 需手动安装** | Windows 上不是 pip install 能解决的 | README 写清楚安装步骤 |
| **扫描版 PDF 不支持** | 图片型 PDF 无文字层，pdfplumber 提取为空 | 后续接入 OCR（paddleocr） |
| **大 PDF 性能** | 200 页以上的 PDF，全量提取文本可能较慢 | 按需提取（先搜后读）作为优化项 |
| **截图消耗 token** | 每张图片约 1-5k token（取决于分辨率） | dpi 默认 150，可配置 |
| **单 PDF 处理** | 无法交叉引用多篇论文 | 长期考虑知识库方案 |
| **嵌入图片中的公式** | pdfplumber 提不到图片型公式 | 截图可看到，Claude Code 可从截图中识别 |

---

> **下一步**：按待完成清单逐项实施。优先创建 `SKILL.md` 和 `server.py`，推送到 GitHub，完成 CCSwitch 配置后做端到端测试。
