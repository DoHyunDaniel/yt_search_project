import numpy as np
from typing import List, Tuple, Union, Optional
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.feature_extraction.text import TfidfVectorizer
import re
from collections import Counter
import Levenshtein
from nltk import ngrams
# 한국어 형태소 분석은 konlpy 사용 (선택사항)


class SimilarityCalculator:
    """
    다양한 유사도 계산 알고리즘을 제공하는 클래스
    
    지원 알고리즘:
    - 코사인 유사도 (벡터 기반)
    - 자카드 유사도 (집합 기반)
    - 편집 거리 (Levenshtein)
    - N-gram 유사도
    - TF-IDF 유사도
    """
    
    def __init__(self):
        self.tfidf_vectorizer = TfidfVectorizer(
            max_features=1000,
            stop_words=None,  # 한국어는 별도 처리
            ngram_range=(1, 2)
        )
    
    def cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """
        코사인 유사도 계산
        
        Args:
            vec1, vec2: 비교할 벡터 (1차원 또는 2차원)
            
        Returns:
            float: 코사인 유사도 (0~1)
        """
        if vec1.ndim == 1:
            vec1 = vec1.reshape(1, -1)
        if vec2.ndim == 1:
            vec2 = vec2.reshape(1, -1)
        
        similarity = cosine_similarity(vec1, vec2)[0][0]
        return float(similarity)
    
    def jaccard_similarity(self, text1: str, text2: str, ngram_size: int = 2) -> float:
        """
        자카드 유사도 계산 (N-gram 기반)
        
        Args:
            text1, text2: 비교할 텍스트
            ngram_size: N-gram 크기
            
        Returns:
            float: 자카드 유사도 (0~1)
        """
        def get_ngrams(text: str, n: int) -> set:
            """텍스트에서 N-gram 추출"""
            # 한국어 텍스트를 문자 단위로 분할
            chars = list(text.replace(' ', ''))
            if len(chars) < n:
                return set([text])
            return set([''.join(chars[i:i+n]) for i in range(len(chars)-n+1)])
        
        set1 = get_ngrams(text1, ngram_size)
        set2 = get_ngrams(text2, ngram_size)
        
        if not set1 and not set2:
            return 1.0
        if not set1 or not set2:
            return 0.0
        
        intersection = len(set1.intersection(set2))
        union = len(set1.union(set2))
        
        return intersection / union if union > 0 else 0.0
    
    def levenshtein_similarity(self, text1: str, text2: str) -> float:
        """
        편집 거리 기반 유사도 계산
        
        Args:
            text1, text2: 비교할 텍스트
            
        Returns:
            float: 편집 거리 유사도 (0~1, 1이 가장 유사)
        """
        if not text1 and not text2:
            return 1.0
        if not text1 or not text2:
            return 0.0
        
        max_len = max(len(text1), len(text2))
        distance = Levenshtein.distance(text1, text2)
        
        return 1.0 - (distance / max_len)
    
    def ngram_similarity(self, text1: str, text2: str, n: int = 2) -> float:
        """
        N-gram 유사도 계산 (문자 단위)
        
        Args:
            text1, text2: 비교할 텍스트
            n: N-gram 크기
            
        Returns:
            float: N-gram 유사도 (0~1)
        """
        def get_char_ngrams(text: str, n: int) -> List[str]:
            """문자 단위 N-gram 추출"""
            text = text.replace(' ', '')
            if len(text) < n:
                return [text]
            return [text[i:i+n] for i in range(len(text)-n+1)]
        
        ngrams1 = get_char_ngrams(text1, n)
        ngrams2 = get_char_ngrams(text2, n)
        
        if not ngrams1 and not ngrams2:
            return 1.0
        if not ngrams1 or not ngrams2:
            return 0.0
        
        # 공통 N-gram 개수 계산
        counter1 = Counter(ngrams1)
        counter2 = Counter(ngrams2)
        
        common_ngrams = 0
        for ngram in counter1:
            if ngram in counter2:
                common_ngrams += min(counter1[ngram], counter2[ngram])
        
        total_ngrams = sum(counter1.values()) + sum(counter2.values())
        
        return (2 * common_ngrams) / total_ngrams if total_ngrams > 0 else 0.0
    
    def tfidf_similarity(self, texts: List[str], query: str) -> List[float]:
        """
        TF-IDF 기반 유사도 계산
        
        Args:
            texts: 비교할 텍스트 리스트
            query: 쿼리 텍스트
            
        Returns:
            List[float]: 각 텍스트와의 TF-IDF 유사도
        """
        if not texts or not query:
            return [0.0] * len(texts)
        
        # 모든 텍스트에 쿼리 추가
        all_texts = texts + [query]
        
        try:
            # TF-IDF 벡터화
            tfidf_matrix = self.tfidf_vectorizer.fit_transform(all_texts)
            
            # 쿼리 벡터 (마지막)
            query_vector = tfidf_matrix[-1]
            text_vectors = tfidf_matrix[:-1]
            
            # 코사인 유사도 계산
            similarities = cosine_similarity(query_vector, text_vectors)[0]
            
            return similarities.tolist()
        except Exception as e:
            print(f"TF-IDF similarity error: {e}")
            return [0.0] * len(texts)
    
    def word_overlap_similarity(self, text1: str, text2: str) -> float:
        """
        단어 겹침 유사도 계산
        
        Args:
            text1, text2: 비교할 텍스트
            
        Returns:
            float: 단어 겹침 유사도 (0~1)
        """
        def tokenize_korean(text: str) -> set:
            """한국어 텍스트를 단어로 분할"""
            # 간단한 공백 기반 분할 (실제로는 형태소 분석기 사용 권장)
            words = set(text.split())
            # 2글자 이상 단어만 포함
            return {word for word in words if len(word) >= 2}
        
        words1 = tokenize_korean(text1)
        words2 = tokenize_korean(text2)
        
        if not words1 and not words2:
            return 1.0
        if not words1 or not words2:
            return 0.0
        
        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))
        
        return intersection / union if union > 0 else 0.0
    
    def calculate_similarity(self, 
                           text1: str, 
                           text2: str, 
                           method: str = "cosine",
                           vec1: Optional[np.ndarray] = None,
                           vec2: Optional[np.ndarray] = None) -> float:
        """
        통합 유사도 계산 메서드
        
        Args:
            text1, text2: 비교할 텍스트
            method: 유사도 계산 방법
            vec1, vec2: 벡터 기반 방법일 때 사용할 벡터
            
        Returns:
            float: 유사도 점수 (0~1)
        """
        method = method.lower()
        
        if method == "cosine":
            if vec1 is None or vec2 is None:
                raise ValueError("벡터 기반 방법은 vec1, vec2가 필요합니다")
            return self.cosine_similarity(vec1, vec2)
        
        elif method == "jaccard":
            return self.jaccard_similarity(text1, text2)
        
        elif method == "levenshtein":
            return self.levenshtein_similarity(text1, text2)
        
        elif method == "ngram":
            return self.ngram_similarity(text1, text2)
        
        elif method == "word_overlap":
            return self.word_overlap_similarity(text1, text2)
        
        else:
            raise ValueError(f"지원하지 않는 방법: {method}")
    
    def find_similar_texts(self, 
                          query: str, 
                          candidates: List[str], 
                          method: str = "cosine",
                          embeddings: Optional[np.ndarray] = None,
                          query_embedding: Optional[np.ndarray] = None,
                          top_k: int = 5) -> List[Tuple[str, float]]:
        """
        유사한 텍스트 찾기
        
        Args:
            query: 쿼리 텍스트
            candidates: 후보 텍스트 리스트
            method: 유사도 계산 방법
            embeddings: 후보 텍스트의 임베딩 (벡터 기반 방법용)
            query_embedding: 쿼리 임베딩 (벡터 기반 방법용)
            top_k: 반환할 상위 개수
            
        Returns:
            List[Tuple[str, float]]: (텍스트, 유사도) 튜플 리스트
        """
        similarities = []
        
        if method == "cosine" and embeddings is not None and query_embedding is not None:
            # 벡터 기반 유사도 계산
            for i, candidate in enumerate(candidates):
                similarity = self.cosine_similarity(query_embedding, embeddings[i])
                similarities.append((candidate, similarity))
        
        elif method == "tfidf":
            # TF-IDF 기반 유사도 계산
            sim_scores = self.tfidf_similarity(candidates, query)
            for candidate, score in zip(candidates, sim_scores):
                similarities.append((candidate, float(score)))
        
        else:
            # 텍스트 기반 유사도 계산
            for candidate in candidates:
                similarity = self.calculate_similarity(query, candidate, method)
                similarities.append((candidate, similarity))
        
        # 유사도 순으로 정렬하고 상위 k개 반환
        similarities.sort(key=lambda x: x[1], reverse=True)
        return similarities[:top_k]


