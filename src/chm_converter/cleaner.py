"""HTML清理模块

清理HTML内容，移除无用标签和样式，为转换为Markdown做准备
"""

import re
from pathlib import Path
from typing import Optional

from bs4 import BeautifulSoup, Comment


class HTMLCleaner:
    """HTML清理器"""

    def __init__(self):
        """初始化清理器"""
        # 需要移除的标签
        self.remove_tags = ["script", "style", "nav", "footer", "iframe", "noscript"]

        # 需要移除的属性
        self.remove_attrs = ["style", "class", "id", "onclick", "onload"]

    def clean_html(self, html_content: str) -> str:
        """
        清理HTML内容

        Args:
            html_content: 原始HTML内容

        Returns:
            清理后的HTML内容
        """
        if not html_content:
            return ""

        # 使用lxml解析器（更快更健壮）
        soup = BeautifulSoup(html_content, "lxml")

        # 移除注释
        self._remove_comments(soup)

        # 移除无用标签
        self._remove_useless_tags(soup)

        # 清理属性
        self._clean_attributes(soup)

        # 处理特殊字符
        cleaned_html = str(soup)
        cleaned_html = self._normalize_whitespace(cleaned_html)

        return cleaned_html

    def _remove_comments(self, soup: BeautifulSoup) -> None:
        """移除HTML注释"""
        for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
            comment.extract()

    def _remove_useless_tags(self, soup: BeautifulSoup) -> None:
        """移除无用的标签"""
        for tag_name in self.remove_tags:
            for tag in soup.find_all(tag_name):
                tag.decompose()

    def _clean_attributes(self, soup: BeautifulSoup) -> None:
        """清理标签属性"""
        for tag in soup.find_all(True):
            # 移除指定的属性
            attrs_to_remove = []
            for attr in tag.attrs:
                if attr in self.remove_attrs:
                    attrs_to_remove.append(attr)

            for attr in attrs_to_remove:
                del tag.attrs[attr]

    def _normalize_whitespace(self, html: str) -> str:
        """规范化空白字符"""
        # 移除多余的空行
        html = re.sub(r"\n{3,}", "\n\n", html)

        # 移除行首行尾空白
        lines = [line.rstrip() for line in html.split("\n")]
        html = "\n".join(lines)

        return html

    def extract_title(self, html_content: str) -> Optional[str]:
        """
        提取HTML标题

        Args:
            html_content: HTML内容

        Returns:
            标题文本，如果没有则返回None
        """
        soup = BeautifulSoup(html_content, "lxml")

        # 尝试从<title>标签提取
        title_tag = soup.find("title")
        if title_tag and title_tag.string:
            return title_tag.string.strip()

        # 尝试从第一个<h1>标签提取
        h1_tag = soup.find("h1")
        if h1_tag:
            return h1_tag.get_text().strip()

        # 尝试从第一个<h2>标签提取
        h2_tag = soup.find("h2")
        if h2_tag:
            return h2_tag.get_text().strip()

        return None

    def process_images(
        self, soup: BeautifulSoup, base_path: Path, assets_dir: Path
    ) -> None:
        """
        处理图片引用

        Args:
            soup: BeautifulSoup对象
            base_path: HTML文件所在目录
            assets_dir: 资源文件目标目录
        """
        for img in soup.find_all("img"):
            src = img.get("src", "")
            if not src:
                continue

            # 如果是相对路径，尝试解析
            if not src.startswith(("http://", "https://", "data:")):
                # 构建图片的实际路径
                img_path = (base_path / src).resolve()

                if img_path.exists():
                    # 计算目标路径
                    rel_path = img_path.relative_to(base_path)
                    target_path = assets_dir / "images" / rel_path.name

                    # 更新src为相对于Markdown文件的路径
                    img["src"] = f"assets/images/{rel_path.name}"

    def extract_body_content(self, html_content: str) -> str:
        """
        提取body内容

        Args:
            html_content: HTML内容

        Returns:
            body中的HTML内容
        """
        soup = BeautifulSoup(html_content, "lxml")

        body = soup.find("body")
        if body:
            return str(body)

        # 如果没有body标签，返回整个内容
        return html_content

    def is_empty_content(self, html_content: str) -> bool:
        """
        检查HTML内容是否为空（只有标签没有实际文本）

        Args:
            html_content: HTML内容

        Returns:
            是否为空内容
        """
        soup = BeautifulSoup(html_content, "lxml")
        text = soup.get_text().strip()

        # 如果文本内容少于10个字符，认为是空内容
        return len(text) < 10
