"""Tracecat integration router for Base Camp OS."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter
from starlette.status import HTTP_201_CREATED

from tracecat.auth.credentials import RoleACL
from tracecat.auth.types import Role
from tracecat.basecamp.enums import IngestionState
from tracecat.basecamp.schemas import (
    DataQueryRequest,
    TracecatIngestRequest,
    TracecatIngestResponse,
    TracecatQueryRequest,
    TracecatQueryResponse,
)
from tracecat.basecamp.storage.service import DataRecordService
from tracecat.db.dependencies import AsyncDBSession
from tracecat.db.models import DataRecord, DataSource, IngestionJob
from tracecat.service import BaseWorkspaceService

router = APIRouter(prefix="/basecamp/tracecat", tags=["basecamp"])

# Allow both user and service/executor roles for workflow integration
WorkspaceServiceRole = Annotated[
    Role,
    RoleACL(
        allow_user=True,
        allow_service=True,
        allow_executor=True,
        require_workspace="yes",
    ),
]


class TracecatIntegrationService(BaseWorkspaceService):
    """Service for Tracecat workflow integration."""

    service_name = "basecamp_integration"

    async def ingest_from_workflow(
        self,
        request: TracecatIngestRequest,
    ) -> TracecatIngestResponse:
        """Ingest data from a Tracecat workflow.

        Args:
            request: The ingestion request.

        Returns:
            The ingestion response.
        """
        # Normalize data to list
        data_list = request.data if isinstance(request.data, list) else [request.data]

        # Create ingestion job
        job = IngestionJob(
            workspace_id=self.workspace_id,
            source_id=request.source_id,
            schema_id=request.schema_id,
            state=IngestionState.RECEIVED,
            file_name="tracecat_workflow",
            file_format=None,
            total_records=len(data_list),
            processed_records=0,
            failed_records=0,
        )

        self.session.add(job)
        await self.session.flush()
        await self.session.refresh(job)

        # Process records
        schema_id = request.schema_id
        if not schema_id and request.source_id:
            # Try to get schema from source
            from sqlalchemy import select

            stmt = select(DataSource).where(DataSource.id == request.source_id)
            result = await self.session.execute(stmt)
            source = result.scalar_one_or_none()
            if source and source.schema_id:
                schema_id = source.schema_id

        # If still no schema, infer one
        if not schema_id:
            from tracecat.basecamp.enums import FileFormat
            from tracecat.basecamp.ingestion.parsers.json_parser import JSONParser
            from tracecat.basecamp.schema.service import SchemaService
            from tracecat.basecamp.types import InferredSchema

            parser = JSONParser()

            # Build field values from sample data
            all_fields: set[str] = set()
            for record in data_list:
                if isinstance(record, dict):
                    all_fields.update(record.keys())

            field_values: dict[str, list[Any]] = {field: [] for field in all_fields}
            for record in data_list:
                if isinstance(record, dict):
                    for field in all_fields:
                        field_values[field].append(record.get(field))

            inferred_fields = [
                parser._create_inferred_field(name, values)
                for name, values in sorted(field_values.items())
            ]

            inferred_schema = InferredSchema(
                fields=inferred_fields,
                record_count=len(data_list),
                source_format=FileFormat.JSON,
            )

            schema_service = SchemaService(self.session, self.role)
            schema_name = f"workflow_{job.id.hex[:8]}"
            schema = await schema_service.create_schema_from_inferred(
                name=schema_name,
                inferred_schema=inferred_schema,
                description="Auto-generated from Tracecat workflow",
            )
            schema_id = schema.id
            job.schema_id = schema_id

        # Create records
        job.state = IngestionState.LOADING
        await self.session.flush()

        processed = 0
        failed = 0

        for item in data_list:
            if not isinstance(item, dict):
                failed += 1
                continue

            try:
                record = DataRecord(
                    workspace_id=self.workspace_id,
                    schema_id=schema_id,
                    job_id=job.id,
                    data=item,
                )
                self.session.add(record)
                processed += 1
            except Exception as e:
                self.logger.warning("Failed to create record", error=str(e))
                failed += 1

        await self.session.flush()

        # Update job status
        job.state = IngestionState.COMPLETE
        job.processed_records = processed
        job.failed_records = failed
        await self.session.flush()

        self.logger.info(
            "Workflow ingestion completed",
            job_id=str(job.id),
            processed=processed,
            failed=failed,
        )

        return TracecatIngestResponse(
            job_id=job.id,
            records_received=processed,
        )

    async def query_from_workflow(
        self,
        request: TracecatQueryRequest,
    ) -> TracecatQueryResponse:
        """Query data from a Tracecat workflow.

        Args:
            request: The query request.

        Returns:
            The query response with matching records.
        """
        service = DataRecordService(self.session, self.role)

        query_request = DataQueryRequest(
            schema_id=request.schema_id,
            filters=request.filters,
            limit=request.limit,
            offset=0,
        )

        response = await service.query(query_request)

        return TracecatQueryResponse(
            records=[r.data for r in response.records],
            total_count=response.total_count,
        )


@router.post("/ingest", status_code=HTTP_201_CREATED)
async def ingest_from_workflow(
    *,
    role: WorkspaceServiceRole,
    session: AsyncDBSession,
    request: TracecatIngestRequest,
) -> TracecatIngestResponse:
    """Webhook for ingesting data from Tracecat workflows.

    This endpoint is designed to be called from workflow actions
    to push data into Base Camp for storage and analysis.
    """
    service = TracecatIntegrationService(session, role)
    return await service.ingest_from_workflow(request)


@router.post("/query")
async def query_from_workflow(
    *,
    role: WorkspaceServiceRole,
    session: AsyncDBSession,
    request: TracecatQueryRequest,
) -> TracecatQueryResponse:
    """Query endpoint for Tracecat workflows.

    This endpoint is designed to be called from workflow actions
    to retrieve data from Base Camp.
    """
    service = TracecatIntegrationService(session, role)
    return await service.query_from_workflow(request)
