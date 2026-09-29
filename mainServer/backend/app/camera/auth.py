from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

bearer = HTTPBearer()


def verify_token(credentials: Annotated[HTTPAuthorizationCredentials, Depends(bearer)]) -> str:
    return credentials.credentials
