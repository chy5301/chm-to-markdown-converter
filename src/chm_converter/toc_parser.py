"""目录树解析模块

从CHM的.hhc文件中提取文档树形结构
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Optional

from bs4 import BeautifulSoup, Tag


class TOCNode:
    """目录树节点"""

    def __init__(
        self,
        title: str,
        file_path: Optional[str] = None,
        level: int = 0,
        children: Optional[List["TOCNode"]] = None,
    ):
        self.title = title
        self.file_path = file_path
        self.level = level
        self.children = children or []

    def to_dict(self) -> dict:
        """转换为字典"""
        result = {
            "title": self.title,
            "level": self.level,
        }

        if self.file_path:
            # 转换.html为.md
            md_path = re.sub(r"\.html?$", ".md", self.file_path)
            result["file_path"] = md_path

        if self.children:
            result["children"] = [child.to_dict() for child in self.children]

        return result

    def to_markdown(self, indent: int = 0) -> str:
        """转换为Markdown目录树"""
        lines = []

        # 当前节点
        prefix = "  " * indent
        if self.file_path:
            md_path = re.sub(r"\.html?$", ".md", self.file_path)
            lines.append(f"{prefix}- [{self.title}]({md_path})")
        else:
            lines.append(f"{prefix}- {self.title}")

        # 子节点
        for child in self.children:
            lines.append(child.to_markdown(indent + 1))

        return "\n".join(lines)


class TOCParser:
    """CHM目录解析器"""

    def __init__(self):
        self.file_mapping = {}  # 文件路径 -> 标题的映射

    def parse_hhc_file(self, hhc_path: Path, encoding: str = "gb18030") -> TOCNode:
        """
        解析.hhc文件

        Args:
            hhc_path: .hhc文件路径
            encoding: 文件编码

        Returns:
            根节点
        """
        # 读取文件
        with open(hhc_path, "r", encoding=encoding, errors="replace") as f:
            content = f.read()

        # 解析HTML
        soup = BeautifulSoup(content, "lxml")

        # 找到顶层UL
        root_ul = soup.find("ul")
        if not root_ul:
            raise ValueError("未找到顶层UL元素")

        # 创建虚拟根节点
        root = TOCNode(title="Root", level=0)

        # 递归解析
        self._parse_ul(root_ul, root, level=1)

        return root

    def _parse_ul(self, ul_element: Tag, parent_node: TOCNode, level: int):
        """
        递归解析UL元素

        Args:
            ul_element: UL标签
            parent_node: 父节点
            level: 层级
        """
        # 遍历所有LI元素
        for li in ul_element.find_all("li", recursive=False):
            # 提取OBJECT元素
            obj = li.find("object", {"type": "text/sitemap"})
            if not obj:
                continue

            # 提取参数
            params = obj.find_all("param")
            title = None
            file_path = None

            for param in params:
                name = param.get("name", "").lower()
                value = param.get("value", "")

                if name == "name":
                    title = value
                elif name == "local":
                    file_path = value

            if not title:
                continue

            # 创建节点
            node = TOCNode(title=title, file_path=file_path, level=level)
            parent_node.children.append(node)

            # 更新文件映射
            if file_path:
                self.file_mapping[file_path] = title

            # 查找子UL
            child_ul = li.find("ul", recursive=False)
            if child_ul:
                self._parse_ul(child_ul, node, level + 1)

    def generate_file_mapping(self, root: TOCNode) -> Dict[str, str]:
        """
        生成文件映射（文件路径 -> 标题）

        Args:
            root: 根节点

        Returns:
            文件映射字典
        """
        return self.file_mapping.copy()

    def save_toc_json(self, root: TOCNode, output_path: Path):
        """
        保存TOC为JSON

        Args:
            root: 根节点
            output_path: 输出路径
        """
        toc_data = {
            "version": "1.0.0",
            "tree": root.to_dict(),
        }

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(toc_data, f, ensure_ascii=False, indent=2)

    def save_toc_markdown(self, root: TOCNode, output_path: Path):
        """
        保存TOC为Markdown

        Args:
            root: 根节点
            output_path: 输出路径
        """
        content = f"""# 文档目录

本目录由CHM文件的目录树自动生成。

{root.to_markdown()}
"""

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)

    def save_file_mapping(self, output_path: Path):
        """
        保存文件映射

        Args:
            output_path: 输出路径
        """
        # 转换.html为.md
        md_mapping = {}
        for html_path, title in self.file_mapping.items():
            md_path = re.sub(r"\.html?$", ".md", html_path)
            md_mapping[md_path] = title

        mapping_data = {
            "version": "1.0.0",
            "count": len(md_mapping),
            "mapping": md_mapping,
        }

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(mapping_data, f, ensure_ascii=False, indent=2)
