import os

import numpy as np
import onnxruntime as ort
import tokenizers
from langchain_core.embeddings import Embeddings


class CustomEmbeddings(Embeddings):
    """本地 BGE 系列（ONNX）向量化，不依赖外部 API。

    模型目录由 EMBED_MODEL_DIR 指定，默认 ./models/bge-base-zh-v1.5（相对 backend）。
    目录里需要 tokenizer.json 和 model.onnx 两个文件。

    模型只加载一次（类级缓存），避免每次聊天都重新加载几百 MB 的权重。
    """

    _cache = {}

    @classmethod
    def _load(cls, model_dir):
        if model_dir in cls._cache:
            return cls._cache[model_dir]
        tokenizer_path = os.path.join(model_dir, 'tokenizer.json')
        model_path = os.path.join(model_dir, 'model.onnx')
        if not (os.path.exists(tokenizer_path) and os.path.exists(model_path)):
            raise FileNotFoundError(
                f'找不到本地向量模型：{model_dir}（需要 tokenizer.json 和 model.onnx）'
            )
        tokenizer = tokenizers.Tokenizer.from_file(tokenizer_path)
        session = ort.InferenceSession(model_path, providers=['CPUExecutionProvider'])
        input_names = [input_node.name for input_node in session.get_inputs()]
        cls._cache[model_dir] = (tokenizer, session, input_names)
        return cls._cache[model_dir]

    def __init__(self):
        model_dir = os.getenv('EMBED_MODEL_DIR', './models/bge-base-zh-v1.5')
        self.model_dir = model_dir
        self.tokenizer, self.session, self.input_names = self._load(model_dir)

    def _embed(self, texts):
        encodings = [self.tokenizer.encode(text) for text in texts]
        max_len = max(min(len(encoding.ids), 512) for encoding in encodings)
        batch = len(texts)
        input_ids = np.zeros((batch, max_len), dtype=np.int64)
        attention_mask = np.zeros((batch, max_len), dtype=np.int64)
        token_type_ids = np.zeros((batch, max_len), dtype=np.int64)
        for i, encoding in enumerate(encodings):
            ids = encoding.ids[:max_len]
            count = len(ids)
            input_ids[i, :count] = ids
            attention_mask[i, :count] = 1

        feeds = {
            'input_ids': input_ids,
            'attention_mask': attention_mask,
            'token_type_ids': token_type_ids,
        }
        selected = {name: feeds[name] for name in self.input_names if name in feeds}
        output = self.session.run(None, selected)[0]
        vectors = output[:, 0, :].astype(np.float32)  # BGE 取 [CLS] 向量
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        return vectors / np.maximum(norms, 1e-8)

    def embed_documents(self, texts):
        texts = [text for text in texts if text.strip()]
        if not texts:
            return []
        return self._embed(texts).tolist()

    def embed_query(self, text):
        return self._embed([text])[0].tolist()
