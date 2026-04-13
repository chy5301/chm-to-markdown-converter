# chm-to-markdown-converter

将 CHM（Microsoft Compiled HTML Help）文件转换为 Markdown 文档库的命令行工具。

## 功能

- 提取 CHM 文件中的所有 HTML 内容和图片资源
- 解析 `.hhc` 目录文件，生成结构化目录树（JSON + Markdown）
- HTML → Markdown 转换（保留表格、链接、图片）
- 自动检测编码（支持 GB2312/GBK/GB18030 等非 UTF-8 编码）
- 生成文件名→标题映射索引

## 安装

```bash
git clone https://github.com/chy5301/chm-to-markdown-converter.git
cd chm-to-markdown-converter
uv sync
```

**外部依赖**：需要 [7-Zip](https://www.7-zip.org/) 在 PATH 中。

## 使用

```bash
uv run python scripts/convert.py \
  --input "<CHM文件路径>" \
  --output "<输出目录>" \
  --category "<分类名称>"
```

## 输出结构

```
<output-dir>/
└── <category>/
    ├── toc.json              # 结构化目录树
    ├── TOC.md                # 可读目录树
    ├── file_mapping.json     # 文件名→标题映射
    ├── metadata.json         # 转换统计
    ├── assets/images/        # 图片文件
    └── *.md                  # 转换后的 Markdown 文件
```

## 许可证

MIT
