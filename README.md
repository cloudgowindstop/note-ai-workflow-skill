# note-ai-workflow-skill

> 基于 Claude Code + CCSwitch 的 PDF 学习助手。自然语言提问 → AI 定位页面 → 截图翻译 → 结构化笔记。

## 架构

```
用户提问（任意课程目录）
       │
       ▼
Claude Code ──激活 Skill──→ 获取 SOP 工作流程
       │
       ├──→ pdf_extract（MCP）──→ 提取 PDF 文本
       │                                    │
       ├──→ pdf_screenshot（MCP）──→ 截图   │ Claude Code
       │                                    │ 语义匹配 + 生成笔记
       ▼                                    │
  ./notes/{pdf名称}/study_notes.md ←────────┘
```

- **Skill**（SKILL.md）：定义工作流程和输出模板
- **MCP Server**（server.py）：提供 `pdf_extract` + `pdf_screenshot` 两个原子工具
- **CCSwitch**：统一管理 Skill 和 MCP 配置，跨课程自动复用

MCP Server **不调用任何 AI API**——翻译、讲解、笔记生成由 Claude Code 完成。

## 仓库结构

```
note-ai-workflow-skill/
├── skills/
│   └── pdf-note-assistant/
│       └── SKILL.md           ← Skill 定义（CCSwitch 规范）
├── mcp-server/
│   ├── server.py              ← MCP 主程序（2 个工具，零 AI 调用）
│   ├── pyproject.toml         ← Python 包配置
│   └── README.md              ← MCP 使用文档
└── README.md                  ← 本文件
```

## 快速开始

### 1. 安装系统依赖

```bash
# Windows: 下载 poppler-windows，将 Library/bin 加入 PATH
# macOS:   brew install poppler
# Ubuntu:  sudo apt install poppler-utils
```

### 2. CCSwitch 配置

#### 添加 Skill 仓库

| 字段 | 值 |
|------|-----|
| Owner | `cloudgowindstop` |
| Name | `note-ai-workflow-skill` |
| Branch | `main` |
| Subdirectory | `skills/` |

#### 添加 MCP Server

| 字段 | 值 |
|------|-----|
| 服务器 ID | `pdf-note-mcp` |
| 传输类型 | `stdio` |
| 命令 | `uvx` |
| 参数 | `--from git+https://github.com/cloudgowindstop/note-ai-workflow-skill.git#subdirectory=mcp-server pdf-note-mcp` |

绑定到 **Claude Code**，重启终端。

### 3. 使用

```bash
cd ~/courses/机器学习/
mv ~/Downloads/lecture1.pdf ./papers/
claude

# 自然语言提问即可
> 帮我分析 lecture1.pdf 里面讲的正则化方法
```

生成的笔记在 `./notes/lecture1/study_notes.md`。

## 输出示例

```markdown
# lecture1 学习笔记

> 问题：正则化方法有哪些
> 日期：2026-07-01

## 第 5 页 — Regularization

### 原文截图
![page_5](screenshots/page_5.png)

### 翻译
正则化（Regularization）是防止过拟合的核心技术...

### 讲解
可以这样理解：模型就像一个学生，如果不加约束...

### 重点提炼
- L1 正则化产生稀疏解，可用于特征选择
- L2 正则化（权重衰减）限制权重大小
- Dropout 是一种隐式正则化

### 关联问题
1. L1 和 L2 同时使用会产生什么效果？
2. 为什么 Dropout 可以看作集成学习？

### 补充知识
- 推荐阅读：《Deep Learning》第 7 章
```

## 技术栈

| 层 | 技术 |
|------|------|
| PDF 文本提取 | pdfplumber |
| PDF 页面渲染 | pdf2image + poppler |
| MCP 协议 | mcp (Python SDK) |
| 编排与生成 | Claude Code |
| 配置管理 | CCSwitch |

## 限制

- 扫描版 PDF（无文字层）需通过截图分析
- 嵌入图片中的公式 pdfplumber 无法提取为文本
- 超大 PDF（200+ 页）全量提取较慢

## 许可

MIT
