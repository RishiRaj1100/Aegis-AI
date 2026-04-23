"""
AegisAI - Batch Operations Service
Bulk import/export, CSV handling, data migrations, scheduled batch processing
"""

from __future__ import annotations

import csv
import io
import logging
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime
from enum import Enum

from motor.motor_asyncio import AsyncIOMotorDatabase

logger = logging.getLogger(__name__)


class BatchStatus(str, Enum):
    """Batch operation status."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"


class BatchOperationService:
    """
    Batch operations for bulk data management.

    Features:
    - CSV import/export
    - Bulk task creation
    - Data validation
    - Progress tracking
    - Error handling
    - Scheduled operations
    """

    def __init__(self, db: AsyncIOMotorDatabase):
        """Initialize with MongoDB."""
        self.db = db
        self.tasks_collection = db["tasks"]
        self.batch_jobs_collection = db["batch_jobs"]
        self.batch_errors_collection = db["batch_errors"]

    # ── Import Operations ─────────────────────────────────────────────────────

    async def import_tasks_from_csv(
        self,
        user_id: str,
        csv_content: str,
        skip_duplicates: bool = True,
    ) -> Dict[str, Any]:
        """
        Import tasks from CSV.

        Expected columns: goal, domain, priority, deadline (optional)
        """
        try:
            batch_job = {
                "user_id": user_id,
                "operation": "import_tasks",
                "status": BatchStatus.PROCESSING.value,
                "started_at": datetime.now(),
                "completed_at": None,
                "total_records": 0,
                "successful": 0,
                "failed": 0,
                "errors": [],
            }

            # Insert batch job
            result = await self.batch_jobs_collection.insert_one(batch_job)
            batch_id = str(result.inserted_id)

            # Parse CSV
            csv_file = io.StringIO(csv_content)
            reader = csv.DictReader(csv_file)

            rows = list(reader)
            batch_job["total_records"] = len(rows)

            # Process rows
            imported_tasks = []
            errors = []

            for idx, row in enumerate(rows):
                try:
                    # Validate required fields
                    if "goal" not in row or not row["goal"].strip():
                        errors.append({
                            "row": idx + 2,  # +2 for header and 1-based indexing
                            "error": "Missing required field: goal",
                            "data": row,
                        })
                        continue

                    goal = row["goal"].strip()

                    # Check for duplicates if enabled
                    if skip_duplicates:
                        existing = await self.tasks_collection.find_one({
                            "user_id": user_id,
                            "goal": goal,
                        })

                        if existing:
                            errors.append({
                                "row": idx + 2,
                                "error": "Duplicate task (skipped)",
                                "data": row,
                            })
                            continue

                    # Create task
                    task = {
                        "task_id": f"{user_id}_{datetime.now().timestamp()}_{idx}",
                        "user_id": user_id,
                        "goal": goal,
                        "domain": row.get("domain", "general"),
                        "priority": row.get("priority", "medium"),
                        "status": "pending",
                        "created_at": datetime.now(),
                    }

                    if "deadline" in row and row["deadline"].strip():
                        try:
                            task["deadline"] = datetime.fromisoformat(row["deadline"])
                        except ValueError:
                            pass

                    imported_tasks.append(task)
                    batch_job["successful"] += 1

                except Exception as e:
                    errors.append({
                        "row": idx + 2,
                        "error": str(e),
                        "data": row,
                    })
                    batch_job["failed"] += 1

            # Bulk insert
            if imported_tasks:
                await self.tasks_collection.insert_many(imported_tasks)

            # Log errors
            for error in errors:
                await self.batch_errors_collection.insert_one({
                    "batch_id": batch_id,
                    **error,
                })

            # Update batch job
            batch_job["completed_at"] = datetime.now()
            batch_job["status"] = (
                BatchStatus.COMPLETED.value if not errors
                else BatchStatus.PARTIAL.value if batch_job["successful"] > 0
                else BatchStatus.FAILED.value
            )

            await self.batch_jobs_collection.update_one(
                {"_id": result.inserted_id},
                {"$set": batch_job}
            )

            logger.info(
                f"Imported {batch_job['successful']} tasks, "
                f"{batch_job['failed']} failed for user {user_id}"
            )

            return {
                "batch_id": batch_id,
                "status": batch_job["status"],
                "total": batch_job["total_records"],
                "successful": batch_job["successful"],
                "failed": batch_job["failed"],
                "errors": errors[:10],  # Return first 10 errors
            }

        except Exception as e:
            logger.error(f"Error importing CSV: {e}")
            return {
                "batch_id": None,
                "status": BatchStatus.FAILED.value,
                "error": str(e),
            }

    # ── Export Operations ─────────────────────────────────────────────────────

    async def export_tasks_to_csv(
        self,
        user_id: str,
        filters: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Export tasks to CSV.

        Returns CSV content as string.
        """
        try:
            query = {"user_id": user_id}

            if filters:
                if "domain" in filters:
                    query["domain"] = filters["domain"]
                if "status" in filters:
                    query["status"] = filters["status"]
                if "priority" in filters:
                    query["priority"] = filters["priority"]

            tasks = await self.tasks_collection.find(query).to_list(None)

            # Build CSV
            output = io.StringIO()
            fieldnames = [
                "task_id",
                "goal",
                "domain",
                "priority",
                "status",
                "confidence_score",
                "created_at",
                "deadline",
            ]

            writer = csv.DictWriter(output, fieldnames=fieldnames)
            writer.writeheader()

            for task in tasks:
                writer.writerow({
                    "task_id": task.get("task_id", ""),
                    "goal": task.get("goal", ""),
                    "domain": task.get("domain", ""),
                    "priority": task.get("priority", ""),
                    "status": task.get("status", ""),
                    "confidence_score": task.get("confidence_score", ""),
                    "created_at": task.get("created_at", ""),
                    "deadline": task.get("deadline", ""),
                })

            csv_content = output.getvalue()
            output.close()

            logger.info(f"Exported {len(tasks)} tasks for user {user_id}")
            return csv_content

        except Exception as e:
            logger.error(f"Error exporting CSV: {e}")
            return ""

    # ── Bulk Operations ───────────────────────────────────────────────────────

    async def bulk_update_tasks(
        self,
        user_id: str,
        task_ids: List[str],
        updates: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Bulk update multiple tasks."""
        try:
            batch_job = {
                "user_id": user_id,
                "operation": "bulk_update",
                "status": BatchStatus.PROCESSING.value,
                "started_at": datetime.now(),
                "completed_at": None,
                "total_records": len(task_ids),
                "successful": 0,
                "failed": 0,
            }

            result = await self.batch_jobs_collection.insert_one(batch_job)
            batch_id = str(result.inserted_id)

            # Perform bulk update
            update_result = await self.tasks_collection.update_many(
                {
                    "user_id": user_id,
                    "task_id": {"$in": task_ids},
                },
                {"$set": {**updates, "updated_at": datetime.now()}}
            )

            batch_job["successful"] = update_result.modified_count
            batch_job["failed"] = len(task_ids) - update_result.modified_count
            batch_job["completed_at"] = datetime.now()
            batch_job["status"] = (
                BatchStatus.COMPLETED.value if batch_job["failed"] == 0
                else BatchStatus.PARTIAL.value
            )

            await self.batch_jobs_collection.update_one(
                {"_id": result.inserted_id},
                {"$set": batch_job}
            )

            logger.info(
                f"Bulk updated {batch_job['successful']} tasks "
                f"for user {user_id}"
            )

            return {
                "batch_id": batch_id,
                "status": batch_job["status"],
                "updated": batch_job["successful"],
                "failed": batch_job["failed"],
            }

        except Exception as e:
            logger.error(f"Error in bulk update: {e}")
            return {"error": str(e), "status": BatchStatus.FAILED.value}

    async def bulk_delete_tasks(
        self,
        user_id: str,
        task_ids: List[str],
    ) -> Dict[str, Any]:
        """Bulk delete multiple tasks."""
        try:
            batch_job = {
                "user_id": user_id,
                "operation": "bulk_delete",
                "status": BatchStatus.PROCESSING.value,
                "started_at": datetime.now(),
                "completed_at": None,
                "total_records": len(task_ids),
                "deleted": 0,
            }

            result = await self.batch_jobs_collection.insert_one(batch_job)
            batch_id = str(result.inserted_id)

            # Perform bulk delete
            delete_result = await self.tasks_collection.delete_many({
                "user_id": user_id,
                "task_id": {"$in": task_ids},
            })

            batch_job["deleted"] = delete_result.deleted_count
            batch_job["completed_at"] = datetime.now()
            batch_job["status"] = BatchStatus.COMPLETED.value

            await self.batch_jobs_collection.update_one(
                {"_id": result.inserted_id},
                {"$set": batch_job}
            )

            logger.info(f"Bulk deleted {batch_job['deleted']} tasks for user {user_id}")

            return {
                "batch_id": batch_id,
                "status": batch_job["status"],
                "deleted": batch_job["deleted"],
            }

        except Exception as e:
            logger.error(f"Error in bulk delete: {e}")
            return {"error": str(e), "status": BatchStatus.FAILED.value}

    # ── Batch Job Tracking ────────────────────────────────────────────────────

    async def get_batch_job_status(self, batch_id: str) -> Optional[Dict[str, Any]]:
        """Get status of batch job."""
        try:
            from bson import ObjectId

            job = await self.batch_jobs_collection.find_one({
                "_id": ObjectId(batch_id)
            })

            if job:
                # Get associated errors
                errors = await self.batch_errors_collection.find({
                    "batch_id": batch_id
                }).to_list(10)

                job["errors"] = errors
                return job

            return None

        except Exception as e:
            logger.error(f"Error getting batch status: {e}")
            return None

    async def get_user_batch_jobs(
        self,
        user_id: str,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """Get user's batch jobs."""
        try:
            jobs = await self.batch_jobs_collection.find({
                "user_id": user_id
            }).sort("started_at", -1).to_list(limit)

            return jobs

        except Exception as e:
            logger.error(f"Error getting batch jobs: {e}")
            return []

    # ── Data Validation ───────────────────────────────────────────────────────

    async def validate_csv(self, csv_content: str) -> Tuple[bool, List[str]]:
        """Validate CSV structure."""
        errors = []

        try:
            csv_file = io.StringIO(csv_content)
            reader = csv.DictReader(csv_file)

            if not reader.fieldnames:
                errors.append("CSV is empty or malformed")
                return False, errors

            required_fields = ["goal"]
            for field in required_fields:
                if field not in reader.fieldnames:
                    errors.append(f"Missing required column: {field}")

            # Check a few rows
            for idx, row in enumerate(reader):
                if idx >= 10:  # Check first 10 rows
                    break

                if not row.get("goal", "").strip():
                    errors.append(f"Row {idx + 2}: Missing goal value")

            return len(errors) == 0, errors

        except Exception as e:
            errors.append(f"CSV parsing error: {str(e)}")
            return False, errors


def get_batch_service(db: AsyncIOMotorDatabase) -> BatchOperationService:
    """Get batch operations service instance."""
    return BatchOperationService(db)
