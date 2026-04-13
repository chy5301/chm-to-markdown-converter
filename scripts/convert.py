#!/usr/bin/env python3
"""CHM到Markdown转换主脚本"""

import argparse
import json
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

# 添加src目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import chardet
from chm_converter.cleaner import HTMLCleaner
from chm_converter.converter import MarkdownConverter
from chm_converter.extractor import CHMExtractor
from chm_converter.toc_parser import TOCParser


def detect_html_encoding(file_path: Path) -> str:
    """
    检测HTML文件的编码

    Args:
        file_path: HTML文件路径

    Returns:
        编码名称
    """
    # 首先读取文件开头，尝试从meta标签中提取编码
    try:
        with open(file_path, "rb") as f:
            raw_data = f.read(4096)  # 读取前4KB

        # 尝试从meta标签中提取charset
        # <meta http-equiv="Content-Type" content="text/html; charset=gb2312">
        # <meta charset="utf-8">
        try:
            text = raw_data.decode("ascii", errors="ignore")
            charset_match = re.search(
                r'charset\s*=\s*["\']?([^"\'>\s]+)', text, re.IGNORECASE
            )
            if charset_match:
                charset = charset_match.group(1).lower()
                # 规范化编码名称
                if charset in ["gb2312", "gbk", "gb18030"]:
                    return "gb18030"  # 使用gb18030兼容gb2312和gbk
                elif charset in ["utf-8", "utf8"]:
                    return "utf-8"
                else:
                    return charset
        except Exception:
            pass

        # 使用chardet检测编码
        result = chardet.detect(raw_data)
        if result and result["encoding"]:
            encoding = result["encoding"].lower()
            # 规范化编码名称
            if "gb" in encoding or "chinese" in encoding:
                return "gb18030"
            return encoding

    except Exception as e:
        print(f"警告: 检测编码失败 {file_path.name}: {e}")

    # 默认使用gb18030（兼容中文CHM）
    return "gb18030"


def create_output_structure(output_dir: Path) -> dict:
    """
    创建输出目录结构

    Args:
        output_dir: 输出目录

    Returns:
        目录路径字典
    """
    dirs = {
        "root": output_dir,
        "temp": output_dir / "_temp",
        "assets": output_dir / "assets",
        "images": output_dir / "assets" / "images",
    }

    for path in dirs.values():
        path.mkdir(parents=True, exist_ok=True)

    return dirs


def process_html_files(
    html_files: list,
    temp_dir: Path,
    output_dir: Path,
    cleaner: HTMLCleaner,
    converter: MarkdownConverter,
) -> dict:
    """
    处理HTML文件，转换为Markdown

    Args:
        html_files: HTML文件路径列表
        temp_dir: 临时目录
        output_dir: 输出目录
        cleaner: HTML清理器
        converter: Markdown转换器

    Returns:
        处理统计信息
    """
    stats = {"total": len(html_files), "success": 0, "failed": 0, "skipped": 0}

    print(f"\n开始处理 {stats['total']} 个HTML文件...")

    for i, html_file in enumerate(html_files, 1):
        try:
            # 检测编码
            encoding = detect_html_encoding(html_file)

            # 读取HTML文件
            with open(html_file, "r", encoding=encoding, errors="replace") as f:
                html_content = f.read()

            # 检查是否为空内容
            if cleaner.is_empty_content(html_content):
                print(f"[{i}/{stats['total']}] 跳过空文件: {html_file.name}")
                stats["skipped"] += 1
                continue

            # 清理HTML
            cleaned_html = cleaner.clean_html(html_content)

            # 提取标题
            title = cleaner.extract_title(cleaned_html)

            # 转换为Markdown
            markdown = converter.html_to_markdown(cleaned_html)

            if not markdown.strip():
                print(f"[{i}/{stats['total']}] 跳过空转换: {html_file.name}")
                stats["skipped"] += 1
                continue

            # 修复链接和图片路径
            markdown = fix_markdown_links(markdown)

            # 确定输出路径
            rel_path = html_file.relative_to(temp_dir)
            md_file = output_dir / rel_path.with_suffix(".md")

            # 创建父目录
            md_file.parent.mkdir(parents=True, exist_ok=True)

            # 写入Markdown文件
            with open(md_file, "w", encoding="utf-8") as f:
                f.write(markdown)

            print(
                f"[{i}/{stats['total']}] ✓ 转换成功: {html_file.name} -> {md_file.name}"
            )
            stats["success"] += 1

        except Exception as e:
            print(f"[{i}/{stats['total']}] ✗ 转换失败: {html_file.name}")
            print(f"    错误: {e}")
            stats["failed"] += 1

    return stats


