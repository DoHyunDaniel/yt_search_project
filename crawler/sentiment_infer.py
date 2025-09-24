import os
from typing import Tuple

from dotenv import load_dotenv
from transformers import AutoTokenizer, AutoModelForSequenceClassification, TextClassificationPipeline

from text_utils import clean_text, label_to_score


load_dotenv()

MODEL_NAME = os.getenv("SENTIMENT_MODEL", "beomi/KcELECTRA-base-v2022")  # 예시 한국어 모델


class SentimentService:
    def __init__(self, model_name: str = MODEL_NAME):
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForSequenceClassification.from_pretrained(model_name)
        self.pipeline = TextClassificationPipeline(model=self.model, tokenizer=self.tokenizer, return_all_scores=False)

    def infer(self, text: str) -> Tuple[str, float]:
        t = clean_text(text)
        if not t:
            return "neu", 0.0
        out = self.pipeline(t, truncation=True)[0]
        label = out.get("label", "neu").lower()
        score = float(out.get("score", 0.0))
        # 라벨 정규화 (positive/negative/neutral → pos/neg/neu 유사 매핑)
        if label.startswith("pos"):
            mapped = "pos"
        elif label.startswith("neg"):
            mapped = "neg"
        else:
            mapped = "neu"
        return mapped, label_to_score(mapped, score)


