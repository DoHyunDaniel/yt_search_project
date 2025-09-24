#!/usr/bin/env python3
"""
API 기능 테스트 스크립트
"""

import os
import sys
import requests
import json
from typing import Dict, Any

# 환경 설정
os.environ["DB_PORT"] = "55432"

# API 기본 URL
BASE_URL = "http://localhost:8000"

def test_endpoint(endpoint: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
    """API 엔드포인트 테스트"""
    url = f"{BASE_URL}{endpoint}"
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        return {
            "status": "success",
            "status_code": response.status_code,
            "data": response.json()
        }
    except requests.exceptions.RequestException as e:
        return {
            "status": "error",
            "error": str(e),
            "status_code": getattr(e.response, 'status_code', None) if hasattr(e, 'response') else None
        }

def main():
    """메인 테스트 함수"""
    print("=== API 기능 테스트 ===\n")
    
    # 1. 헬스 체크
    print("1. 헬스 체크 테스트")
    result = test_endpoint("/health")
    print(f"   결과: {result['status']}")
    if result['status'] == 'success':
        print(f"   데이터: {result['data']}")
    else:
        print(f"   오류: {result['error']}")
    print()
    
    # 2. 검색 방법 목록
    print("2. 검색 방법 목록 테스트")
    result = test_endpoint("/search_methods")
    print(f"   결과: {result['status']}")
    if result['status'] == 'success':
        methods = result['data']['methods']
        print(f"   지원 방법 수: {len(methods)}")
        for method in methods[:3]:  # 처음 3개만 출력
            print(f"   - {method['name']}: {method['description']}")
    else:
        print(f"   오류: {result['error']}")
    print()
    
    # 3. 임베딩 통계
    print("3. 임베딩 통계 테스트")
    result = test_endpoint("/embedding_stats")
    print(f"   결과: {result['status']}")
    if result['status'] == 'success':
        progress = result['data']['progress']
        print(f"   전체 영상: {progress['total_videos']}")
        print(f"   임베딩된 영상: {progress['embedded_videos']}")
        print(f"   진행률: {progress['progress_percent']:.1f}%")
    else:
        print(f"   오류: {result['error']}")
    print()
    
    # 4. 유사 검색 테스트 (텍스트 기반)
    print("4. 유사 검색 테스트 (jaccard 방법)")
    result = test_endpoint("/similar_search", {
        "q": "제주도 맛집",
        "method": "jaccard",
        "limit": 3
    })
    print(f"   결과: {result['status']}")
    if result['status'] == 'success':
        videos = result['data']
        print(f"   검색 결과 수: {len(videos)}")
        for i, video in enumerate(videos[:2], 1):  # 처음 2개만 출력
            print(f"   {i}. {video['title']} (유사도: {video.get('similarity_score', 0):.3f})")
    else:
        print(f"   오류: {result['error']}")
    print()
    
    # 5. 유사 키워드 테스트
    print("5. 유사 키워드 테스트")
    result = test_endpoint("/similar_keywords", {
        "q": "제주도",
        "method": "jaccard",
        "limit": 5
    })
    print(f"   결과: {result['status']}")
    if result['status'] == 'success':
        keywords = result['data']
        print(f"   키워드 수: {len(keywords)}")
        for i, kw in enumerate(keywords[:3], 1):  # 처음 3개만 출력
            print(f"   {i}. {kw['keyword']} (유사도: {kw['similarity_score']:.3f})")
    else:
        print(f"   오류: {result['error']}")
    print()
    
    print("=== 테스트 완료 ===")

if __name__ == "__main__":
    main()
