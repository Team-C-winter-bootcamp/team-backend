import jwt
import requests
from typing import Optional, Dict, Any
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


def get_clerk_jwks_url(issuer: str) -> str:
    """
    Clerk issuer URL에서 JWKS 엔드포인트 URL을 생성합니다.
    
    Args:
        issuer: JWT 토큰의 issuer (예: https://your-domain.clerk.accounts.dev)
    
    Returns:
        JWKS 엔드포인트 URL
    """
    # Clerk의 issuer 형식에 따라 JWKS URL 생성
    if issuer.endswith('/'):
        issuer = issuer[:-1]
    return f"{issuer}/.well-known/jwks.json"


def get_jwks_keys(jwks_url: str) -> Dict[str, Any]:
    """
    JWKS 엔드포인트에서 공개 키를 가져옵니다.
    
    Args:
        jwks_url: JWKS 엔드포인트 URL
    
    Returns:
        JWKS 키 딕셔너리
    """
    try:
        response = requests.get(jwks_url, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        logger.error(f"JWKS 키를 가져오는 중 오류 발생: {e}")
        raise


def get_signing_key_from_jwks(jwks: Dict[str, Any], kid: str) -> Optional[str]:
    """
    JWKS에서 특정 kid(Key ID)에 해당하는 공개 키를 찾습니다.
    
    Args:
        jwks: JWKS 키 딕셔너리
        kid: Key ID
    
    Returns:
        공개 키 (PEM 형식) 또는 None
    """
    try:
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric import rsa
        import base64
        
        # JWKS에서 해당 kid의 키 찾기
        for key in jwks.get("keys", []):
            if key.get("kid") == kid:
                # RSA 공개 키 구성 요소 추출
                n = base64.urlsafe_b64decode(
                    key["n"] + "=="
                )
                e = base64.urlsafe_b64decode(
                    key["e"] + "=="
                )
                
                # RSA 공개 키 생성
                public_key = rsa.RSAPublicNumbers(
                    int.from_bytes(e, "big"),
                    int.from_bytes(n, "big")
                ).public_key()
                
                # PEM 형식으로 변환
                pem = public_key.public_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PublicFormat.SubjectPublicKeyInfo
                )
                return pem.decode("utf-8")
        
        return None
    except Exception as e:
        logger.error(f"공개 키를 생성하는 중 오류 발생: {e}")
        return None


def verify_clerk_token(token: str) -> tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
    """
    Clerk JWT 토큰을 검증합니다.
    
    검증 항목:
    1. 토큰 서명 검증 (위조 확인)
    2. 토큰 만료 확인
    3. 발급자(issuer) 확인
    
    Args:
        token: 검증할 JWT 토큰
    
    Returns:
        (검증 성공 여부, 디코딩된 페이로드, 오류 메시지) 튜플
    """
    try:
        # 토큰 헤더에서 kid 추출 (서명 검증을 위해)
        unverified_header = jwt.get_unverified_header(token)
        kid = unverified_header.get("kid")
        
        if not kid:
            return False, None, "토큰에 Key ID가 없습니다."
        
        # 토큰을 디코딩하여 issuer 확인 (서명 검증 없이)
        unverified_payload = jwt.decode(
            token,
            options={"verify_signature": False, "verify_exp": False}
        )
        
        issuer = unverified_payload.get("iss")
        if not issuer:
            return False, None, "토큰에 발급자 정보가 없습니다."
        
        # JWKS URL 생성 및 공개 키 가져오기
        jwks_url = get_clerk_jwks_url(issuer)
        jwks = get_jwks_keys(jwks_url)
        public_key = get_signing_key_from_jwks(jwks, kid)
        
        if not public_key:
            return False, None, "토큰 서명 검증에 필요한 공개 키를 찾을 수 없습니다."
        
        # 토큰 검증 (서명, 만료, issuer 모두 확인)
        try:
            payload = jwt.decode(
                token,
                public_key,
                algorithms=["RS256"],
                issuer=issuer,
                options={"verify_signature": True, "verify_exp": True, "verify_iss": True}
            )
            return True, payload, None
        except jwt.ExpiredSignatureError:
            return False, None, "토큰이 만료되었습니다."
        except jwt.InvalidIssuerError:
            return False, None, "토큰 발급자가 유효하지 않습니다."
        except jwt.InvalidSignatureError:
            return False, None, "토큰 서명이 유효하지 않습니다 (위조 가능성)."
        except jwt.InvalidTokenError as e:
            return False, None, f"토큰이 유효하지 않습니다: {str(e)}"
            
    except jwt.DecodeError:
        return False, None, "토큰 형식이 올바르지 않습니다."
    except Exception as e:
        logger.error(f"토큰 검증 중 오류 발생: {e}")
        return False, None, f"토큰 검증 중 오류가 발생했습니다: {str(e)}"

