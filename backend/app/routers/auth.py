"""鉴权路由。"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from ..auth import create_access_token, get_current_user, verify_password
from ..schemas import LoginRequest, TokenResponse

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(form: OAuth2PasswordRequestForm = Depends()):
    """OAuth2 表单登录（username 忽略，仅校验 password）。"""
    if not verify_password(form.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="口令错误"
        )
    return TokenResponse(access_token=create_access_token())


@router.post("/login-json", response_model=TokenResponse)
def login_json(body: LoginRequest):
    """JSON 登录，供前端直接调用。"""
    if not verify_password(body.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="口令错误"
        )
    return TokenResponse(access_token=create_access_token())


@router.get("/me")
def me(user: str = Depends(get_current_user)):
    return {"user": user}
