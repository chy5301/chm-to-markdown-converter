"""
测试 embedder.py 模块

验证文本向量化功能是否正常工作
"""

import numpy as np
from chm_converter.embedder import TextEmbedder, create_embedder


class TestTextEmbedder:
    """测试 TextEmbedder 类"""

    def test_initialization_cpu(self):
        """测试CPU模式初始化"""
        embedder = TextEmbedder(
            model_name="paraphrase-multilingual-MiniLM-L12-v2",
            device="cpu",
            batch_size=32,
        )

        assert embedder.model_name == "paraphrase-multilingual-MiniLM-L12-v2"
        assert embedder.device == "cpu"
        assert embedder.batch_size == 32
        assert embedder.embedding_dim == 384  # 该模型的维度

    def test_encode_single_text(self):
        """测试单个文本向量化"""
        embedder = TextEmbedder(device="cpu")

        text = "这是一个测试文本"
        embedding = embedder.encode_single(text)

        # 验证返回值是numpy数组
        assert isinstance(embedding, np.ndarray)

        # 验证维度
        assert embedding.shape == (384,)  # MiniLM-L12-v2 的维度

        # 验证归一化（L2范数应该接近1）
        norm = np.linalg.norm(embedding)
        assert 0.99 < norm < 1.01  # 允许浮点误差

    def test_encode_multiple_texts(self):
        """测试批量文本向量化"""
        embedder = TextEmbedder(device="cpu", batch_size=2)

        texts = [
            "第一个测试文本",
            "第二个测试文本",
            "第三个测试文本",
            "第四个测试文本",
            "第五个测试文本",
        ]

        embeddings = embedder.encode_texts(texts)

        # 验证返回值是numpy数组
        assert isinstance(embeddings, np.ndarray)

        # 验证shape
        assert embeddings.shape == (5, 384)

        # 验证所有向量都归一化了
        norms = np.linalg.norm(embeddings, axis=1)
        assert np.all(norms > 0.99) and np.all(norms < 1.01)

    def test_encode_empty_list(self):
        """测试空列表"""
        embedder = TextEmbedder(device="cpu")

        embeddings = embedder.encode_texts([])

        # 空列表应该返回空数组
        assert embeddings.size == 0
        assert embeddings.shape == (0,)

    def test_embedding_similarity(self):
        """测试相似文本的embedding相似度"""
        embedder = TextEmbedder(device="cpu")

        # 相似的文本
        text1 = "如何配置网络"
        text2 = "网络配置的方法"
        # 不相似的文本
        text3 = "今天天气很好"

        emb1 = embedder.encode_single(text1)
        emb2 = embedder.encode_single(text2)
        emb3 = embedder.encode_single(text3)

        # 计算余弦相似度（因为已归一化，直接点积即可）
        sim_12 = np.dot(emb1, emb2)
        sim_13 = np.dot(emb1, emb3)

        # 相似文本的相似度应该更高
        assert sim_12 > sim_13

        # 相似度应该在[-1, 1]范围内
        assert -1 <= sim_12 <= 1
        assert -1 <= sim_13 <= 1

    def test_chinese_text_embedding(self):
        """测试中文文本向量化"""
        embedder = TextEmbedder(device="cpu")

        chinese_texts = ["自然语言处理技术", "机器学习算法", "深度学习框架"]

        embeddings = embedder.encode_texts(chinese_texts)

        # 验证shape
        assert embeddings.shape == (3, 384)

        # 验证没有NaN值
        assert not np.any(np.isnan(embeddings))

    def test_batch_processing(self):
        """测试批处理功能"""
        # 小batch size
        embedder = TextEmbedder(device="cpu", batch_size=2)

        # 5个文本，batch_size=2，应该分3批处理
        texts = [f"文本 {i}" for i in range(5)]

        embeddings = embedder.encode_texts(texts)

        # 验证结果正确
        assert embeddings.shape == (5, 384)


class TestCreateEmbedder:
    """测试 create_embedder 便捷函数"""

    def test_create_embedder_default_params(self):
        """测试默认参数创建"""
        embedder = create_embedder()

        assert isinstance(embedder, TextEmbedder)
        assert embedder.model_name == "paraphrase-multilingual-MiniLM-L12-v2"
        assert embedder.batch_size == 32

    def test_create_embedder_custom_params(self):
        """测试自定义参数创建"""
        embedder = create_embedder(
            model_name="paraphrase-multilingual-MiniLM-L12-v2",
            device="cpu",
            batch_size=16,
        )

        assert isinstance(embedder, TextEmbedder)
        assert embedder.device == "cpu"
        assert embedder.batch_size == 16
