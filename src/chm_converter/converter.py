"""Markdown转换模块

将清理后的HTML内容转换为Markdown格式
"""

import re

import html2text


class MarkdownConverter:
    """Markdown转换器"""

    def __init__(self):
        """初始化转换器"""
        self.h2t = html2text.HTML2Text()

        # 配置html2text选项
        self.h2t.ignore_links = False  # 保留链接
        self.h2t.ignore_images = False  # 保留图片
        self.h2t.ignore_emphasis = False  # 保留强调
        self.h2t.body_width = 0  # 不限制行宽
        self.h2t.unicode_snob = True  # 使用Unicode字符
        self.h2t.escape_snob = True  # 转义特殊字符
        self.h2t.mark_code = True  # 标记代码块
        self.h2t.protect_links = True  # 保护链接
        self.h2t.wrap_links = False  # 不换行链接
        self.h2t.default_image_alt = ""  # 默认图片alt文本
        self.h2t.skip_internal_links = False  # 不跳过内部链接
        self.h2t.inline_links = True  # 使用内联链接格式
        self.h2t.ul_item_mark = "-"  # 无序列表标记

    def html_to_markdown(self, html_content: str) -> str:
        """
        将HTML转换为Markdown

        Args:
            html_content: HTML内容

        Returns:
            Markdown内容
        """
        if not html_content:
            return ""

        try:
            # 转换为Markdown
            markdown = self.h2t.handle(html_content)

            # 后处理
            markdown = self._post_process(markdown)

            return markdown

        except Exception as e:
            print(f"警告: HTML转Markdown时出错: {e}")
            return ""

    def _post_process(self, markdown: str) -> str:
        """
        后处理Markdown内容

        Args:
            markdown: 原始Markdown

        Returns:
            处理后的Markdown
        """
        # 修复多余的空行（3个以上空行改为2个）
        markdown = re.sub(r"\n{4,}", "\n\n\n", markdown)

        # 修复表格周围的空行
        markdown = re.sub(r"\n{2,}(\|)", r"\n\n\1", markdown)
        markdown = re.sub(r"(\|)\n{2,}", r"\1\n\n", markdown)

        # 修复代码块周围的空行
        markdown = re.sub(r"\n{2,}(```)", r"\n\n\1", markdown)
        markdown = re.sub(r"(```)\n{2,}", r"\1\n\n", markdown)

        # 修复列表项之间的空行
        markdown = re.sub(r"(\n[-\*]\s+.*)\n{2,}([-\*]\s+)", r"\1\n\2", markdown)

        # 移除行尾空白
        lines = [line.rstrip() for line in markdown.split("\n")]
        markdown = "\n".join(lines)

        # 确保文件以单个换行符结尾
        markdown = markdown.rstrip() + "\n"

        return markdown

    def fix_links(self, markdown: str, base_path: str = "") -> str:
        """
        修复Markdown中的链接

        Args:
            markdown: Markdown内容
            base_path: 基础路径

        Returns:
            修复后的Markdown
        """
        # 将.html/.htm链接改为.md链接
        markdown = re.sub(r"\[([^\]]+)\]\(([^)]+\.html?)\)", r"[\1](\2)", markdown)

        # 可以在这里添加更多链接修复逻辑

        return markdown

    def add_frontmatter(
        self, markdown: str, title: str = "", metadata: dict = None
    ) -> str:
        """
        添加YAML frontmatter到Markdown

        Args:
            markdown: Markdown内容
            title: 文档标题
            metadata: 元数据字典

        Returns:
            带frontmatter的Markdown
        """
        if not title and not metadata:
            return markdown

        frontmatter = ["---"]

        if title:
            frontmatter.append(f"title: {title}")

        if metadata:
            for key, value in metadata.items():
                if isinstance(value, str):
                    frontmatter.append(f"{key}: {value}")
                elif isinstance(value, list):
                    frontmatter.append(f"{key}:")
                    for item in value:
                        frontmatter.append(f"  - {item}")
                else:
                    frontmatter.append(f"{key}: {value}")

        frontmatter.append("---")
        frontmatter.append("")

        return "\n".join(frontmatter) + markdown

    def extract_headings(self, markdown: str) -> list:
        """
        提取Markdown中的标题

        Args:
            markdown: Markdown内容

        Returns:
            标题列表，每个元素为(level, text, line_number)
        """
        headings = []
        lines = markdown.split("\n")

        for i, line in enumerate(lines, 1):
            # 匹配ATX风格标题 (# 标题)
            match = re.match(r"^(#{1,6})\s+(.+)$", line)
            if match:
                level = len(match.group(1))
                text = match.group(2).strip()
                headings.append((level, text, i))

        return headings

    def create_toc(self, markdown: str, max_level: int = 3) -> str:
        """
        创建目录（Table of Contents）

        Args:
            markdown: Markdown内容
            max_level: 最大标题级别

        Returns:
            目录Markdown
        """
        headings = self.extract_headings(markdown)

        if not headings:
            return ""

        toc_lines = ["## 目录\n"]

        for level, text, _ in headings:
            if level <= max_level:
                # 创建锚点链接
                anchor = text.lower()
                anchor = re.sub(r"[^\w\s-]", "", anchor)
                anchor = re.sub(r"[-\s]+", "-", anchor)

                indent = "  " * (level - 1)
                toc_lines.append(f"{indent}- [{text}](#{anchor})")

        return "\n".join(toc_lines) + "\n\n"
