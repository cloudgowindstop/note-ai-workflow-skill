# PDF AI 笔记工作流项目

> **项目定位**：基于 Claude Code + CCSwitch 的 AI 辅助学习工具链，实现 PDF 论文/课件 -> 智能定位 -> 截图翻译 -> 结构化笔记 的自动化工作流。

---

## 一、项目背景与需求

### 1.1 用户痛点
- 阅读英文论文/课件时，需要反复切换翻译工具、截图、手动整理笔记
- 笔记格式不统一，回顾时难以快速定位原文
- 缺乏系统化的知识沉淀流程

### 1.2 核心需求
| 步骤 | 需求 | 技术方案 |
|------|------|---------|
| 输入 | 支持 PDF 论文/课件 | `pdfplumber` + `pdf2image` |
| 定位 | 根据提问找到相关内容 | 关键词搜索 + 语义匹配 |
| 截图 | 精准截取对应页面区域 | `pdf2image` + `Pillow` |
| 翻译 | 英文学术内容 -> 中文 | Claude API |
| 讲解 | 通俗解释 + 背景补充 | Claude API |
| 输出 | 结构化 Markdown 笔记 | 模板引擎 + 文件写入 |

---

## 二、技术架构

### 2.1 整体架构图

```
+-------------------------------------------------------------+
|                      用户（你）                              |
|         "帮我分析这篇论文的注意力机制"                      |
+---------------------+---------------------------------------+
                      |
                      v
+-------------------------------------------------------------+
|                 Claude Code（Agent 编排器）                   |
|  - 理解用户意图 -> 激活 Skill -> 按 SOP 执行步骤               |
|  - 调用 MCP 工具 -> 获取数据 -> 生成内容 -> 写入文件          |
+--------------+----------------------------------------------+
               |
    +----------+----------+
    |                     |
    v                     v
+------------+    +----------------------+
|   Skill    |    |    MCP Server        |
| (SOP/规范) |<-->|  (Tools/工具)        |
|            |    |                      |
| - 触发条件 |    | - pdf_search         |
| - 工作步骤 |    | - pdf_screenshot     |
| - 输出模板 |    | - generate_note      |
| - 质量检查 |    |                      |
+------------+    +----------------------+
                          |
                          v
                   +--------------+
                   |  外部依赖     |
                   | - pdfplumber |
                   | - pdf2image  |
                   | - anthropic  |
                   | - Pillow     |
                   +--------------+
```

### 2.2 核心组件说明

| 组件 | 角色 | 类比 |
|------|------|------|
| **Claude Code** | 总指挥 | 项目经理，理解需求、分配任务、检查结果 |
| **Skill** | 工作手册 | SOP 标准作业程序，定义怎么做 |
| **MCP Server** | 工具箱 | 提供具体执行能力的工具集合 |
| **CCSwitch** | 配置中心 | 统一管理 Skill 和 MCP 的跨应用同步 |

---

## 三、项目结构（GitHub 仓库）

### 3.1 仓库组织

```
pdf-note-ai-workflow/          <- 主仓库（或拆分为两个仓库）
|-- skills/
|   |-- pdf-note-assistant/    <- Skill：AI 的 SOP
|       |-- README.md
|       |-- prompt.md            <- 核心：工作流程定义
|
|-- mcp-server/
|   |-- server.py                <- MCP Server 主程序
|   |-- tools/
|   |   |-- __init__.py
|   |   |-- pdf_search.py       <- PDF 内容搜索
|   |   |-- screenshot.py         <- 页面截图
|   |   |-- note_generator.py   <- 笔记生成
|   |-- pyproject.toml           <- 依赖与入口配置
|   |-- README.md
|
|-- examples/                    <- 示例输出
|   |-- sample_notes.md
|
|-- .github/
|   |-- workflows/
|       |-- release.yml          <- CI/CD 自动发布
|
|-- README.md                    <- 项目总览
```

### 3.2 Skill 文件（prompt.md）

