"""
Batch Operations API Router
CSV import/export, bulk operations
"""

from fastapi import APIRouter, Depends, HTTPException, File, UploadFile, Query
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import List
import asyncio

from services.batch_operations_service import (
    BatchOperationService,
    get_batch_service,
)

router = APIRouter(prefix="/api/batch", tags=["batch"])


async def get_db() -> AsyncIOMotorDatabase:
    """Get database instance."""
    from core.pipeline import get_database

    result = get_database()
    if asyncio.iscoroutinefunction(get_database):
        return await result
    return result


@router.post("/import-csv")
async def import_csv(
    user_id: str,
    file: UploadFile = File(...),
    skip_duplicates: bool = Query(True),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Import tasks from CSV file."""
    try:
        service = get_batch_service(db)

        # Read file
        content = await file.read()
        csv_content = content.decode("utf-8")

        # Validate CSV
        is_valid, errors = await service.validate_csv(csv_content)
        if not is_valid:
            raise HTTPException(
                status_code=400,
                detail={"validation_errors": errors}
            )

        # Import
        result = await service.import_tasks_from_csv(
            user_id=user_id,
            csv_content=csv_content,
            skip_duplicates=skip_duplicates,
        )

        return {
            "status": "success",
            **result,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/export-csv")
async def export_csv(
    user_id: str,
    domain: str = Query(None),
    status: str = Query(None),
    priority: str = Query(None),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Export tasks to CSV."""
    try:
        service = get_batch_service(db)

        filters = {}
        if domain:
            filters["domain"] = domain
        if status:
            filters["status"] = status
        if priority:
            filters["priority"] = priority

        csv_content = await service.export_tasks_to_csv(
            user_id=user_id,
            filters=filters if filters else None,
        )

        return {
            "status": "success",
            "format": "csv",
            "data": csv_content,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/bulk-update")
async def bulk_update(
    user_id: str,
    task_ids: List[str],
    updates: dict,
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Bulk update tasks."""
    try:
        service = get_batch_service(db)

        result = await service.bulk_update_tasks(
            user_id=user_id,
            task_ids=task_ids,
            updates=updates,
        )

        return {
            "status": "success",
            **result,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/bulk-delete")
async def bulk_delete(
    user_id: str,
    task_ids: List[str],
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Bulk delete tasks."""
    try:
        service = get_batch_service(db)

        result = await service.bulk_delete_tasks(
            user_id=user_id,
            task_ids=task_ids,
        )

        return {
            "status": "success",
            **result,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/job-status/{batch_id}")
async def get_batch_status(
    batch_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Get batch job status."""
    try:
        service = get_batch_service(db)

        job = await service.get_batch_job_status(batch_id)

        if not job:
            raise HTTPException(status_code=404, detail="Batch job not found")

        return {
            "status": "success",
            "job": job,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/jobs")
async def get_user_batch_jobs(
    user_id: str,
    limit: int = Query(20, ge=1, le=100),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Get user's batch jobs."""
    try:
        service = get_batch_service(db)

        jobs = await service.get_user_batch_jobs(user_id, limit)

        return {
            "status": "success",
            "count": len(jobs),
            "jobs": jobs,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/validate-csv")
async def validate_csv(
    file: UploadFile = File(...),
):
    """Validate CSV structure."""
    try:
        content = await file.read()
        csv_content = content.decode("utf-8")

        from services.batch_operations_service import BatchOperationService
        service = BatchOperationService(None)  # No DB needed for validation

        is_valid, errors = await service.validate_csv(csv_content)

        return {
            "status": "success",
            "is_valid": is_valid,
            "errors": errors if not is_valid else [],
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
