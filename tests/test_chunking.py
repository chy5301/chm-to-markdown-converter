"""
测试 chunker.py 模块

验证文档分块功能是否正常工作
"""

from chm_converter.chunker import MarkdownChunker, DocumentChunk, chunk_directory


class TestMarkdownChunker:
    """测试 MarkdownChunker 类"""

    def test_initialization(self):
        """测试分块器初始化"""
        chunker = MarkdownChunker(chunk_size=512, chunk_overlap=50, min_chunk_size=100)
        assert chunker.chunk_size == 512
        assert chunker.chunk_overlap == 50
        assert chunker.min_chunk_size == 100

    def test_extract_title(self):
        """测试标题提取"""
        chunker = MarkdownChunker()

        # 测试标准标题
        content = "# 这是主标题\n\n一些内容"
        title = chunker._extract_title(content)
        assert title == "这是主标题"

        # 测试二级标题
        content = "## 这是二级标题\n\n内容"
        title = chunker._extract_title(content)
        assert title == "这是二级标题"

        # 测试无标题
        content = "直接是内容，没有标题"
        title = chunker._extract_title(content)
        assert title == "Untitled"

    def test_split_by_headings(self):
        """测试按标题分割"""
        chunker = MarkdownChunker()

        content = """# 第一章

第一章的内容

## 第一节

第一节的内容

# 第二章

第二章的内容
"""

        sections = chunker._split_by_headings(content)

        # 应该有3个section（第一章、第一节、第二章）
        assert len(sections) == 3

        # 验证第一个section
        assert sections[0]["heading"] == "第一章"
        assert sections[0]["level"] == 1
        assert "第一章的内容" in sections[0]["text"]

        # 验证第二个section
        assert sections[1]["heading"] == "第一节"
        assert sections[1]["level"] == 2

    def test_split_large_text(self):
        """测试大文本分割"""
        chunker = MarkdownChunker()
        max_chars = 100

        # 创建一个较长的文本
        long_text = "\n\n".join([f"段落 {i} 的内容" * 10 for i in range(10)])

        chunks = chunker._split_large_text(long_text, max_chars)

        # 验证分割成多个块
        assert len(chunks) > 1

        # 验证每个块不超过最大长度（允许一定误差）
        for chunk in chunks:
            assert len(chunk) <= max_chars + 50  # 允许重叠部分超出

    def test_chunk_file_with_small_file(self, tmp_path):
        """测试小文件分块"""
        # 创建测试文件（确保内容足够长，不会被过滤）
        test_file = tmp_path / "test.md"
        content = """# 测试文档

这是一个测试文档。这里需要有足够的内容才能生成分块，因为min_chunk_size默认是100字符。所以我们添加更多的内容来确保每个section都有足够的长度。

## 第一节

这是第一节的内容。为了确保内容不会被过滤掉，我们需要添加足够的文字。在Markdown分块策略中，小于min_chunk_size的块会被跳过。所以这里我们写一些更多的内容来确保测试能够正常工作。

## 第二节

这是第二节的内容。同样地，我们需要确保这个section有足够的长度。测试文档的分块功能对于验证整个系统非常重要。我们希望确保分块逻辑能够正确地处理各种大小的文档。
"""
        test_file.write_text(content, encoding="utf-8")

        # 测试分块
        chunker = MarkdownChunker(chunk_size=512, chunk_overlap=50, min_chunk_size=50)
        chunks = chunker.chunk_file(test_file, "test-category")

        # 验证结果
        assert len(chunks) > 0
        assert all(isinstance(chunk, DocumentChunk) for chunk in chunks)
        assert all(chunk.category == "test-category" for chunk in chunks)
        assert chunks[0].title == "测试文档"

    def test_chunk_file_with_large_file(self, tmp_path):
        """测试大文件分块（会触发进一步分割）"""
        # 创建一个大文件
        test_file = tmp_path / "large_test.md"

        # 生成大量内容
        content_parts = ["# 大文档\n\n"]
        for i in range(50):
            content_parts.append(f"## 第{i + 1}节\n\n")
            content_parts.append("这是一段很长的内容。" * 100 + "\n\n")

        test_file.write_text("".join(content_parts), encoding="utf-8")

        # 测试分块
        chunker = MarkdownChunker(chunk_size=512, chunk_overlap=50)
        chunks = chunker.chunk_file(test_file, "test-category")

        # 验证生成多个chunk
        assert len(chunks) > 10  # 大文件应该产生多个块

        # 验证chunk ID连续
        chunk_ids = [chunk.chunk_id for chunk in chunks]
        assert chunk_ids == list(range(len(chunks)))

    def test_chunk_file_with_nonexistent_file(self, tmp_path):
        """测试不存在的文件"""
        chunker = MarkdownChunker()
        nonexistent_file = tmp_path / "nonexistent.md"

        chunks = chunker.chunk_file(nonexistent_file, "test-category")

        # 不存在的文件应该返回空列表
        assert len(chunks) == 0

    def test_document_chunk_to_dict(self):
        """测试 DocumentChunk.to_dict() 方法"""
        chunk = DocumentChunk(
            text="测试文本",
            file_path="test/category/file.md",
            category="test-category",
            title="测试标题",
            chunk_id=0,
            metadata={"heading": "测试章节", "level": 1},
        )

        chunk_dict = chunk.to_dict()

        assert chunk_dict["text"] == "测试文本"
        assert chunk_dict["file_path"] == "test/category/file.md"
        assert chunk_dict["category"] == "test-category"
        assert chunk_dict["title"] == "测试标题"
        assert chunk_dict["chunk_id"] == 0
        assert chunk_dict["metadata"]["heading"] == "测试章节"


class TestChunkDirectory:
    """测试 chunk_directory 函数"""

    def test_chunk_directory_with_real_docs(self, tmp_path):
        """测试真实文档目录的分块"""
        # 创建测试文档目录结构
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()

        # 创建几个测试文件（确保内容足够长）
        for i in range(3):
            file_path = docs_dir / f"test_{i}.md"
            content = f"""# 测试文档 {i}

这是测试文档 {i} 的介绍部分。我们需要确保内容足够长，这样才能生成分块。在Markdown文档处理中，内容长度是一个重要的考虑因素。

## 章节 {i}.1

这是章节 {i}.1 的详细内容。为了确保文档分块功能正常工作，我们添加了足够的文字。这个测试会验证整个分块流程是否能够正确处理目录中的多个文件。

## 章节 {i}.2

这是章节 {i}.2 的内容。同样地，我们确保每个section都有足够的长度。这样可以避免因为内容过短而被过滤掉的情况。
"""
            file_path.write_text(content, encoding="utf-8")

        # 执行分块（使用较小的min_chunk_size）
        chunker = MarkdownChunker(chunk_size=512, chunk_overlap=50, min_chunk_size=50)
        chunks = chunk_directory(docs_dir, "test-category", chunker)

        # 验证结果
        assert len(chunks) > 0
        assert all(chunk.category == "test-category" for chunk in chunks)

    def test_chunk_directory_with_empty_directory(self, tmp_path):
        """测试空目录"""
        docs_dir = tmp_path / "empty_docs"
        docs_dir.mkdir()

        chunker = MarkdownChunker()
        chunks = chunk_directory(docs_dir, "test-category", chunker)

        # 空目录应该返回空列表
        assert len(chunks) == 0