def copy_images(temp_dir: Path, output_dir: Path) -> int:
    """
    复制图片文件到assets目录

    Args:
        temp_dir: 临时目录
        output_dir: 输出目录

    Returns:
        复制的图片数量
    """
    assets_images_dir = output_dir / "assets" / "images"
    assets_images_dir.mkdir(parents=True, exist_ok=True)

    # 查找所有图片文件
    image_extensions = ["*.png", "*.jpg", "*.jpeg", "*.gif", "*.svg"]
    image_files = []
    for ext in image_extensions:
        image_files.extend(temp_dir.rglob(ext))

    copied_count = 0
    for img_file in image_files:
        try:
            # 目标路径：保持原文件名
            target_file = assets_images_dir / img_file.name

            # 如果文件已存在且同名，跳过
            if target_file.exists():
                continue

            # 复制文件
            shutil.copy2(img_file, target_file)
            copied_count += 1

        except Exception as e:
            print(f"警告: 复制图片失败 {img_file.name}: {e}")

    print(f"\n✓ 已复制 {copied_count} 个图片文件到 assets/images/")
    return copied_count


def fix_markdown_links(markdown: str) -> str:
    """
    修复Markdown中的链接

    Args:
        markdown: Markdown内容

    Returns:
        修复后的Markdown
    """

    # 1. 修复.html链接为.md链接
    # 匹配: ](<file.html>) 或 ](file.html)
    # 但不匹配外部URL (http:// 或 https://)
    def fix_html_link(match):
        url = match.group(1)  # 不包含.html后缀

        # 如果是外部URL，保持不变（保留尖括号）
        if url.startswith("http://") or url.startswith("https://"):
            return match.group(0)

        # 内部链接：添加.md后缀，并去掉尖括号
        return f"]({url}.md)"

    markdown = re.sub(r"\]\(<?([^)>]+)\.html>?\)", fix_html_link, markdown)

    # 2. 修复图片路径 - 将所有图片路径指向assets/images/
    # 匹配: ![alt](path/to/image.png) 或 ![](image.png)
    def fix_image_path(match):
        alt_text = match.group(1) if match.group(1) else ""
        img_path = match.group(2)

        # 提取文件名
        img_filename = Path(img_path).name

        # 返回修复后的路径
        return f"![{alt_text}](assets/images/{img_filename})"

    markdown = re.sub(r"!\[([^\]]*)\]\(([^)]+)\)", fix_image_path, markdown)

    # 3. 移除HTML锚点链接（它们在Markdown中无效）
    # 例如: [图1](<#ZH-CN_TOPIC_xxx__figxxx>) -> [图1](#)
    markdown = re.sub(r"\]\(<#[^>]+>\)", "](#)", markdown)

    # 4. 修复表格格式
    # 移除表头和分隔行之间的空行
    markdown = re.sub(r"(\|[^\n]+\|)\n\n(---)", r"\1\n\2", markdown)

    # 确保表格前后有空行
    lines = markdown.split("\n")
    fixed_lines = []
    in_table = False

    for i, line in enumerate(lines):
        # 识别表格行：包含 | 符号
        is_table_header = (
            "|" in line
            and "---|" not in line
            and (i + 1 < len(lines) and "---|" in lines[i + 1])
        )
        is_table_separator = "---|" in line
        is_table_content = "|" in line and "---|" not in line and in_table

        is_table_line = is_table_header or is_table_separator or is_table_content

        if (is_table_header or is_table_separator) and not in_table:
            # 表格开始，前面加空行
            if fixed_lines and fixed_lines[-1].strip():
                fixed_lines.append("")
            in_table = True
            fixed_lines.append(line)
        elif is_table_line and in_table:
            # 表格中
            fixed_lines.append(line)
        elif not is_table_line and in_table:
            # 表格结束，后面加空行
            in_table = False
            if line.strip():
                fixed_lines.append("")
            fixed_lines.append(line)
        else:
            # 普通行
            fixed_lines.append(line)

    markdown = "\n".join(fixed_lines)

    return markdown


