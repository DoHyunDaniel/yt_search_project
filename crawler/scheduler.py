#!/usr/bin/env python3
"""
데이터 수집 및 임베딩 처리 자동화 스크립트
"""

import os
import sys
import time
import schedule
import logging
from datetime import datetime, timedelta
from typing import Optional

# 현재 디렉토리를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from crawl_comments import collect_comments
from process_comments import process_sentiment
from aggregate_sentiment import run as aggregate_sentiment
from generate_embeddings import EmbeddingPipeline

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('scheduler.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class DataProcessingScheduler:
    """데이터 처리 스케줄러"""
    
    def __init__(self):
        self.embedding_pipeline = EmbeddingPipeline()
        self.is_running = False
    
    def collect_new_comments(self):
        """새로운 댓글 수집"""
        try:
            logger.info("댓글 수집 시작")
            collect_comments(days=7, per_video_limit=300)
            logger.info("댓글 수집 완료")
        except Exception as e:
            logger.error(f"댓글 수집 실패: {e}")
    
    def process_sentiment_analysis(self):
        """감성분석 처리"""
        try:
            logger.info("감성분석 시작")
            process_sentiment(batch_size=100)
            logger.info("감성분석 완료")
        except Exception as e:
            logger.error(f"감성분석 실패: {e}")
    
    def aggregate_sentiment_data(self):
        """감성 데이터 집계"""
        try:
            logger.info("감성 데이터 집계 시작")
            aggregate_sentiment(days=7)
            logger.info("감성 데이터 집계 완료")
        except Exception as e:
            logger.error(f"감성 데이터 집계 실패: {e}")
    
    def generate_embeddings(self):
        """임베딩 생성"""
        try:
            logger.info("임베딩 생성 시작")
            self.embedding_pipeline.run(limit=200, batch_size=20)
            logger.info("임베딩 생성 완료")
        except Exception as e:
            logger.error(f"임베딩 생성 실패: {e}")
    
    def full_pipeline(self):
        """전체 파이프라인 실행"""
        try:
            logger.info("=== 전체 파이프라인 시작 ===")
            start_time = time.time()
            
            # 1. 댓글 수집
            self.collect_new_comments()
            
            # 2. 감성분석
            self.process_sentiment_analysis()
            
            # 3. 데이터 집계
            self.aggregate_sentiment_data()
            
            # 4. 임베딩 생성
            self.generate_embeddings()
            
            elapsed_time = time.time() - start_time
            logger.info(f"=== 전체 파이프라인 완료 (소요시간: {elapsed_time:.2f}초) ===")
            
        except Exception as e:
            logger.error(f"전체 파이프라인 실패: {e}")
    
    def setup_schedule(self):
        """스케줄 설정"""
        # 매일 새벽 2시에 전체 파이프라인 실행
        schedule.every().day.at("02:00").do(self.full_pipeline)
        
        # 매 4시간마다 댓글 수집 (기존 6시간)
        schedule.every(4).hours.do(self.collect_new_comments)
        
        # 매 1시간마다 감성분석 (기존 2시간)
        schedule.every(1).hours.do(self.process_sentiment_analysis)
        
        # 매 2시간마다 데이터 집계 (기존 4시간)
        schedule.every(2).hours.do(self.aggregate_sentiment_data)
        
        # 매 4시간마다 임베딩 생성 (기존 8시간)
        schedule.every(4).hours.do(self.generate_embeddings)
        
        logger.info("스케줄 설정 완료")
        logger.info("- 전체 파이프라인: 매일 02:00")
        logger.info("- 댓글 수집: 매 4시간")
        logger.info("- 감성분석: 매 1시간")
        logger.info("- 데이터 집계: 매 2시간")
        logger.info("- 임베딩 생성: 매 4시간")
    
    def run(self):
        """스케줄러 실행"""
        self.setup_schedule()
        self.is_running = True
        
        logger.info("스케줄러 시작")
        
        try:
            while self.is_running:
                schedule.run_pending()
                time.sleep(60)  # 1분마다 체크
        except KeyboardInterrupt:
            logger.info("스케줄러 종료 요청")
            self.is_running = False
        except Exception as e:
            logger.error(f"스케줄러 오류: {e}")
        finally:
            logger.info("스케줄러 종료")
    
    def stop(self):
        """스케줄러 중지"""
        self.is_running = False

def main():
    """메인 함수"""
    import argparse
    
    parser = argparse.ArgumentParser(description='데이터 처리 자동화 스케줄러')
    parser.add_argument('--mode', choices=['schedule', 'once'], default='schedule',
                       help='실행 모드: schedule(스케줄러), once(한 번만 실행)')
    parser.add_argument('--task', choices=['collect', 'sentiment', 'aggregate', 'embedding', 'full'],
                       help='특정 작업만 실행 (once 모드에서만 사용)')
    
    args = parser.parse_args()
    
    scheduler = DataProcessingScheduler()
    
    if args.mode == 'once':
        if args.task == 'collect':
            scheduler.collect_new_comments()
        elif args.task == 'sentiment':
            scheduler.process_sentiment_analysis()
        elif args.task == 'aggregate':
            scheduler.aggregate_sentiment_data()
        elif args.task == 'embedding':
            scheduler.generate_embeddings()
        elif args.task == 'full':
            scheduler.full_pipeline()
        else:
            print("--task 옵션을 지정해주세요")
    else:
        scheduler.run()

if __name__ == "__main__":
    main()
