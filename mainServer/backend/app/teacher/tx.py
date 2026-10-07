from collections.abc import Callable
from contextlib import AbstractContextManager

import psycopg2
from fastapi import HTTPException, status
from fastapi.concurrency import run_in_threadpool

from common.db import ConflictError, write


def as_user(user_id: int) -> AbstractContextManager:
    return write("app.user_id", str(user_id))


def _in_transaction(tx: AbstractContextManager, func: Callable, *args):
    with tx as conn:
        return func(conn, *args)


async def run(tx: AbstractContextManager, func: Callable, *args):
    try:
        return await run_in_threadpool(_in_transaction, tx, func, *args)
    except ValueError as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(e)) from e
    except ConflictError as e:
        raise HTTPException(status.HTTP_409_CONFLICT, str(e)) from e
    except psycopg2.IntegrityError as e:
        raise HTTPException(status.HTTP_409_CONFLICT, e.pgerror or str(e)) from e