```markdown
# PDF 学习笔记助手

## 触发条件
当用户提到以下关键词时激活：PDF、论文、课件、笔记、翻译、讲解、截图

## 工作步骤
1. **理解问题**：分析用户的具体问题，提取核心概念和关键词
2. **定位内容**：调用 `pdf_search` 工具，在 PDF 中找到最相关的页面（默认 top 3）
3. **截取证据**：调用 `pdf_screenshot` 工具获取页面截图，确保包含足够上下文
4. **翻译讲解**：基于原文内容，调用 `generate_note` 生成中文翻译和通俗讲解
5. **生成笔记**：按照下方模板写入 Markdown 文件到 `./notes/{pdf_name}/` 目录

## 输出模板
```markdown
## 第 {页码} 页 - {章节标题}

### 原文截图
![page_{页码}](screenshots/page_{页码}.png)

### 翻译
{中文翻译，保留专业术语英文原文}

### 讲解
{通俗解释 + 背景知识补充}
{公式：解释每个符号含义}
{图表：描述图表传达的信息}

### 重点提炼
- {要点1}
- {要点2}
- {要点3}

### 关联问题
{延伸思考1}
{延伸思考2}

### 补充知识
{扩展概念或推荐阅读}
```

## 质量检查清单
- [ ] 截图是否包含问题相关的完整上下文？
- [ ] 翻译是否准确，专业术语是否保留英文？
- [ ] 讲解是否让非专业人士也能理解？
- [ ] 公式是否用 LaTeX 格式？
- [ ] 笔记是否保存到正确的目录？
```

### 3.3 MCP Server 核心代码（server.py）