def test_similarity_calculator():
    """유사도 계산기 테스트"""
    print("=== Similarity Calculator Test ===")
    
    # 테스트 데이터
    query = "제주도 맛집"
    candidates = [
        "제주 여행 코스",
        "제주 카페 투어", 
        "서울 맛집",
        "부산 여행",
        "제주도 관광지"
    ]
    
    calculator = SimilarityCalculator()
    
    # 각 방법별 테스트
    methods = ["jaccard", "levenshtein", "ngram", "word_overlap"]
    
    for method in methods:
        print(f"\n--- {method.upper()} Similarity ---")
        try:
            results = calculator.find_similar_texts(
                query, candidates, method=method, top_k=3
            )
            
            print(f"Query: {query}")
            for text, score in results:
                print(f"  {text}: {score:.4f}")
                
        except Exception as e:
            print(f"Error with {method}: {e}")
    
    # TF-IDF 테스트
    print(f"\n--- TF-IDF Similarity ---")
    try:
        results = calculator.find_similar_texts(
            query, candidates, method="tfidf", top_k=3
        )
        
        print(f"Query: {query}")
        for text, score in results:
            print(f"  {text}: {score:.4f}")
            
    except Exception as e:
        print(f"Error with TF-IDF: {e}")


if __name__ == "__main__":
    test_similarity_calculator()
