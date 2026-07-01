#!/usr/bin/env python3
"""pdf-note-mcp — Zero-AI MCP server for PDF text extraction and page screenshots.

Only two tools:
  - pdf_extract   : extract text from all pages via pdfplumber
  - pdf_screenshot: render a single page as PNG via pdf2image

All errors are caught and returned as Chinese TextContent — nothing leaks to stderr
except logging, and nothing touches stdout except MCP JSON-RPC.
"""

import asyncio
import logging
import os
import sys

import pdfplumber
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import ImageContent, TextContent, Tool

# ── Logging to stderr only (stdout is the MCP transport) ────────────────
logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s [%(levelname)s] %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger("pdf-note-mcp")

# ── Server instance ─────────────────────────────────────────────────────
server = Server("pdf-note-mcp")


# ══════════════════════════════════════════════════════════════════════════
# Pure helpers — zero AI, zero side-effects beyond filesystem
# ══════════════════════════════════════════════════════════════════════════

def _extract_all_text(pdf_path: str) -> dict[int, str]:
    """Return {page_num: text_content} for every page in the PDF.

    Raises ValueError with a user-facing Chinese message on failure.
    """
    try:
        with pdfplumber.open(pdf_path) as pdf:
            if len(pdf.pages) == 0:
                raise ValueError("PDF 文件没有页面。")

            result: dict[int, str] = {}
            for i, page in enumerate(pdf.pages, start=1):
                text = page.extract_text()
                result[i] = text if text else "(此页无文字内容)"
            return result

    except FileNotFoundError:
        raise ValueError(
            f"找不到文件 '{pdf_path}'。请确认路径正确且文件存在。"
        )
    except PermissionError:
        raise ValueError(
            f"无权限读取文件 '{pdf_path}'。请检查文件权限。"
        )
    except Exception as exc:
        msg = str(exc).lower()
        if any(kw in msg for kw in ("encrypt", "crypt", "password")):
            raise ValueError("PDF 文件已加密，无法提取文字。请先解密后再试。")
        if "not a valid pdf" in msg or "syntax" in msg:
            raise ValueError("PDF 文件可能已损坏或格式无效，无法解析。")
        raise ValueError(f"提取文字时发生错误: {str(exc)}")


def _render_page(
    pdf_path: str,
    page_num: int,
    output_dir: str = "./screenshots",
    dpi: int = 200,
) -> tuple[str, bytes]:
    """Render a single PDF page to PNG.  Returns (save_path, png_bytes).

    Raises ValueError with a user-facing Chinese message on failure.
    """
    from pdf2image import convert_from_path
    from pdf2image.exceptions import PDFInfoNotInstalledError

    # Validate page_num is positive
    if page_num < 1:
        raise ValueError(f"页码必须 >= 1，收到: {page_num}。")

    # Validate output_dir is writable
    try:
        os.makedirs(output_dir, exist_ok=True)
    except PermissionError:
        raise ValueError(
            f"无法创建目录 '{output_dir}'。请检查目录权限。"
        )

    # Quick page-count check
    try:
        with pdfplumber.open(pdf_path) as pdf:
            total_pages = len(pdf.pages)
    except FileNotFoundError:
        raise ValueError(
            f"找不到文件 '{pdf_path}'。请确认路径正确且文件存在。"
        )
    except Exception:
        total_pages = None  # will let pdf2image report the error

    if total_pages is not None and page_num > total_pages:
        raise ValueError(
            f"页码 {page_num} 超出范围。PDF 共 {total_pages} 页。"
        )

    # Render
    try:
        images = convert_from_path(
            pdf_path,
            first_page=page_num,
            last_page=page_num,
            dpi=dpi,
        )
    except FileNotFoundError:
        raise ValueError(
            f"找不到文件 '{pdf_path}'。请确认路径正确且文件存在。"
        )
    except PDFInfoNotInstalledError:
        raise ValueError(
            "未找到 poppler。Windows 用户请从 "
            "https://github.com/oschwartz10612/poppler-windows/releases "
            "下载并解压，将 Library/bin 加入系统 PATH。"
            "\nmacOS: brew install poppler"
            "\nUbuntu: sudo apt install poppler-utils"
        )
    except Exception as exc:
        msg = str(exc).lower()
        if any(kw in msg for kw in ("encrypt", "crypt", "password")):
            raise ValueError("PDF 文件已加密，无法截图。请先解密后再试。")
        if "page number" in msg or "out of range" in msg or "index" in msg:
            raise ValueError(
                f"页码 {page_num} 超出范围。"
                + (f" PDF 共 {total_pages} 页。" if total_pages else "")
            )
        raise ValueError(f"截图失败: {str(exc)}")

    if not images:
        raise ValueError(f"第 {page_num} 页渲染结果为空。")

    # Save
    save_path = os.path.join(output_dir, f"page_{page_num}.png")
    try:
        images[0].save(save_path, "PNG")
    except Exception as exc:
        raise ValueError(f"保存截图失败: {str(exc)}")

    # Read back bytes for MCP ImageContent
    with open(save_path, "rb") as fh:
        png_bytes = fh.read()

    return save_path, png_bytes


