from loguru import logger
from modelscope import snapshot_download
from sentence_transformers import SentenceTransformer, util

from src.services.config import app_config

# 从 ModelScope 下载模型到本地
model_dir = snapshot_download('Qwen/Qwen3-Embedding-0.6B')

# 从本地路径加载
model = SentenceTransformer(model_dir)

class VectorHandler:

    @staticmethod
    def calculate_similarity(memory, query, group):
        """用新问题检索相关记忆"""

        threshold = app_config.memorial.threshold

        # 查询向量（加指令）
        q_emb = model.encode(
            query,
            prompt="Retrieve passages that share similar mathematical variables, logic, or contextual entities",
            normalize_embeddings=True
        )

        m_emb = model.encode(
            memory,
            normalize_embeddings=True
        )

        # 计算余弦相似度
        score = util.cos_sim(q_emb, m_emb).item()
        logger.debug(f"{group}记忆匹配程度{score}")

        if score >= threshold:
            return 1
        return 0
