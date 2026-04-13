"""
向量索引构建脚本

功能：
1. 扫描指定目录的所有 Markdown 文档
2. 使用 chunker 按标题分块
3. 使用 embedder 批量向量化（避免 OOM）
4. 构建 FAISS 索引（IndexFlatIP）
5. 保存索引 + 元数据到输出目录

使用方法：
    uv run python scripts/build_vector_index.py \\
        --docs-dir "../markdown-docs" \\
        --output-dir "../search-index/vector-store" \\
        --model "paraphrase-multilingual-MiniLM-L12-v2" \\
        --chunk-size 512 \\
        --batch-size 32

预期耗时（CPU）：
- 文档扫描：1分钟
- 分块：5-10分钟
- 向量化：20-30分钟（最耗时）
- 索引构建：2-5分钟
- 总计：30-45分钟
"""

import argparse
import json
import time
from datetime import datetime
from pathlib import Path

import faiss
import numpy as np
from chm_converter.chunker import MarkdownChunker, chunk_directory
from chm_converter.embedder import create_embedder


def build_index(
    docs_dir: Path,
    output_dir: Path,
    model_name: str,
    chunk_size: int,
    batch_size: int,
    device: str,
):
    """
    构建向量索引的主流程

    Args:
        docs_dir: 文档根目录
        output_dir: 输出目录
        model_name: embedding模型名称
        chunk_size: 分块大小（tokens）
        batch_size: 批处理大小
        device: 运行设备（auto/cpu/cuda）
    """
    print("=" * 60)
    print("🚀 开始构建文档向量索引")
    print("=" * 60)

    start_time = time.time()

    # 创建输出目录
    output_dir.mkdir(parents=True, exist_ok=True)

    # ===== 阶段1: 扫描文档目录 =====
    print(f"\n📂 文档目录: {docs_dir}")
    print(f"📁 输出目录: {output_dir}")

    categories = []
    for item in docs_dir.iterdir():
        if item.is_dir() and not item.name.startswith("."):
            categories.append(item.name)

    print(f"✅ 发现 {len(categories)} 个文档分类: {', '.join(categories)}")

    # ===== 阶段2: 初始化分块器和向量化器 =====
    chunker = MarkdownChunker(
        chunk_size=chunk_size, chunk_overlap=50, min_chunk_size=100
    )

    embedder = create_embedder(
        model_name=model_name, device=device, batch_size=batch_size
    )

    # ===== 阶段3: 分块和向量化 =====
    all_chunks = []
    all_embeddings = []

    for category in categories:
        category_dir = docs_dir / category

        if not category_dir.exists():
            print(f"⚠️  跳过不存在的目录: {category_dir}")
            continue

        print(f"\n{'=' * 60}")
        print(f"📚 处理分类: {category}")
        print(f"{'=' * 60}")

        # 分块
        chunks = chunk_directory(category_dir, category, chunker)

        if not chunks:
            print(f"⚠️  分类 {category} 没有生成任何块")
            continue

        # 提取文本
        texts = [chunk.text for chunk in chunks]

        # 向量化
        embeddings = embedder.encode_texts(texts)

        all_chunks.extend(chunks)
        all_embeddings.append(embeddings)

        print(f"✅ {category}: {len(chunks)} 个块")

    # ===== 阶段4: 合并所有embeddings =====
    print(f"\n{'=' * 60}")
    print("🔄 合并所有向量")
    print(f"{'=' * 60}")

    if not all_embeddings:
        print("❌ 没有生成任何embedding！")
        return

    all_embeddings_np = np.vstack(all_embeddings)
    total_chunks = len(all_chunks)

    print(f"✅ 总计: {total_chunks} 个文档块")
    print(f"   向量shape: {all_embeddings_np.shape}")

    # ===== 阶段5: 构建FAISS索引 =====
    print(f"\n{'=' * 60}")
    print("🔨 构建FAISS索引")
    print(f"{'=' * 60}")

    embedding_dim = all_embeddings_np.shape[1]

    # 使用IndexFlatIP（内积索引，适合归一化向量）
    # IndexFlatIP: 精确搜索，内存占用小，查询速度快
    index = faiss.IndexFlatIP(embedding_dim)

    # 添加向量到索引
    index.add(all_embeddings_np.astype("float32"))

    print("✅ FAISS索引构建完成")
    print("   索引类型: IndexFlatIP")
    print(f"   向量维度: {embedding_dim}")
    print(f"   索引向量数: {index.ntotal}")

    # ===== 阶段6: 保存索引和元数据 =====
    print(f"\n{'=' * 60}")
    print("💾 保存索引和元数据")
    print(f"{'=' * 60}")

    # 保存FAISS索引
    faiss_index_path = output_dir / "faiss.index"
    faiss.write_index(index, str(faiss_index_path))
    print(
        f"✅ FAISS索引: {faiss_index_path} ({faiss_index_path.stat().st_size / 1024 / 1024:.1f} MB)"
    )

    # 保存元数据
    metadata = [chunk.to_dict() for chunk in all_chunks]
    metadata_path = output_dir / "metadata.json"
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)
    print(
        f"✅ 元数据: {metadata_path} ({metadata_path.stat().st_size / 1024 / 1024:.1f} MB)"
    )

    # 保存chunks文本（可选，用于后续分析）
    chunks_path = output_dir / "chunks.json"
    with open(chunks_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "total": total_chunks,
                "embedding_dim": embedding_dim,
                "model_name": model_name,
                "chunk_size": chunk_size,
                "categories": categories,
                "chunks": metadata,
            },
            f,
            ensure_ascii=False,
            indent=2,
        )
    print(
        f"✅ Chunks数据: {chunks_path} ({chunks_path.stat().st_size / 1024 / 1024:.1f} MB)"
    )

    # 保存构建日志
    log_path = output_dir / "build_log.txt"
    with open(log_path, "w", encoding="utf-8") as f:
        f.write("文档向量索引构建日志\n")
        f.write("=" * 60 + "\n\n")
        f.write(f"构建时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"文档目录: {docs_dir}\n")
        f.write(f"输出目录: {output_dir}\n\n")
        f.write("配置参数:\n")
        f.write(f"  - 模型: {model_name}\n")
        f.write(f"  - 分块大小: {chunk_size} tokens\n")
        f.write(f"  - 批处理大小: {batch_size}\n")
        f.write(f"  - 设备: {device}\n\n")
        f.write("统计信息:\n")
        f.write(f"  - 文档分类数: {len(categories)}\n")
        f.write(f"  - 总文档块数: {total_chunks}\n")
        f.write(f"  - 向量维度: {embedding_dim}\n")
        f.write(
            f"  - 索引大小: {faiss_index_path.stat().st_size / 1024 / 1024:.2f} MB\n"
        )
        f.write(
            f"  - 元数据大小: {metadata_path.stat().st_size / 1024 / 1024:.2f} MB\n\n"
        )

        elapsed_time = time.time() - start_time
        f.write(f"构建耗时: {elapsed_time / 60:.1f} 分钟\n")

    print(f"✅ 构建日志: {log_path}")

    # ===== 完成 =====
    print(f"\n{'=' * 60}")
    print("🎉 索引构建完成！")
    print(f"{'=' * 60}")
    print("\n输出文件:")
    print(
        f"  - {faiss_index_path.name} ({faiss_index_path.stat().st_size / 1024 / 1024:.1f} MB)"
    )
    print(
        f"  - {metadata_path.name} ({metadata_path.stat().st_size / 1024 / 1024:.1f} MB)"
    )
    print(f"  - {chunks_path.name} ({chunks_path.stat().st_size / 1024 / 1024:.1f} MB)")
    print(f"  - {log_path.name}")

    elapsed_time = time.time() - start_time
    print(f"\n⏱️  总耗时: {elapsed_time / 60:.1f} 分钟")
    print("\n💡 索引构建完成，可用于文档检索。")


def main():
    """命令行入口"""
    parser = argparse.ArgumentParser(
        description="构建文档向量索引",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--docs-dir", type=str, required=True, help="Markdown文档根目录"
    )

    parser.add_argument("--output-dir", type=str, required=True, help="索引输出目录")

    parser.add_argument(
        "--model",
        type=str,
        default="paraphrase-multilingual-MiniLM-L12-v2",
        help="sentence-transformers模型名称（默认: paraphrase-multilingual-MiniLM-L12-v2）",
    )

    parser.add_argument(
        "--chunk-size", type=int, default=512, help="分块大小（tokens，默认512）"
    )

    parser.add_argument(
        "--batch-size",
        type=int,
        default=32,
        help="批处理大小（默认32，内存不足时降低到16或8）",
    )

    parser.add_argument(
        "--device",
        type=str,
        default="auto",
        choices=["auto", "cpu", "cuda"],
        help="运行设备（默认: auto，自动检测GPU）",
    )

    args = parser.parse_args()

    # 转换为Path对象
    docs_dir = Path(args.docs_dir)
    output_dir = Path(args.output_dir)

    # 验证输入
    if not docs_dir.exists():
        print(f"❌ 错误: 文档目录不存在: {docs_dir}")
        return 1

    # 构建索引
    build_index(
        docs_dir=docs_dir,
        output_dir=output_dir,
        model_name=args.model,
        chunk_size=args.chunk_size,
        batch_size=args.batch_size,
        device=args.device,
    )

    return 0


if __name__ == "__main__":
    exit(main())