def parse_toc(temp_dir: Path, output_dir: Path) -> dict:
    """
    解析CHM目录结构

    Args:
        temp_dir: 临时目录
        output_dir: 输出目录

    Returns:
        TOC统计信息
    """
    # 查找.hhc文件
    hhc_files = list(temp_dir.glob("*.hhc"))

    if not hhc_files:
        print("  警告: 未找到.hhc目录文件，跳过目录解析")
        return {"has_toc": False}

    hhc_file = hhc_files[0]
    print(f"  找到目录文件: {hhc_file.name}")

    try:
        # 解析TOC
        parser = TOCParser()
        root = parser.parse_hhc_file(hhc_file, encoding="gb18030")

        # 保存toc.json
        toc_json_path = output_dir / "toc.json"
        parser.save_toc_json(root, toc_json_path)
        print(f"  ✓ 已保存目录树: {toc_json_path.name}")

        # 保存toc.md
        toc_md_path = output_dir / "TOC.md"
        parser.save_toc_markdown(root, toc_md_path)
        print(f"  ✓ 已保存目录树(Markdown): {toc_md_path.name}")

        # 保存file_mapping.json
        file_mapping_path = output_dir / "file_mapping.json"
        parser.save_file_mapping(file_mapping_path)
        print(f"  ✓ 已保存文件映射: {file_mapping_path.name}")

        return {
            "has_toc": True,
            "file_count": len(parser.file_mapping),
            "max_depth": _get_max_depth(root),
        }

    except Exception as e:
        print(f"  警告: 目录解析失败: {e}")
        return {"has_toc": False, "error": str(e)}


def _get_max_depth(node, current_depth=0):
    """获取树的最大深度"""
    if not node.children:
        return current_depth
    return max(_get_max_depth(child, current_depth + 1) for child in node.children)


