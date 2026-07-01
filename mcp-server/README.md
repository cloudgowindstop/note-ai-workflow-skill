# pdf-note-mcp

> MCP Server 提供 `pdf_extract`（文本提取）和 `pdf_screenshot`（页面截图）两个工具。零 AI 调用，纯数据获取。

## 前置依赖

| 依赖 | 安装方式 |
|------|---------|
| Python 3.10+ | [python.org](https://www.python.org/) 或 `scoop install python` |
| uv | `scoop install uv` 或 `pip install uv` |
| **poppler**（Windows） | 见下方 ⬇ |

### Windows 安装 poppler

1. 下载 [poppler-windows](https://github.com/oschwartz10612/poppler-windows/releases) 最新 Release
2. 解压到固定目录，如 `C:\poppler\`
3. 将 `C:\poppler\Library\bin` 添加到系统 PATH
4. 验证：`pdftoppm -v` 能输出版本信息

> macOS: `brew install poppler` ｜ Ubuntu: `sudo apt install poppler-utils`

## 安装

```bash
# 通过 uvx 直接运行（CCSwitch 推荐）
uvx --from git+https://github.com/cloudgowindstop/note-ai-workflow-skill.git#subdirectory=mcp-server pdf-note-mcp

# 本地开发
git clone https://github.com/cloudgowindstop/note-ai-workflow-skill.git
cd note-ai-workflow-skill/mcp-server
uv sync
uv run pdf-note-mcp
```

## 工具参考

### pdf_extract

提取 PDF 全部页面的文本内容。

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `pdf_path` | string | ✅ | PDF 文件的绝对路径 |

**返回**：格式化的文本，每页以 `=== Page N ===` 分隔。无文字的页标记为 `(此页无文字内容)`。

### pdf_screenshot

将 PDF 指定页面渲染为 PNG 图片。

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `pdf_path` | string | ✅ | — | PDF 文件的绝对路径 |
| `page_num` | integer | ✅ | — | 页码（1-indexed） |
| `output_dir` | string | ❌ | `./screenshots` | 截图保存目录 |

**返回**：保存路径文本 + PNG 图片数据。

## 本地测试

```bash
cd mcp-server
uv sync
uv run mcp dev server.py
# 浏览器打开 http://localhost:5173 进入 MCP Inspector
```

## CCSwitch 配置

| 字段 | 值 |
|------|-----|
| 服务器 ID | `pdf-note-mcp` |
| 传输类型 | `stdio` |
| 命令 | `uvx` |
| 参数 | `--from git+https://github.com/cloudgowindstop/note-ai-workflow-skill.git#subdirectory=mcp-server pdf-note-mcp` |

## 故障排除

| 问题 | 解决方案 |
|------|---------|
| `PDFInfoNotInstalledError` | poppler 未安装或不在 PATH 中 |
| `FileNotFoundError` | 确认 `pdf_path` 使用绝对路径 |
| 加密 PDF 无法读取 | 先解密再处理 |
| 截图为空白 | 该页可能确实是空白页，检查原 PDF |
