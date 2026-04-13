"""
文本向量化模块

使用sentence-transformers模型将文本转换为向量embeddings。

核心功能：
- 批量向量化文本（提高效率）
- GPU自动检测和加速
- 支持多语言模型（默认使用中文友好的multilingual模型）
"""

from typing import List


def _check_vector_deps():
    """检查向量化可选依赖是否已安装"""
    try:
        import numpy  # noqa: F401
        import torch  # noqa: F401
        from sentence_transformers import SentenceTransformer  # noqa: F401
    except ImportError as e:
        raise ImportError(
            "向量化功能需要安装可选依赖：uv sync --extra vector"
        ) from e


class TextEmbedder:
    """文本向量化器"""

    def __init__(
        self,
        model_name: str = "paraphrase-multilingual-MiniLM-L12-v2",
        device: str = "auto",
        batch_size: int = 32,
    ):
        """
        初始化向量化器

        Args:
            model_name: sentence-transformers模型名称
                默认: paraphrase-multilingual-MiniLM-L12-v2
                特点: 384维，支持100+语言，中文效果好，轻量级

                备选模型:
                - shibing624/text2vec-base-chinese: 专门针对中文优化（768维）
                - paraphrase-MiniLM-L6-v2: 更小更快（384维）

            device: 运行设备
                - "auto": 自动检测（有GPU就用GPU）
                - "cpu": 强制使用CPU
                - "cuda": 强制使用GPU

            batch_size: 批处理大小（默认32）
                较大的batch_size更快，但占用更多内存
                内存不足时降低此值（16、8）
        """
        _check_vector_deps()
        import torch
        from sentence_transformers import SentenceTransformer

        self.model_name = model_name
        self.batch_size = batch_size

        # 设备检测
        if device == "auto":
            if torch.cuda.is_available():
                self.device = "cuda"
                print("🔥 检测到GPU，使用CUDA加速")
            else:
                self.device = "cpu"
                print("💻 使用CPU运行")
        else:
            self.device = device
            print(f"🖥️  使用设备: {device}")

        # 加载模型
        print(f"📦 加载embedding模型: {model_name}")
        self.model = SentenceTransformer(model_name, device=self.device)
        self.embedding_dim = self.model.get_sentence_embedding_dimension()
        print(f"✅ 模型加载完成，向量维度: {self.embedding_dim}")

    def encode_texts(self, texts: List[str]) -> "np.ndarray":
        """
        批量向量化文本

        Args:
            texts: 文本列表

        Returns:
            numpy数组，shape=(len(texts), embedding_dim)
        """
        import numpy as np

        if not texts:
            return np.array([])

        print(f"🔄 向量化 {len(texts)} 个文本块...")

        # 批量编码（自动处理进度显示）
        embeddings = self.model.encode(
            texts,
            batch_size=self.batch_size,
            show_progress_bar=True,
            convert_to_numpy=True,
            normalize_embeddings=True,  # L2归一化，提高余弦相似度准确性
        )

        print(f"✅ 向量化完成，shape: {embeddings.shape}")

        return embeddings

    def encode_single(self, text: str) -> "np.ndarray":
        """
        向量化单个文本

        Args:
            text: 单个文本字符串

        Returns:
            numpy数组，shape=(embedding_dim,)
        """
        embedding = self.model.encode(
            text,
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return embedding


# 便捷函数
def create_embedder(
    model_name: str = "paraphrase-multilingual-MiniLM-L12-v2",
    device: str = "auto",
    batch_size: int = 32,
) -> TextEmbedder:
    """
    创建向量化器实例

    Args:
        model_name: 模型名称
        device: 设备（auto/cpu/cuda）
        batch_size: 批处理大小

    Returns:
        TextEmbedder实例
    """
    return TextEmbedder(model_name=model_name, device=device, batch_size=batch_size)
