# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

通用的 CHM（Microsoft Compiled HTML Help）到 Markdown 转换工具。支持提取 CHM 文件中的所有 HTML 内容、图片资源和目录结构，转换为 AI 友好的 Markdown 文档库。

## 核心命令

### 转换CHM文件
```bash
uv run python scripts/convert.py \
  --input "<CHM文件路径>" \
  --output "<输出目录>" \
  --category "<分类名称>" \
  [--keep-temp]  # 可选：保留临时文件用于调试
```

示例：
```bash
uv run python scripts/convert.py \
  --input "./my-docs.chm" \
  --output "./output/my-docs" \
  --category "my-docs"
```

### 代码检查
```bash
uv run ruff check src/ scripts/
```

### 依赖管理
```bash
# 添加依赖
uv add <package-name>

# 添加开发依赖
uv add --dev <package-name>

# 同步依赖
uv sync
```

## 架构设计

### 转换流程（5步）

1. **CHM提取** (`extractor.py`)
   - 使用7-Zip CLI提取CHM文件（避免PyCHM在Windows上的编译问题）
   - 提取所有HTML文件和资源（图片等）

2. **目录解析** (`toc_parser.py`)
   - 解析`.hhc`文件（HTML Help Contents格式）
   - 提取完整的文档树形结构（支持8层嵌套）
   - 生成3个索引文件：
     - `toc.json` - 结构化目录树
     - `TOC.md` - 人类可读的目录树
     - `file_mapping.json` - 文件名→标题映射

3. **HTML转换** (`cleaner.py` + `converter.py`)
   - **清理**：移除script/style标签、清理属性
   - **编码检测**：从meta标签提取charset（支持GB2312/GBK/GB18030）
   - **转换**：使用html2text转为Markdown
   - **后处理**：修复表格格式、链接转换

4. **资源复制**
   - 复制所有图片到`assets/images/`
   - 修复Markdown中的图片路径引用

5. **元数据生成**
   - 生成`metadata.json`记录转换统计
   - 生成`README.md`

### 核心模块职责

**src/chm_converter/extractor.py**
- CHM文件提取（依赖7-Zip）
- 列出HTML文件

**src/chm_converter/cleaner.py**
- HTML清理和预处理
- 检测空内容
- 提取标题

**src/chm_converter/converter.py**
- HTML → Markdown转换
- 配置html2text选项（保留链接、图片、表格）
- 后处理（修复空行、列表格式）

**src/chm_converter/toc_parser.py**
- 解析`.hhc`文件
- 构建树形结构（TOCNode）
- 导出JSON和Markdown格式

**scripts/convert.py**
- 主转换脚本，整合所有模块
- 编码检测（`detect_html_encoding`）
- 链接修复（`fix_markdown_links`）
- 图片复制（`copy_images`）

### 关键设计决策

**为何使用7-Zip而非PyCHM**
- PyCHM在Windows上需要C编译器和chm_lib.h
- 7-Zip是跨平台的通用解决方案

**编码处理策略**
- 从HTML meta标签提取charset
- GB2312/GBK统一使用gb18030（向后兼容）
- 使用chardet作为fallback

**链接转换规则**
- `.html` → `.md`
- 支持尖括号包裹的链接：`](<file.html>)` → `](file.md)`
- 图片路径统一指向`assets/images/文件名`
- HTML锚点链接替换为`(#)`（Markdown中不可用）

**表格格式修复**
- 移除表头和分隔行之间的空行
- 确保表格前后有空行
- 处理html2text的表格输出问题

## 输出结构

转换后的文档结构：
```
<output-dir>/
└── <category>/
    ├── toc.json              # 结构化目录树
    ├── TOC.md                # 可读目录树
    ├── file_mapping.json     # 文件映射
    ├── metadata.json         # 转换元数据
    ├── README.md
    ├── assets/
    │   └── images/           # 图片文件
    └── *.md                  # 转换后的Markdown文件
```

## 重要约束

**大索引文件问题**
- 大型 CHM 转换后的 `toc.json` 可能达数百 KB，直接读取会消耗大量上下文
- **不要直接用Read工具读取完整索引文件**
- 使用 `file_mapping.json` 或 `TOC.md` 按需查找

**文件名不可读问题**
- Markdown文件名是CHM内部ID（如`zh-cn_topic_0000001511850684.md`）
- 真实标题在文件内的`# 标题`
- 使用`file_mapping.json`或`TOC.md`进行标题查找

**编码问题**
- CHM文档可能使用非 UTF-8 编码（如 GB2312）
- 必须先调用`detect_html_encoding()`检测编码
- 读取HTML时使用`encoding=编码, errors="replace"`

## 依赖说明

**运行时依赖**：
- `beautifulsoup4` + `lxml` - HTML解析
- `html2text` - Markdown转换
- `chardet` - 编码检测

**可选依赖**（向量索引构建）：
- `sentence-transformers`, `faiss-cpu`, `torch` - 安装方式：`uv sync --extra vector`

**外部依赖**：
- 7-Zip - 必须在PATH中或通过参数指定路径