```python
#!/usr/bin/env python3
"""PDF Note MCP Server - 提供 PDF 搜索、截图、笔记生成工具"""

import asyncio
import os
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent, ImageContent

import pdfplumber
from pdf2image import convert_from_path
import anthropic

app = Server("pdf-note-server")

class PDFNoteEngine:
    def __init__(self):
        self.pdf_cache = {}
        self.claude_client = anthropic.Anthropic(
            api_key=os.getenv("ANTHROPIC_API_KEY")
        )
    
    def load_pdf(self, pdf_path: str) -> dict:
        """加载 PDF 并建立文本索引"""
        if pdf_path in self.pdf_cache:
            return self.pdf_cache[pdf_path]
        
        index = {}
        with pdfplumber.open(pdf_path) as pdf:
            for i, page in enumerate(pdf.pages, 1):
                text = page.extract_text() or ""
                index[i] = {
                    'text': text,
                    'words': set(text.lower().split()),
                    'page': page
                }
        
        self.pdf_cache[pdf_path] = {
            'pages': len(pdf.pages),
            'index': index,
            'path': pdf_path
        }
        return self.pdf_cache[pdf_path]
    
    def search_pages(self, pdf_path: str, query: str, top_k: int = 3) -> list:
        """根据关键词搜索最相关的页面"""
        doc = self.load_pdf(pdf_path)
        query_words = set(query.lower().split())
        
        scores = {}
        for page_num, data in doc['index'].items():
            if not data['text']:
                continue
            score = len(query_words & data['words'])
            if score > 0:
                scores[page_num] = score
        
        sorted_pages = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return [p[0] for p in sorted_pages[:top_k]]
    
    def screenshot_page(self, pdf_path: str, page_num: int, 
                        output_dir: str = "./screenshots") -> str:
        """截取指定页面为图片"""
        os.makedirs(output_dir, exist_ok=True)
        
        images = convert_from_path(
            pdf_path, 
            first_page=page_num, 
            last_page=page_num,
            dpi=200
        )
        
        if not images:
            return None
        
        path = os.path.join(output_dir, f"page_{page_num}.png")
        images[0].save(path, "PNG")
        return path
    
    def generate_note(self, page_text: str, page_num: int, query: str) -> str:
        """调用 Claude API 生成翻译讲解笔记"""
        
        prompt = f"""用户正在学习一篇学术论文/课件，提出了以下问题：
"{query}"

以下是 PDF 第 {page_num} 页的内容：
---
{page_text[:3000]}
---

请按照以下格式生成学习笔记：

### 翻译
[将核心学术内容翻译成流畅的中文，保留专业术语的英文原文]

### 讲解
[用通俗易懂的方式解释这个概念]
[如果是公式，解释每个符号的含义]
[如果是图表，描述图表传达的信息]

### 重点提炼
- [要点1]
- [要点2]
- [要点3]

### 关联问题
[提出2-3个可以延伸思考的问题]

### 补充知识
[相关的扩展概念或推荐阅读]
"""
        
        response = self.claude_client.messages.create(
            model="claude-sonnet-4-5-20251001",
            max_tokens=4000,
            messages=[{"role": "user", "content": prompt}]
        )
        
        return response.content[0].text

engine = PDFNoteEngine()

@app.list_tools()
async def list_tools():
    return [
        Tool(
            name="pdf_search",
            description="在PDF中搜索与问题相关的页面",
            inputSchema={
                "type": "object",
                'properties': {
                    "pdf_path": {"type": "string"},
                    "query": {"type": "string"},
                    "top_k": {"type": "integer", "default": 3}
                },
                "required": ["pdf_path", "query"]
            }
        ),
        Tool(
            name="pdf_screenshot",
            description="截取PDF指定页面的截图",
            inputSchema={
                "type": "object",
                'properties': {
                    "pdf_path": {"type": "string"},
                    "page_num": {"type": "integer"},
                    "output_dir": {"type": "string", "default": "./screenshots"}
                },
                "required": ["pdf_path", "page_num"]
            }
        ),
        Tool(
            name="generate_note",
            description="根据PDF页面内容生成翻译讲解笔记",
            inputSchema={
                "type": "object",
                'properties': {
                    "pdf_path": {"type": "string"},
                    "page_num": {"type": "integer"},
                    "query": {"type": "string"}
                },
                "required": ["pdf_path", "page_num", "query"]
            }
        ),
        Tool(
            name="full_workflow",
            description="完整工作流：搜索-截图-翻译讲解-生成Markdown",
            inputSchema={
                "type": "object",
                'properties': {
                    "pdf_path": {"type": "string"},
                    "query": {"type": "string"},
                    "output_dir": {"type": "string", "default": "./notes"}
                },
                "required": ["pdf_path", "query"]
            }
        )
    ]

@app.call_tool()
async def call_tool(name: str, arguments: dict):
    if name == "pdf_search":
        pages = engine.search_pages(arguments['pdf_path'], arguments['query'], 
                                     arguments.get('top_k', 3))
        doc = engine.load_pdf(arguments['pdf_path'])
        previews = [f"第{p}页: {doc['index'][p]['text'][:500]}..." for p in pages]
        return [TextContent(text=f"找到 {len(pages)} 个相关页面:\n\n" + "\n\n".join(previews))]
    
    elif name == "pdf_screenshot":
        path = engine.screenshot_page(arguments['pdf_path'], arguments['page_num'],
                                        arguments.get('output_dir', './screenshots'))
        with open(path, 'rb') as f:
            img_data = f.read()
        return [
            TextContent(text=f"截图已保存: {path}"),
            ImageContent(data=img_data, mimeType="image/png")
        ]
    
    elif name == "generate_note":
        doc = engine.load_pdf(arguments['pdf_path'])
        text = doc['index'][arguments['page_num']]['text']
        note = engine.generate_note(text, arguments['page_num'], arguments['query'])
        return [TextContent(text=note)]
    
    elif name == "full_workflow":
        pdf_path = arguments['pdf_path']
        query = arguments['query']
        output_dir = arguments.get('output_dir', './notes')
        os.makedirs(output_dir, exist_ok=True)
        
        pages = engine.search_pages(pdf_path, query)
        pdf_name = os.path.splitext(os.path.basename(pdf_path))[0]
        note_dir = os.path.join(output_dir, pdf_name)
        os.makedirs(note_dir, exist_ok=True)
        os.makedirs(os.path.join(note_dir, 'screenshots'), exist_ok=True)
        
        md_content = f"# {pdf_name} 学习笔记\n\n> 问题: {query}\n> 来源: {pdf_path}\n\n---\n"
        
        for page in pages:
            screenshot_path = engine.screenshot_page(
                pdf_path, page, os.path.join(note_dir, 'screenshots')
            )
            doc = engine.load_pdf(pdf_path)
            text = doc['index'][page]['text']
            note = engine.generate_note(text, page, query)
            
            rel_screenshot = os.path.relpath(screenshot_path, note_dir)
            md_content += f"""
## 第 {page} 页

### 原文截图
![page_{page}]({rel_screenshot})

{note}

---
"""
        
        md_path = os.path.join(note_dir, 'notes.md')
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write(md_content)
        
        return [TextContent(
            text=f"笔记已生成!\n文件: {md_path}\n共处理 {len(pages)} 页"
        )]

async def main():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream)

if __name__ == "__main__":
    asyncio.run(main())
```

