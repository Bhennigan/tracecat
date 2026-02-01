"""Schema router for Base Camp OS."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query
from starlette.status import (
    HTTP_201_CREATED,
    HTTP_204_NO_CONTENT,
    HTTP_404_NOT_FOUND,
)

from tracecat.auth.credentials import RoleACL
from tracecat.auth.types import Role
from tracecat.basecamp.enums import SchemaStatus
from tracecat.basecamp.schema.service import SchemaService
from tracecat.basecamp.schemas import (
    BaseCampSchemaCreate,
    BaseCampSchemaRead,
    BaseCampSchemaReadMinimal,
    BaseCampSchemaUpdate,
    SchemaInferRequest,
    SchemaInferResponse,
)
from tracecat.db.dependencies import AsyncDBSession
from tracecat.exceptions import TracecatNotFoundError

router = APIRouter(prefix="/basecamp/schemas", tags=["basecamp"])

WorkspaceUser = Annotated[
    Role,
    RoleACL(
        allow_user=True,
        allow_service=True,
        require_workspace="yes",
    ),
]


@router.get("")
async def list_schemas(
    *,
    role: WorkspaceUser,
    session: AsyncDBSession,
    status: SchemaStatus | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
) -> list[BaseCampSchemaReadMinimal]:
    """List all schemas for the workspace."""
    service = SchemaService(session, role)
    return await service.list_schemas(
        status=status,
        limit=limit,
        offset=offset,
    )


@router.get("/{schema_id}")
async def get_schema(
    *,
    role: WorkspaceUser,
    session: AsyncDBSession,
    schema_id: uuid.UUID,
    version: int | None = Query(default=None),
) -> BaseCampSchemaRead:
    """Get a schema by ID."""
    service = SchemaService(session, role)
    try:
        return await service.get_schema(schema_id, version=version)
    except TracecatNotFoundError:
        raise HTTPException(
            status_code=HTTP_404_NOT_FOUND, detail="Schema not found"
        ) from None


@router.post("", status_code=HTTP_201_CREATED)
async def create_schema(
    *,
    role: WorkspaceUser,
    session: AsyncDBSession,
    params: BaseCampSchemaCreate,
) -> BaseCampSchemaRead:
    """Create a new schema."""
    service = SchemaService(session, role)
    return await service.create_schema(params)


@router.patch("/{schema_id}")
async def update_schema(
    *,
    role: WorkspaceUser,
    session: AsyncDBSession,
    schema_id: uuid.UUID,
    params: BaseCampSchemaUpdate,
) -> BaseCampSchemaRead:
    """Update a schema.

    If fields are changed, a new version will be created.
    """
    service = SchemaService(session, role)
    try:
        return await service.update_schema(schema_id, params)
    except TracecatNotFoundError:
        raise HTTPException(
            status_code=HTTP_404_NOT_FOUND, detail="Schema not found"
        ) from None


@router.delete("/{schema_id}", status_code=HTTP_204_NO_CONTENT)
async def delete_schema(
    *,
    role: WorkspaceUser,
    session: AsyncDBSession,
    schema_id: uuid.UUID,
) -> None:
    """Delete a schema."""
    service = SchemaService(session, role)
    try:
        await service.delete_schema(schema_id)
    except TracecatNotFoundError:
        raise HTTPException(
            status_code=HTTP_404_NOT_FOUND, detail="Schema not found"
        ) from None


@router.post("/infer")
async def infer_schema(
    *,
    role: WorkspaceUser,
    session: AsyncDBSession,
    request: SchemaInferRequest,
) -> SchemaInferResponse:
    """Preview schema inference from sample data.

    Useful for previewing what schema would be inferred before creating it.
    """
    service = SchemaService(session, role)
    return await service.infer_schema_preview(request)
