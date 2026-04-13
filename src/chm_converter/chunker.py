"""
文档分块模块

将Markdown文档智能分割为小块，用于向量化和语义搜索。

核心策略：
- 按Markdown标题（#、##、###）分割，保持逻辑完整性
- 目标块大小：512 tokens（约1000-1500中文字符）
- 块之间重叠：50 tokens（约100字符），避免边界信息丢失
- 保留元数据：文件路径、分类、标题等
"""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List


@dataclass
class DocumentChunk:
    """文档分块"""

    text: str
    file_path: str
    category: str
    title: str
    chunk_id: int
    metadata: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "text": self.text,
            "file_path": self.file_path,
            "category": self.category,
            "title": self.title,
            "chunk_id": self.chunk_id,
            "metadata": self.metadata,
        }


class MarkdownChunker:
    """Markdown文档分块器"""

    def __init__(
        self, chunk_size: int = 512, chunk_overlap: int = 50, min_chunk_size: int = 100
    ):
        """
        初始化分块器

        Args:
            chunk_size: 目标块大小（tokens），默认512
            chunk_overlap: 块之间重叠大小（tokens），默认50
            min_chunk_size: 最小块大小（字符数），小于此值的块会被合并
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_chunk_size = min_chunk_size

    def chunk_file(self, file_path: Path, category: str) -> List[DocumentChunk]:
        """
        对单个Markdown文件进行分块

        Args:
            file_path: Markdown文件路径
            category: 文档分类标识符（如 my-project、tool-docs 等）

        Returns:
            DocumentChunk列表
        """
        # 读取文件内容
        try:
            content = file_path.read_text(encoding="utf-8")
        except Exception as e:
            print(f"⚠️  读取文件失败 {file_path}: {e}")
            return []

        # 提取标题（第一行 # 标题）
        title = self._extract_title(content)

        # 按标题分割文档
        sections = self._split_by_headings(content)

        # 为每个section创建chunk
        chunks = []
        chunk_id = 0

        for section in sections:
            # 移除标题行，只检查内容部分
            # 标题行格式：# 标题\n 或 ## 标题\n
            section_lines = section["text"].split("\n")
            content_without_heading = "\n".join(section_lines[1:]).strip()

            # 如果内容部分太小，跳过（避免只有标题的section）
            if len(content_without_heading) < self.min_chunk_size:
                continue

            # 计算字符数（粗略估计：1 token ≈ 2-3 中文字符）
            # chunk_size * 3 = 最大字符数
            max_chars = self.chunk_size * 3

            # 如果section太大，进一步分割
            if len(section["text"]) > max_chars:
                sub_chunks = self._split_large_text(section["text"], max_chars)
                for sub_chunk in sub_chunks:
                    chunk = DocumentChunk(
                        text=sub_chunk,
                        file_path=str(file_path.relative_to(file_path.parent.parent)),
                        category=category,
                        title=title,
                        chunk_id=chunk_id,
                        metadata={
                            "heading": section["heading"],
                            "level": section["level"],
                        },
                    )
                    chunks.append(chunk)
                    chunk_id += 1
            else:
                # section大小合适，直接作为一个chunk
                chunk = DocumentChunk(
                    text=section["text"],
                    file_path=str(file_path.relative_to(file_path.parent.parent)),
                    category=category,
                    title=title,
                    chunk_id=chunk_id,
                    metadata={"heading": section["heading"], "level": section["level"]},
                )
                chunks.append(chunk)
                chunk_id += 1

        return chunks

    def _extract_title(self, content: str) -> str:
        """提取文档标题（第一行 # 标题）"""
        lines = content.strip().split("\n")
        for line in lines:
            line = line.strip()
            if line.startswith("#"):
                # 移除 # 符号和空白
                title = re.sub(r"^#+\s*", "", line)
                return title
        return "Untitled"

    def _split_by_headings(self, content: str) -> List[Dict[str, Any]]:
        """
        按Markdown标题分割文档

        Returns:
            [
                {"heading": "标题", "level": 1, "text": "内容"},
                ...
            ]
        """
        sections = []
        current_section = {"heading": "", "level": 0, "text": ""}

        lines = content.split("\n")

        for line in lines:
            # 检查是否是标题行
            heading_match = re.match(r"^(#{1,6})\s+(.+)$", line)

            if heading_match:
                # 保存上一个section（如果非空）
                if current_section["text"].strip():
                    sections.append(current_section.copy())

                # 开始新section
                level = len(heading_match.group(1))
                heading = heading_match.group(2)
                current_section = {
                    "heading": heading,
                    "level": level,
                    "text": line + "\n",  # 保留标题行
                }
            else:
                # 添加到当前section
                current_section["text"] += line + "\n"

        # 保存最后一个section
        if current_section["text"].strip():
            sections.append(current_section)

        return sections

    def _split_large_text(self, text: str, max_chars: int) -> List[str]:
        """
        分割过大的文本块

        策略：
        - 优先按段落分割（空行分隔）
        - 如果单个段落超过max_chars，强制按字符数分割
        - 添加重叠部分，保持上下文连续性
        """
        chunks = []
        overlap_chars = self.chunk_overlap * 3  # 重叠字符数

        # 按段落分割
        paragraphs = re.split(r"\n\s*\n", text)

        current_chunk = ""
        current_length = 0

        for para in paragraphs:
            para_length = len(para)

            # 如果单个段落就超过max_chars（例如巨大的代码块或表格）
            # 强制按字符数分割
            if para_length > max_chars:
                # 先保存当前积累的chunk
                if current_chunk.strip():
                    chunks.append(current_chunk.strip())
                    current_chunk = ""
                    current_length = 0

                # 强制分割这个超大段落
                for i in range(0, para_length, max_chars - overlap_chars):
                    sub_para = para[i : i + max_chars]
                    if sub_para.strip():
                        chunks.append(sub_para.strip())
                continue  # 跳过后续处理

            # 如果当前chunk加上这个paragraph会超过限制
            if current_length + para_length > max_chars and current_chunk:
                # 保存当前chunk
                chunks.append(current_chunk.strip())

                # 计算重叠部分（最后几个字符）
                if overlap_chars > 0 and len(current_chunk) > overlap_chars:
                    # 从上一个chunk末尾提取重叠部分
                    overlap_start = len(current_chunk) - overlap_chars
                    overlap_text = current_chunk[overlap_start:]
                    current_chunk = overlap_text + "\n\n"  # 保留重叠作为新chunk开头
                    current_length = len(current_chunk)
                else:
                    current_chunk = ""
                    current_length = 0

            # 添加paragraph到当前chunk
            current_chunk += para + "\n\n"
            current_length += para_length + 2  # +2 for \n\n

        # 保存最后一个chunk
        if current_chunk.strip():
            chunks.append(current_chunk.strip())

        return chunks


def chunk_directory(
    docs_dir: Path, category: str, chunker: MarkdownChunker
) -> List[DocumentChunk]:
    """
    对整个目录的Markdown文件进行分块

    Args:
        docs_dir: 文档目录
        category: 文档分类
        chunker: 分块器实例

    Returns:
        所有DocumentChunk列表
    """
    all_chunks = []

    # 查找所有.md文件，但排除TOC.md（目录树文件）
    md_files = [f for f in docs_dir.rglob("*.md") if f.name != "TOC.md"]

    print(f"📂 扫到 {len(md_files)} 个Markdown文件（已过滤TOC.md）")

    for i, md_file in enumerate(md_files, 1):
        if i % 100 == 0:
            print(f"   处理中: {i}/{len(md_files)}")

        chunks = chunker.chunk_file(md_file, category)
        all_chunks.extend(chunks)

    print(f"✅ 分块完成: 共 {len(all_chunks)} 个块")

    return all_chunks