---

## 四、CCSwitch 配置指南

### 4.1 添加 Skill 仓库

```
CCSwitch -> Skills -> 仓库管理 -> 添加自定义仓库

Owner: your-username
Name: pdf-note-ai-workflow
Branch: main
Subdirectory: skills/          <- Skill 存放的子目录
```

CCSwitch 自动解析为：
```
https://github.com/your-username/pdf-note-ai-workflow/tree/main/skills/
```

### 4.2 添加 MCP Server

```
CCSwitch -> MCP -> + 按钮 -> 自定义配置

服务器 ID: pdf-note-mcp
名称: PDF Note MCP
描述: PDF 搜索、截图、笔记生成工具
传输类型: stdio
命令: uvx
参数:
  - --from
  - git+https://github.com/your-username/pdf-note-ai-workflow.git#subdirectory=mcp-server
  - pdf-note-mcp
环境变量:
  ANTHROPIC_API_KEY: sk-ant-xxx...
```

### 4.3 绑定同步

| 应用 | Skill 同步 | MCP 同步 |
|------|-----------|---------|
| Claude Code | ~/.claude/skills/ | ~/.claude.json |
| Codex | ~/.codex/skills/ | ~/.codex/config.toml |
| Gemini CLI | ~/.gemini/skills/ | ~/.gemini/settings.json |
| OpenCode | ~/.opencode/skills/ | ~/.opencode/config.json |

**注意**：修改配置后需重启终端生效。

---

## 五、使用流程

### 5.1 日常使用

```bash
# 1. 进入项目目录
cd my-study-notes/

# 2. 放入 PDF
mv ~/Downloads/attention_is_all_you_need.pdf ./

# 3. 启动 Claude Code
claude

# 4. 自然语言提问（自动触发 Skill）
> 请帮我分析 attention_is_all_you_need.pdf，我想了解：
> 1. 注意力机制的核心公式
> 2. 多头注意力的实现原理
> 3. 与 RNN 的对比优势

# 5. Claude Code 自动执行：
#    - 激活 Skill -> 按 SOP 执行
#    - 调用 MCP pdf_search -> 定位相关页面
#    - 调用 MCP pdf_screenshot -> 截取页面
#    - 调用 MCP generate_note -> 生成翻译讲解
#    - 写入 ./notes/attention_is_all_you_need/notes.md

# 6. 查看生成的笔记
cat ./notes/attention_is_all_you_need/notes.md
```

### 5.2 输出示例

```markdown
# attention_is_all_you_need 学习笔记

> 问题: 注意力机制的核心公式、多头注意力实现、与RNN对比
> 来源: ./attention_is_all_you_need.pdf

---

## 第 3 页

### 原文截图
![page_3](screenshots/page_3.png)

### 翻译
Scaled Dot-Product Attention（缩放点积注意力）的计算公式为：

Attention(Q, K, V) = softmax(QK^T / sqrt(d_k)) V

其中 Q（Query）、K（Key）、V（Value）是输入向量通过线性变换得到的矩阵。

### 讲解
想象你在图书馆找书：
- **Q（Query）**：你想找的书名（你的问题）
- **K（Key）**：书架上每本书的标签（文档的关键词）
- **V（Value）**：书的实际内容

通过计算 Q 和 K 的相似度（点积），找到最相关的书，然后取出它们的内容 V。除以 sqrt(d_k) 是为了防止点积值过大导致 softmax 梯度消失。

### 重点提炼
- 注意力机制的核心是查询-匹配-提取的三步操作
- 缩放因子 sqrt(d_k) 保证数值稳定性
- 完全并行计算，区别于 RNN 的串行结构

### 关联问题
1. 为什么用点积而不是其他相似度度量？
2. 如果没有缩放因子，训练会出现什么问题？
3. 自注意力中 Q、K、V 来自同一输入，这有什么特殊意义？

### 补充知识
- **推荐阅读**：《The Annotated Transformer》
- **相关概念**：Self-Attention、Cross-Attention、Causal Mask

---

## 第 5 页
...
```

