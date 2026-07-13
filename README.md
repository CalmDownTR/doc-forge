# DocForge

[![Python](https://img.shields.io/badge/python-%E2%89%A53.12-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](https://opensource.org/licenses/MIT)

通用文档解析器，专为 RAG 应用设计。中文优先。一次函数调用将任意文档转换为结构化 Markdown。

Universal document parser for RAG applications. Chinese-first. One function call converts any document to structured Markdown.

---

**[中文](#中文)** | **[English](#english)**

---

## 中文

### 安装

```bash
pip install docforge-parser                    # 核心功能
pip install docforge-parser[ocr-surya]        # 含 Surya OCR
pip install docforge-parser[all]              # 全部功能
```

### 快速开始

```python
from docforge import parse

# 解析原生 PDF
result = parse("report.pdf")
print(result.markdown)

# 解析扫描件 PDF（OCR）
result = parse("scanned.pdf", ocr_backend="surya")

# 解析 DOCX 并提取图片
result = parse("document.docx", extract_images=True)
```

### Python API

**`parse(file_path, **kwargs) -> ParseResult`**

核心函数。接收文件路径和可选配置参数，返回 `ParseResult`。

`ParseResult` 包含：

- `markdown: str` — 渲染好的 Markdown 文本
- `blocks: list[ContentBlock]` — 通用中间表示（文本/表格/图片）
- `metadata: DocumentMetadata` — 文件类型、页数、解析方式
- `tables: list[TableResult]` — 表格索引（含行列数）
- `images: list[ImageResult]` — 图片索引（路径、位置）
- `warnings: list[ParseWarning]` — 非致命警告

**`ParseConfig`** 可选参数（通过 `**kwargs` 传入）：

| 参数 | 默认值 | 说明 |
| --- | --- | --- |
| `ocr_backend` | `"auto"` | OCR 后端：`"paddle"` / `"surya"` / `"auto"` / `"none"` |
| `ocr_languages` | `("chi_sim", "eng")` | OCR 识别语言 |
| `ocr_fallback` | `True` | 原生解析质量不足时自动切换 OCR |
| `extract_images` | `True` | 提取嵌入图片 |
| `image_format` | `"png"` | 图片输出格式 |
| `table_mode` | `"accurate"` | 表格解析模式 |
| `dpi` | `200` | 图片/PDF 渲染 DPI |
| `max_pages` | `None` | 最大解析页数 |

### CLI 用法

```bash
# 单文件解析
docforge parse document.pdf -o output.md

# 指定 OCR 后端
docforge parse document.pdf --ocr surya

# 导出表格为 CSV
docforge parse document.pdf --export-tables

# 批量解析目录
docforge parse ./docs/ --recursive -o ./output/
```

### 支持的格式

| 格式 | 扩展名 | 解析方式 |
| --- | --- | --- |
| PDF（原生文字层） | `.pdf` | PyMuPDF 原生提取 |
| PDF（扫描件） | `.pdf` | OCR（Surya / PaddleOCR） |
| Word | `.docx` | python-docx 原生提取 |
| Excel | `.xlsx` | openpyxl 原生提取 |
| PowerPoint | `.pptx` | python-pptx 原生提取 |
| 图片 | `.png` `.jpg` `.jpeg` `.gif` `.bmp` | OCR |
| 纯文本 | `.txt` | 直接读取 |
| Markdown | `.md` | 直接读取 |

### 已知限制

- v1 仅处理带边框表格，无边框表格不识别
- 不支持数学公式（`ContentType.FORMULA` 保留但未实现）
- 跨页表格仅做简单合并，不处理复杂跨页拆分
- OCR 扫描件解析比原生文本慢，建议为大批量场景安装 GPU 版 OCR

### 参与贡献

```bash
git clone https://github.com/CalmDownTR/doc-forge.git
cd doc-forge
uv sync --extra dev
uv run pytest tests/
uv run ruff check src/
```

欢迎提交 Issue 和 PR。

### 许可证

MIT License

---

## English

### Installation

```bash
pip install docforge-parser                    # Core only
pip install docforge-parser[ocr-surya]        # With Surya OCR
pip install docforge-parser[all]              # Everything
```

### Quickstart

```python
from docforge import parse

# Parse a native PDF
result = parse("report.pdf")
print(result.markdown)

# Parse a scanned PDF with OCR
result = parse("scanned.pdf", ocr_backend="surya")

# Parse a DOCX and extract images
result = parse("document.docx", extract_images=True)
```

### Python API

**`parse(file_path, **kwargs) -> ParseResult`**

Core function. Takes a file path and optional config overrides, returns a `ParseResult`.

`ParseResult` fields:

- `markdown: str` — rendered Markdown text
- `blocks: list[ContentBlock]` — universal IR (text/table/image)
- `metadata: DocumentMetadata` — file type, page count, parse method
- `tables: list[TableResult]` — table index (row/col counts)
- `images: list[ImageResult]` — image index (path, position)
- `warnings: list[ParseWarning]` — non-fatal warnings

**`ParseConfig`** options (via `**kwargs`):

| Parameter | Default | Description |
| --- | --- | --- |
| `ocr_backend` | `"auto"` | OCR backend: `"paddle"` / `"surya"` / `"auto"` / `"none"` |
| `ocr_languages` | `("chi_sim", "eng")` | OCR recognition languages |
| `ocr_fallback` | `True` | Auto-switch to OCR on low-quality native extraction |
| `extract_images` | `True` | Extract embedded images |
| `image_format` | `"png"` | Output image format |
| `table_mode` | `"accurate"` | Table extraction mode |
| `dpi` | `200` | Image/PDF render DPI |
| `max_pages` | `None` | Maximum pages to parse |

### CLI Usage

```bash
# Single file
docforge parse document.pdf -o output.md

# Specify OCR backend
docforge parse document.pdf --ocr surya

# Export tables as CSV
docforge parse document.pdf --export-tables

# Batch parse a directory
docforge parse ./docs/ --recursive -o ./output/
```

### Supported Formats

| Format | Extension | Method |
| --- | --- | --- |
| PDF (native text) | `.pdf` | PyMuPDF native extraction |
| PDF (scanned) | `.pdf` | OCR (Surya / PaddleOCR) |
| Word | `.docx` | python-docx native extraction |
| Excel | `.xlsx` | openpyxl native extraction |
| PowerPoint | `.pptx` | python-pptx native extraction |
| Image | `.png` `.jpg` `.jpeg` `.gif` `.bmp` | OCR |
| Plain text | `.txt` | Direct read |
| Markdown | `.md` | Direct read |

### Known Limitations

- v1 handles bordered tables only; borderless tables are not detected
- Math formulas are not supported (`ContentType.FORMULA` is reserved but not implemented)
- Cross-page table merging is basic; complex split tables are not handled
- OCR parsing of scanned documents is slower than native text; consider GPU-accelerated OCR for batch processing

### Contributing

```bash
git clone https://github.com/CalmDownTR/doc-forge.git
cd doc-forge
uv sync --extra dev
uv run pytest tests/
uv run ruff check src/
```

Issues and PRs welcome.

### License

MIT License
