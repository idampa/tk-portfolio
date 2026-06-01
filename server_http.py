"""
Railway 배포용 HTTP(SSE) 진입점.
mcp_server.py는 stdio transport(로컬 Claude Desktop용)이고,
이 파일은 Railway에서 SSE transport로 실행하기 위한 래퍼다.

실행: python server_http.py
      PORT 환경변수가 없으면 8080 사용.
"""
import os
from mcp_server import mcp

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    mcp.run(transport="sse", host="0.0.0.0", port=port)