---

## 六、技术依赖

### 6.1 Python 依赖

```toml
[project]
name = "pdf-note-mcp"
version = "0.1.0"
description = "MCP Server for PDF note-taking workflow"
dependencies = [
    "mcp>=1.0.0",
    "pdfplumber>=0.10.0",
    "pdf2image>=1.16.0",
    "anthropic>=0.40.0",
    "Pillow>=10.0.0",
]

[project.scripts]
pdf-note-mcp = "server:main"
```

### 6.2 系统依赖

| 系统 | 命令 |
|------|------|
| macOS | `brew install poppler` |
| Ubuntu | `sudo apt-get install poppler-utils` |
| Windows | 下载 poppler for Windows |

---

## 七、进阶优化方向

| 优化点 | 方案 | 优先级 |
|--------|------|--------|
| **语义搜索** | 用 `sentence-transformers` 替代关键词匹配 | 高 |
| **OCR 支持** | 扫描版 PDF 用 `paddleocr`/`easyocr` 识别 | 高 |
| **批量处理** | 一次提问处理多个 PDF | 中 |
| **学科模板** | 数学/计算机/生物等学科的专用笔记模板 | 中 |
| **增量更新** | 已有笔记时只追加新内容 | 中 |
| **知识库集成** | 与 Obsidian/Notion 同步 | 低 |
| **多语言支持** | 日文/德文等论文的翻译 | 低 |

---

## 八、项目总结

### 8.1 核心设计哲学

> **Skill 定义流程，MCP 提供能力，Claude Code 负责编排，CCSwitch 统一管理**

- **Skill** = 做什么（What）+ 怎么做（How）+ 做成什么样（Standard）
- **MCP** = 能做什么（Capabilities）+ 工具接口（API）
- **Claude Code** = 理解意图（Understand）+ 决策执行（Decide）+ 质量检查（Verify）
- **CCSwitch** = 配置集中（Centralize）+ 跨应用同步（Sync）+ 版本管理（Version）

### 8.2 为什么选择这个架构

| 方案 | 优点 | 缺点 |
|------|------|------|
| **纯脚本** | 简单直接 | 无 AI 编排能力，流程僵硬 |
| **纯 Skill** | 零代码，易维护 | 无法截图、无法精准定位 |
| **纯 MCP** | 工具能力强 | 无流程规范，输出格式混乱 |
| **Skill + MCP（本项目）** | 流程规范 + 能力完整 | 需要维护两个组件 |
| **Agent 框架（LangChain）** | 复杂决策能力强 | 过重，不适合个人工作流 |

### 8.3 关键成功因素

1. **GitHub 托管**：Skill 和 MCP 都放 GitHub，CCSwitch 自动拉取更新
2. **模板驱动**：固定的 Markdown 模板保证输出一致性
3. **分层解耦**：Skill 管流程、MCP 管工具、CCSwitch 管配置，互不侵入
4. **渐进优化**：先跑通关键词搜索，再升级语义搜索；先支持文本 PDF，再支持扫描版

---

## 九、快速开始 Checklist

- [ ] 在 GitHub 创建仓库 `pdf-note-ai-workflow`
- [ ] 编写 `skills/pdf-note-assistant/prompt.md`
- [ ] 编写 `mcp-server/server.py` 和 `pyproject.toml`
- [ ] 推送到 GitHub
- [ ] 在 CCSwitch 中添加 Skill 仓库和 MCP Server
- [ ] 安装系统依赖（poppler）
- [ ] 配置 `ANTHROPIC_API_KEY` 环境变量
- [ ] 测试：放入 PDF -> 提问 -> 检查生成的笔记
- [ ] 根据使用反馈优化 Skill 提示词和 MCP 工具

---

> **项目愿景**：让每一个学习者都能用自然语言与论文对话，自动产出结构化的知识笔记，实现读一篇论文 = 产出一篇笔记的闭环。