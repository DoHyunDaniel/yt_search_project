#!/usr/bin/env python3
"""
간단한 정적 파일 서버
"""

import http.server
import socketserver
import os
import webbrowser
from threading import Timer

PORT = 3000

class CustomHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        # CORS 헤더 추가
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()

def open_browser():
    """브라우저 자동 열기"""
    webbrowser.open(f'http://localhost:{PORT}')

def main():
    """메인 함수"""
    # frontend 디렉토리로 이동
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    with socketserver.TCPServer(("", PORT), CustomHTTPRequestHandler) as httpd:
        print(f"프론트엔드 서버가 http://localhost:{PORT} 에서 실행 중입니다.")
        print("브라우저에서 자동으로 열립니다...")
        
        # 2초 후 브라우저 열기
        Timer(2.0, open_browser).start()
        
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n서버를 종료합니다.")

if __name__ == "__main__":
    main()
