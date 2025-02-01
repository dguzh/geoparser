from fastapi import Request, status
from fastapi.responses import JSONResponse

from geoparser.annotator.models.api import BaseResponse


class SessionNotFoundException(Exception):
    pass


class SessionSettingsNotFoundException(Exception):
    pass


class DocumentNotFoundException(Exception):
    pass


class ToponymNotFoundException(Exception):
    pass


class ToponymOverlapException(Exception):
    pass


def session_exception_handler(
    request: Request, exc: SessionNotFoundException
) -> JSONResponse:
    return JSONResponse(
        content={
            **BaseResponse(status="error", message="Session not found.").model_dump()
        },
        status_code=status.HTTP_404_NOT_FOUND,
    )


def sessionsettings_exception_handler(
    request: Request, exc: SessionSettingsNotFoundException
) -> JSONResponse:
    return JSONResponse(
        content={
            **BaseResponse(status="error", message="Settings not found.").model_dump()
        },
        status_code=status.HTTP_404_NOT_FOUND,
    )


def document_exception_handler(
    request: Request, exc: DocumentNotFoundException
) -> JSONResponse:
    return JSONResponse(
        content={
            **BaseResponse(
                status="error", message="Invalid document index."
            ).model_dump()
        },
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
    )


def toponym_exception_handler(
    request: Request, exc: ToponymNotFoundException
) -> JSONResponse:
    return JSONResponse(
        content={
            **BaseResponse(status="error", message="Toponym not found.").model_dump()
        },
        status_code=status.HTTP_404_NOT_FOUND,
    )


def toponym_overlap_exception_handler(
    request: Request, exc: ToponymOverlapException
) -> JSONResponse:
    return JSONResponse(
        content={
            **BaseResponse(
                status="error", message="Overlap with existing toponym."
            ).model_dump()
        },
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
    )
