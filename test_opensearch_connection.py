"""
OpenSearch 연결 테스트 스크립트
"""
import os
import sys

print("=" * 50)
print("OpenSearch Connection Test")
print("=" * 50)

# 환경 변수 확인
print("\n1. Environment Variables:")
opensearch_host = os.environ.get("OPENSEARCH_HOST", "localhost")
opensearch_port = int(os.environ.get("OPENSEARCH_PORT", 9200))
print(f"  OPENSEARCH_HOST: {opensearch_host}")
print(f"  OPENSEARCH_PORT: {opensearch_port}")

# OpenSearch 연결 테스트
print("\n2. Connection Test:")
try:
    from opensearchpy import OpenSearch, RequestsHttpConnection
    
    client = OpenSearch(
        hosts=[{'host': opensearch_host, 'port': opensearch_port}],
        http_conn_class=RequestsHttpConnection,
        use_ssl=False,
        verify_certs=False,
        ssl_show_warn=False,
        timeout=5
    )
    
    # Ping 테스트
    try:
        ping_result = client.ping()
        if ping_result:
            print(f"  [OK] Connected to OpenSearch at {opensearch_host}:{opensearch_port}")
            
            # 클러스터 정보 확인
            try:
                info = client.info()
                print(f"  [OK] Cluster: {info.get('cluster_name', 'N/A')}")
                print(f"  [OK] Version: {info.get('version', {}).get('number', 'N/A')}")
            except Exception as e:
                print(f"  [WARNING] Could not get cluster info: {e}")
        else:
            print(f"  [ERROR] Could not ping OpenSearch at {opensearch_host}:{opensearch_port}")
            print("\nPossible solutions:")
            print("  1. Check if OpenSearch is running:")
            print("     - Docker: docker ps | findstr opensearch")
            print("     - Local: Check if port 9200 is listening")
            print("  2. Check OPENSEARCH_HOST environment variable")
            print("     - Docker: Should be 'opensearch' or 'localhost'")
            print("     - Local: Should be 'localhost'")
            print("  3. Start OpenSearch:")
            print("     - Docker: docker compose up opensearch")
            print("     - Or: docker run -p 9200:9200 opensearchproject/opensearch:latest")
    except Exception as e:
        print(f"  [ERROR] Connection failed: {e}")
        print("\nPossible solutions:")
        print("  1. OpenSearch is not running")
        print("  2. Wrong host/port configuration")
        print("  3. Firewall blocking connection")
        print("  4. Network connectivity issue")
        
except ImportError:
    print("  [ERROR] opensearch-py is not installed")
    print("  Install: pip install opensearch-py")
    sys.exit(1)

# 포트 확인
print("\n3. Port Check:")
import socket
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
result = sock.connect_ex((opensearch_host, opensearch_port))
sock.close()

if result == 0:
    print(f"  [OK] Port {opensearch_port} is open on {opensearch_host}")
else:
    print(f"  [ERROR] Port {opensearch_port} is not accessible on {opensearch_host}")
    print("\nPossible solutions:")
    print("  1. Start OpenSearch service")
    print("  2. Check firewall settings")
    print("  3. Verify host and port configuration")

print("\n" + "=" * 50)