def create_metadata(
    chm_path: Path, output_dir: Path, category: str, stats: dict
) -> None:
    """
    创建元数据文件

    Args:
        chm_path: CHM文件路径
        output_dir: 输出目录
        category: 文档分类
        stats: 转换统计信息
    """
    metadata = {
        "version": "1.0.0",
        "source": {
            "file": chm_path.name,
            "size": chm_path.stat().st_size,
            "date": datetime.fromtimestamp(chm_path.stat().st_mtime).isoformat(),
        },
        "converted": {
            "date": datetime.now().isoformat(),
            "tool": "chm-to-markdown-converter",
            "version": "1.0.0",
        },
        "category": category,
        "statistics": stats,
    }

    metadata_file = output_dir / "metadata.json"
    with open(metadata_file, "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)

    print(f"\n✓ 元数据已保存: {metadata_file}")


def create_readme(output_dir: Path, category: str, stats: dict) -> None:
    """
    创建README文件

    Args:
        output_dir: 输出目录
        category: 文档分类
        stats: 转换统计信息
    """
    readme_content = f"""# {category.upper()} 文档

本文档由CHM文件自动转换而成。

## 转换信息

- 转换时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
- 总文件数: {stats["total"]}
- 转换成功: {stats["success"]}
- 转换失败: {stats["failed"]}
- 跳过文件: {stats["skipped"]}

## 文档结构

本目录包含从CHM文件提取的Markdown文档，按原始目录结构组织。

## 使用说明

1. 使用Claude Code的Read/Grep工具可以直接搜索和查询文档内容
2. 使用MCP Server可以实现语义搜索
3. 所有图片资源保存在 `assets/images/` 目录下

## 注意事项

- 部分复杂的HTML格式可能在转换过程中丢失
- 图片路径已更新为相对路径
- 建议查看原始CHM文件以确认关键信息
"""

    readme_file = output_dir / "README.md"
    with open(readme_file, "w", encoding="utf-8") as f:
        f.write(readme_content)

    print(f"✓ README已创建: {readme_file}")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="将CHM文件转换为Markdown文档")
    parser.add_argument("--input", required=True, help="CHM文件路径")
    parser.add_argument("--output", required=True, help="输出目录路径")
    parser.add_argument("--category", required=True, help="文档分类名称")
    parser.add_argument("--keep-temp", action="store_true", help="保留临时文件")

    args = parser.parse_args()

    # 路径处理
    chm_path = Path(args.input).resolve()
    output_dir = Path(args.output).resolve()

    # 验证输入文件
    if not chm_path.exists():
        print(f"错误: CHM文件不存在: {chm_path}")
        sys.exit(1)

    if not chm_path.suffix.lower() == ".chm":
        print(f"错误: 输入文件不是CHM格式: {chm_path}")
        sys.exit(1)

    print("=" * 60)
    print("CHM到Markdown转换工具")
    print("=" * 60)
    print(f"输入文件: {chm_path}")
    print(f"输出目录: {output_dir}")
    print(f"文档分类: {args.category}")
    print("=" * 60)

    # 创建输出目录结构
    dirs = create_output_structure(output_dir)

    # 初始化组件
    extractor = CHMExtractor()
    cleaner = HTMLCleaner()
    converter = MarkdownConverter()

    # 步骤1: 提取CHM文件
    print("\n[步骤 1/5] 提取CHM文件...")
    if not extractor.extract_chm(str(chm_path), str(dirs["temp"])):
        print("错误: CHM文件提取失败")
        sys.exit(1)

    # 获取HTML文件列表
    html_files = extractor.get_html_files(str(dirs["temp"]))
    print(f"✓ 找到 {len(html_files)} 个HTML文件")

    if not html_files:
        print("警告: 未找到HTML文件")
        sys.exit(1)

    # 步骤2: 解析目录结构
    print("\n[步骤 2/5] 解析目录结构...")
    toc_stats = parse_toc(dirs["temp"], output_dir)

    # 步骤3: 转换为Markdown
    print("\n[步骤 3/5] 转换HTML为Markdown...")
    stats = process_html_files(html_files, dirs["temp"], output_dir, cleaner, converter)
    stats["toc"] = toc_stats

    # 步骤4: 复制图片文件
    print("\n[步骤 4/5] 复制图片文件...")
    image_count = copy_images(dirs["temp"], output_dir)
    stats["images"] = image_count

    # 步骤5: 创建元数据和README
    print("\n[步骤 5/5] 生成元数据和文档...")
    create_metadata(chm_path, output_dir, args.category, stats)
    create_readme(output_dir, args.category, stats)

    # 清理临时文件
    if not args.keep_temp:
        print(f"\n清理临时文件: {dirs['temp']}")
        shutil.rmtree(dirs["temp"], ignore_errors=True)
    else:
        print(f"\n临时文件保留在: {dirs['temp']}")

    # 打印总结
    print("\n" + "=" * 60)
    print("转换完成!")
    print("=" * 60)
    print(f"总文件数: {stats['total']}")
    print(f"转换成功: {stats['success']}")
    print(f"转换失败: {stats['failed']}")
    print(f"跳过文件: {stats['skipped']}")
    print(f"成功率: {stats['success'] / stats['total'] * 100:.1f}%")
    print("=" * 60)


if __name__ == "__main__":
    main()
