"""极简的签名 token 鉴权（测试/上线前可用，生产请换 JWT/会话）。

设计要点：
- 登录/注册成功后服务端签发 token（HMAC-SHA256 签名 + 过期时间），不信任前端传入的 user_id。
- 前端把 token 放进 Authorization: Bearer 头（或 ?token= 查询参数）；后端用 get_current_user_id 校验，
  拿到真实 user_id 后再去查数据，从而关闭「改 URL 就能看别人数据」的越权（IDOR）。
- SECRET_KEY 必须在生产环境通过环境变量设置，否则使用写死的开发默认值（仅本地测试）。
"""
import base64
import hashlib
import hmac
import os
import time

from fastapi import Depends, Header, HTTPException, Query

from .database import get_db
from . import crud

SECRET = os.getenv("SECRET_KEY", "learnai-dev-secret-change-in-prod")
_TOKEN_TTL = 60 * 60 * 24 * 30  # 30 天


def create_token(user_id: int, ttl: int = _TOKEN_TTL) -> str:
    exp = int(time.time()) + ttl
    payload = f"{user_id}.{exp}"
    sig = hmac.new(SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return base64.urlsafe_b64encode(f"{payload}.{sig}".encode()).decode()


def verify_token(token: str | None) -> int | None:
    if not token:
        return None
    try:
        raw = base64.urlsafe_b64decode(token.encode()).decode()
        payload, sig = raw.rsplit(".", 1)
        uid_str, exp_str = payload.split(".")
        expected = hmac.new(SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, sig):
            return None
        if int(exp_str) < int(time.time()):
            return None
        return int(uid_str)
    except Exception:
        return None


def get_current_user_id(
    authorization: str | None = Header(None),
    token: str | None = Query(None),
) -> int:
    """从 Authorization: Bearer <token> 或 ?token= 提取并校验身份。校验失败一律 401。"""
    t = None
    if authorization and authorization.startswith("Bearer "):
        t = authorization[7:].strip()
    elif token:
        t = token.strip()
    uid = verify_token(t)
    if uid is None:
        raise HTTPException(status_code=401, detail="未登录或登录已过期，请重新登录")
    return uid
