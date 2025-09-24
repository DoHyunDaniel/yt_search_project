#!/usr/bin/env python3
"""
행궁 관련 검색어 관리 모듈
"""

# 행궁 관련 검색어 목록
PALACE_KEYWORDS = [
    # 주요 궁궐
    "경복궁", "창덕궁", "덕수궁", "창경궁", "경희궁",
    
    # 행궁 일반
    "행궁", "궁궐", "고궁", "왕궁",
    
    # 구체적 장소
    "경복궁 근정전", "창덕궁 인정전", "덕수궁 중화전",
    "창경궁 명정전", "경희궁 숭정전",
    
    # 관련 용어
    "궁궐 관광", "고궁 투어", "궁궐 역사", "조선 궁궐",
    "궁궐 문화", "궁궐 체험", "궁궐 가이드",
    
    # 지역별
    "서울 궁궐", "종로 궁궐", "중구 궁궐",
    
    # 활동
    "궁궐 산책", "궁궐 사진", "궁궐 탐방", "궁궐 답사"
]

# 검색어 카테고리별 분류
PALACE_CATEGORIES = {
    "main_palaces": ["경복궁", "창덕궁", "덕수궁", "창경궁", "경희궁"],
    "general_terms": ["행궁", "궁궐", "고궁", "왕궁"],
    "specific_places": [
        "경복궁 근정전", "창덕궁 인정전", "덕수궁 중화전",
        "창경궁 명정전", "경희궁 숭정전"
    ],
    "activities": [
        "궁궐 관광", "고궁 투어", "궁궐 역사", "조선 궁궐",
        "궁궐 문화", "궁궐 체험", "궁궐 가이드",
        "궁궐 산책", "궁궐 사진", "궁궐 탐방", "궁궐 답사"
    ],
    "locations": ["서울 궁궐", "종로 궁궐", "중구 궁궐"]
}

def get_all_keywords():
    """모든 행궁 관련 키워드 반환"""
    return PALACE_KEYWORDS.copy()

def get_keywords_by_category(category):
    """카테고리별 키워드 반환"""
    return PALACE_CATEGORIES.get(category, [])

def get_keywords_for_search():
    """검색에 사용할 키워드 목록 반환 (중복 제거)"""
    all_keywords = set()
    for category_keywords in PALACE_CATEGORIES.values():
        all_keywords.update(category_keywords)
    return list(all_keywords)

def find_most_similar_keywords(query, top_k=5):
    """입력된 쿼리와 가장 유사한 행궁 키워드들 반환"""
    # 간단한 문자열 유사도 계산
    query_lower = query.lower()
    similarities = []
    
    for keyword in PALACE_KEYWORDS:
        keyword_lower = keyword.lower()
        
        # 1. 완전 일치
        if query_lower == keyword_lower:
            similarities.append((keyword, 1.0))
            continue
            
        # 2. 포함 관계
        if query_lower in keyword_lower or keyword_lower in query_lower:
            similarity = min(len(query_lower), len(keyword_lower)) / max(len(query_lower), len(keyword_lower))
            similarities.append((keyword, similarity))
            continue
            
        # 3. 공통 단어 개수
        query_words = set(query_lower.split())
        keyword_words = set(keyword_lower.split())
        common_words = query_words.intersection(keyword_words)
        
        if common_words:
            similarity = len(common_words) / max(len(query_words), len(keyword_words))
            similarities.append((keyword, similarity))
    
    # 유사도 순으로 정렬하고 상위 k개 반환
    similarities.sort(key=lambda x: x[1], reverse=True)
    return similarities[:top_k]

if __name__ == "__main__":
    # 테스트
    print("=== 행궁 관련 키워드 목록 ===")
    for category, keywords in PALACE_CATEGORIES.items():
        print(f"\n{category}: {keywords}")
    
    print(f"\n=== 전체 키워드 수: {len(PALACE_KEYWORDS)} ===")
    
    # 유사도 테스트
    test_queries = ["궁궐", "경복궁", "고궁", "왕궁", "궁궐 관광"]
    for query in test_queries:
        print(f"\n=== '{query}' 검색 결과 ===")
        similar = find_most_similar_keywords(query, 3)
        for keyword, score in similar:
            print(f"  {keyword}: {score:.3f}")