# ══════════════════════════════════════════════════════════════════════════
# MCP tool registration
# ══════════════════════════════════════════════════════════════════════════

@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="pdf_extract",
            description=(
                "提取 PDF 全部页面的文本内容。"
                "返回所有页的文本，每页以 '=== Page N ===' 分隔。"
                "无文字层（扫描版）的页面标记为 '(此页无文字内容)'。"
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "pdf_path": {
                        "type": "string",
                        "description": "PDF 文件的绝对路径。如 /home/user/paper.pdf",
                    }
                },
                "required": ["pdf_path"],
            },
        ),
        Tool(
            name="pdf_screenshot",
            description=(
                "将 PDF 的指定页面渲染为高清 PNG 截图（200 DPI）。"
                "截图保存到 output_dir 目录，同时返回图片数据供预览。"
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "pdf_path": {
                        "type": "string",
                        "description": "PDF 文件的绝对路径。",
                    },
                    "page_num": {
                        "type": "integer",
                        "description": "要截图的页码（1-indexed）。",
                        "minimum": 1,
                    },
                    "output_dir": {
                        "type": "string",
                        "description": "截图保存目录，默认 ./screenshots。",
                        "default": "./screenshots",
                    },
                },
                "required": ["pdf_path", "page_num"],
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent | ImageContent]:
    """Dispatch to the correct helper; all errors become TextContent."""

    # ── pdf_extract ─────────────────────────────────────────────────
    if name == "pdf_extract":
        pdf_path = arguments.get("pdf_path", "")
        if not pdf_path:
            return [TextContent(type="text", text="错误: 缺少必填参数 'pdf_path'。")]

        try:
            pages = _extract_all_text(pdf_path)
        except ValueError as exc:
            return [TextContent(type="text", text=str(exc))]

        blocks: list[str] = [f"共 {len(pages)} 页\n"]
        for num in sorted(pages):
            blocks.append(f"=== 第 {num} 页 ===\n{pages[num]}\n")
        return [TextContent(type="text", text="\n".join(blocks))]

    # ── pdf_screenshot ──────────────────────────────────────────────
    if name == "pdf_screenshot":
        pdf_path = arguments.get("pdf_path", "")
        page_num = arguments.get("page_num")
        output_dir = arguments.get("output_dir", "./screenshots")

        if not pdf_path:
            return [TextContent(type="text", text="错误: 缺少必填参数 'pdf_path'。")]
        if page_num is None:
            return [TextContent(type="text", text="错误: 缺少必填参数 'page_num'。")]
        if not isinstance(page_num, int):
            return [TextContent(type="text", text="错误: 'page_num' 必须是整数。")]

        try:
            save_path, png_bytes = _render_page(pdf_path, page_num, output_dir)
        except ValueError as exc:
            return [TextContent(type="text", text=str(exc))]

        return [
            TextContent(type="text", text=f"截图已保存: {save_path}"),
            ImageContent(type="image", data=png_bytes, mimeType="image/png"),
        ]

    # ── Unknown tool ────────────────────────────────────────────────
    return [TextContent(type="text", text=f"未知工具: '{name}'。可用工具: pdf_extract, pdf_screenshot。")]


# ══════════════════════════════════════════════════════════════════════════
# Entry point
# ══════════════════════════════════════════════════════════════════════════

async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
