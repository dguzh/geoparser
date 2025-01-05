from fastapi import Request, status
from fastapi.responses import JSONResponse


class SessionNotFoundException(Exception):
    pass


class DocumentNotFoundException(Exception):
    pass


class ToponymNotFoundException(Exception):
    pass


def session_exception_handler(request: Request, exc: SessionNotFoundException):
    return JSONResponse(
        content={"message": "Session not found.", "status": "error"},
        status_code=status.HTTP_404_NOT_FOUND,
    )


def document_exception_handler(request: Request, exc: DocumentNotFoundException):
    return JSONResponse(
        {"message": "Invalid document index.", "status": "error"},
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
    )


def toponym_exception_handler(request: Request, exc: ToponymNotFoundException):
    return JSONResponse(
        {"error": "Toponym not found"}, status_code=status.HTTP_404_NOT_FOUND
    )
