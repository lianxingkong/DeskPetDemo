import copy
import json
from pathlib import Path

from PyQt5.QtCore import QObject, pyqtSignal
from loguru import logger
from openai import Client

from .vector_handler import VectorHandler
from .. import app_config

path = Path(__file__).resolve().parent
filepath = path / 'memory.json'
data = json.loads(filepath.read_text(encoding='utf-8'))

client = Client(
    base_url=app_config.openai.api_url,
    api_key=app_config.openai.api_key,
    timeout=15
)


class HandleMemory(QObject):
    finished = pyqtSignal(object)
    query_result = pyqtSignal(str, object)  # (原始问题, 匹配到的记忆dict或None)

    def __init__(self):
        super().__init__()
        self.current_dialogue = None
        self._matched_group = None  # 暂存检索匹配到的组别

        # 初始化向量化模型
        self.embModel = VectorHandler()

    def query_memory(self, user_msg):
        """检索与当前问题相关的记忆"""
        self._matched_group = None

        # 1. 直接用权重匹配分数
        scored_groups = []
        for group in data.keys():
            score = data.get(group, {}).get("weight", "")
            scored_groups.append((group, score))

        # 2. 按权重匹配分数降序排序
        scored_groups.sort(key=lambda x: x[1], reverse=True)

        # 3. 依次用向量化判断相关性
        for group, _oi in scored_groups:
            old_mem = data.get(group, {}).get("memory", "")
            weight = data.get(group, {}).get("weight", 0)
            if not old_mem or weight <= 0:
                continue

            # 转换为字符串
            if isinstance(old_mem, list):
                old_mem_str = "\n".join(old_mem)
            else:
                old_mem_str = str(old_mem)

            try:
                result = self.embModel.calculate_similarity(old_mem_str, user_msg, group)
                if result == 1:
                    self._matched_group = group
                    break  # 找到一个即停
            except Exception as e:
                import traceback
                traceback.print_exc()
                logger.error(e)

        if self._matched_group:
            matched_data = {self._matched_group: copy.deepcopy(data[self._matched_group])}
            self.query_result.emit(user_msg, matched_data)
        else:
            self.query_result.emit(user_msg, None)


    def to_ai_memory(self, new_dialogue):
        """归档记忆，复用检索时已匹配的 group，不再二次判断相关性"""
        self.current_dialogue = new_dialogue

        if self.current_dialogue is None:
            logger.error("输入合并记忆的信息为空")
            return

        if self._matched_group and self._matched_group in data:
            # 有匹配：只需合并，不再判断相关性
            old_mem = data[self._matched_group]['memory']

            prompt = f"""【角色】你是一个专业的记忆归档助手，负责精简合并记忆。
【输入数据】
新信息：{self.current_dialogue}
记忆数据：{old_mem}
【处理规则】
1. 提取两者核心语义合并，去除冗余解释和过渡句。
2. 压缩率要求：纯文字部分必须精简，不超过新旧信息纯文字总和的75%。
3. 代码保护：如果内容包含代码，直接跳过代码部分【不参与精简计算，必须原样完整保留】，直接在其他内容精简完后将代码原样拼接到最后。
4. 忽略人物的语气词，如喵之类的，加速精简速度
【输出格式】
必须且只能严格按照以下纯文本格式输出，不要添加额外的解释、前言后缀或Markdown标记：
用户问题：[概括合并后的用户问题]
AI回复：[概括合并后的AI回复，若有代码则原样保留]"""
            try:
                refined_msg = self.call_ai_sync(prompt)
            except Exception as e:
                import traceback
                traceback.print_exc()
                logger.error(e)

            logger.debug(f"记忆合并时的动作{refined_msg}")
            # 增加对有效格式的判断，且超时/失败时保护原记忆
            if refined_msg != 0:

                # 最终清理后的完整memory
                clean_lines = [line for line in refined_msg.strip().split('\n')]

                data[self._matched_group]['memory'] = clean_lines
                data[self._matched_group]['weight'] += 1
                self.save_to_json()
                self.finished.emit(copy.deepcopy(data))
                logger.info(f"记忆已合并到组别 {self._matched_group}")
            else:
                logger.warning(f"记忆合并失败(API超时或格式错误)，保留组别 {self._matched_group} 原有记忆")

            self._matched_group = None
            return

        # 无匹配：新建记忆
        self._create_new_memory()

    # 符合条件时重置记忆
    def _create_new_memory(self):
        """在权重最低的组别新建记忆"""
        lowest_group = min(data.keys(), key=lambda k: data[k].get("weight", 0))
        data[lowest_group]['memory'] = self.current_dialogue
        data[lowest_group]['weight'] = 1
        self.save_to_json()
        self.finished.emit("")
        self._matched_group = None
        logger.info("未找到相关记忆，新记忆已归档")

    def call_ai_sync(self, prompt):
        """同步调用大模型API进行记忆精简"""
        if not client:
            logger.error("OpenAI Client 未初始化！无法调用API")
            return None

        try:
            response = client.chat.completions.create(
                model="Pro/deepseek-ai/DeepSeek-V3.2",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
            )

            # 提取结果
            if response.choices and len(response.choices) > 0:
                content = response.choices[0].message.content
                return content
            else:
                logger.warning("API 返回了空的内容")
                return None

        except Exception as e:
            import traceback
            traceback.print_exc()
            logger.error(e)


    def save_to_json(self):
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
        except Exception as e:
            logger.error(f"记忆文件保存失败: {e}")
