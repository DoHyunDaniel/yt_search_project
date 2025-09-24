import os
import numpy as np
from typing import List, Union, Optional
from sentence_transformers import SentenceTransformer
import torch

class EmbeddingService:
    """
    한국어 텍스트를 벡터 임베딩으로 변환하는 서비스
    
    지원 모델:
    - sentence-transformers/all-MiniLM-L6-v2: 경량, 빠름, 다국어 지원
    - jhgan/ko-sroberta-multitask: 한국어 특화, 높은 정확도
    """
    
    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        """
        임베딩 서비스 초기화
        
        Args:
            model_name: 사용할 모델명
        """
        self.model_name = model_name
        self.model = None
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self._load_model()
    
    def _load_model(self):
        """모델 로드"""
        try:
            print(f"Loading embedding model: {self.model_name}")
            self.model = SentenceTransformer(self.model_name, device=self.device)
            print(f"Model loaded successfully on {self.device}")
        except Exception as e:
            print(f"Failed to load model {self.model_name}: {e}")
            # 폴백 모델 사용
            fallback_model = "sentence-transformers/all-MiniLM-L6-v2"
            print(f"Loading fallback model: {fallback_model}")
            self.model = SentenceTransformer(fallback_model, device=self.device)
    
    def encode(self, texts: Union[str, List[str]], normalize: bool = True) -> np.ndarray:
        """
        텍스트를 벡터 임베딩으로 변환
        
        Args:
            texts: 변환할 텍스트 (단일 문자열 또는 문자열 리스트)
            normalize: 벡터 정규화 여부 (코사인 유사도 계산 시 권장)
            
        Returns:
            numpy array: 임베딩 벡터 (shape: [len(texts), embedding_dim])
        """
        if isinstance(texts, str):
            texts = [texts]
        
        if not texts or not any(texts):
            # 빈 텍스트의 경우 0 벡터 반환
            embedding_dim = self.model.get_sentence_embedding_dimension()
            return np.zeros((len(texts), embedding_dim))
        
        # 빈 문자열 필터링
        valid_texts = [text for text in texts if text and text.strip()]
        if not valid_texts:
            embedding_dim = self.model.get_sentence_embedding_dimension()
            return np.zeros((len(texts), embedding_dim))
        
        # 임베딩 생성
        embeddings = self.model.encode(
            valid_texts,
            convert_to_numpy=True,
            normalize_embeddings=normalize,
            show_progress_bar=len(valid_texts) > 100
        )
        
        # 원본 길이에 맞춰 패딩 (빈 문자열은 0 벡터)
        if len(valid_texts) < len(texts):
            embedding_dim = embeddings.shape[1]
            padded_embeddings = np.zeros((len(texts), embedding_dim))
            valid_idx = 0
            for i, text in enumerate(texts):
                if text and text.strip():
                    padded_embeddings[i] = embeddings[valid_idx]
                    valid_idx += 1
            embeddings = padded_embeddings
        
        return embeddings
    
    def get_embedding_dimension(self) -> int:
        """임베딩 차원 수 반환"""
        return self.model.get_sentence_embedding_dimension()
    
    def batch_encode(self, texts: List[str], batch_size: int = 32, normalize: bool = True) -> np.ndarray:
        """
        대용량 텍스트 배치 처리
        
        Args:
            texts: 변환할 텍스트 리스트
            batch_size: 배치 크기
            normalize: 벡터 정규화 여부
            
        Returns:
            numpy array: 임베딩 벡터
        """
        if not texts:
            return np.array([])
        
        all_embeddings = []
        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i:i + batch_size]
            batch_embeddings = self.encode(batch_texts, normalize=normalize)
            all_embeddings.append(batch_embeddings)
        
        return np.vstack(all_embeddings) if all_embeddings else np.array([])


def test_embedding_service():
    """임베딩 서비스 테스트"""
    print("=== Embedding Service Test ===")
    
    # 테스트 텍스트
    test_texts = [
        "제주도 맛집 추천",
        "제주 여행 코스",
        "제주 카페 투어",
        "서울 맛집",
        "부산 여행"
    ]
    
    # 모델별 테스트
    models_to_test = [
        "sentence-transformers/all-MiniLM-L6-v2",
        "jhgan/ko-sroberta-multitask"
    ]
    
    for model_name in models_to_test:
        try:
            print(f"\n--- Testing {model_name} ---")
            service = EmbeddingService(model_name)
            
            # 단일 텍스트 테스트
            single_embedding = service.encode("제주도 맛집")
            print(f"Single text embedding shape: {single_embedding.shape}")
            
            # 다중 텍스트 테스트
            embeddings = service.encode(test_texts)
            print(f"Multiple texts embedding shape: {embeddings.shape}")
            
            # 유사도 계산 테스트
            from sklearn.metrics.pairwise import cosine_similarity
            similarity_matrix = cosine_similarity(embeddings)
            print(f"Similarity matrix shape: {similarity_matrix.shape}")
            
            # 가장 유사한 텍스트 찾기
            query_idx = 0  # "제주도 맛집 추천"
            similarities = similarity_matrix[query_idx]
            most_similar_idx = np.argsort(similarities)[-2]  # 자기 자신 제외
            
            print(f"Query: {test_texts[query_idx]}")
            print(f"Most similar: {test_texts[most_similar_idx]} (similarity: {similarities[most_similar_idx]:.4f})")
            
        except Exception as e:
            print(f"Error testing {model_name}: {e}")


if __name__ == "__main__":
    test_embedding_service()
