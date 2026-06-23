"""
app.workers.processing — NATS pull consumer for file.uploaded events.

Subscribes to the FILENEST_EVENTS stream on the `filenest.*.*.file.uploaded`
filter subject using a durable pull consumer named "processing-workers". Each
message contains a JSON payload with file_id; the org_id and project_id are
parsed from the NATS subject.

Up to `max_concurrent` files are processed in parallel via an asyncio.Semaphore.
Messages are ack'd after PipelineExecutor.run() completes (success or failure)
so the file is never stuck in processing state due to a worker crash — the NATS
server re-delivers to another replica after the ack_wait timeout.

Usage:
    from app.workers.processing import ProcessingWorker
    worker = ProcessingWorker()
    task = worker.start()          # returns asyncio.Task
    task.cancel(); await task      # graceful shutdown
"""
import asyncio
import json

import nats.js.errors

from app.core.logging import get_logger
from app.core.nats import get_js
from app.core.config import settings
from app.processing.pipeline import PipelineExecutor

logger = get_logger(__name__)

_CONSUMER_DURABLE = "processing-workers"
_FETCH_BATCH = 10
_FETCH_TIMEOUT = 5.0   # seconds to wait for NATS to return a batch


class ProcessingWorker:
    """
    Durable pull consumer that runs PipelineExecutor for each file.uploaded event.

    Args:
        max_concurrent: Maximum number of files being processed simultaneously.
                        Each in-flight file holds a DB session + storage connection.
    """

    def __init__(self, *, max_concurrent: int = 20) -> None:
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._executor = PipelineExecutor()

    def start(self) -> asyncio.Task:
        """Spawn the worker as a named asyncio.Task and return it."""
        return asyncio.create_task(self._run(), name="processing-worker")

    async def _run(self) -> None:
        js = get_js()
        logger.info("processing_worker.starting", consumer=_CONSUMER_DURABLE)

        _filter = "filenest.*.*.file.uploaded"
        try:
            psub = await js.pull_subscribe(
                subject=_filter,
                durable=_CONSUMER_DURABLE,
                stream=settings.nats_stream_name,
            )
        except Exception as exc:
            logger.error("processing_worker.subscribe_failed", error=str(exc))
            return

        logger.info("processing_worker.started", consumer=_CONSUMER_DURABLE)

        tasks: set[asyncio.Task] = set()

        while True:
            try:
                msgs = await psub.fetch(_FETCH_BATCH, timeout=_FETCH_TIMEOUT)
            except nats.js.errors.TimeoutError:
                # Normal — empty queue. Reap any finished tasks before looping.
                tasks = {t for t in tasks if not t.done()}
                continue
            except asyncio.CancelledError:
                logger.info("processing_worker.stopping")
                # Wait for in-flight processing to complete before exit.
                if tasks:
                    await asyncio.gather(*tasks, return_exceptions=True)
                return
            except Exception as exc:
                logger.error("processing_worker.fetch_error", error=str(exc))
                await asyncio.sleep(2)
                continue

            for msg in msgs:
                task = asyncio.create_task(self._handle(msg))
                tasks.add(task)
                task.add_done_callback(tasks.discard)

            tasks = {t for t in tasks if not t.done()}

    async def _handle(self, msg) -> None:
        """Process one NATS message under the concurrency semaphore."""
        async with self._semaphore:
            try:
                payload = json.loads(msg.data.decode())
                file_id: str = payload["file_id"]

                # Subject format: filenest.<org_id>.<project_id>.file.uploaded
                parts = msg.subject.split(".")
                organization_id = parts[1]
                project_id = parts[2]

                logger.info(
                    "processing_worker.received",
                    file_id=file_id,
                    organization_id=organization_id,
                    project_id=project_id,
                )

                await self._executor.run(file_id, organization_id, project_id)
                await msg.ack()

                logger.info(
                    "processing_worker.processed",
                    file_id=file_id,
                    organization_id=organization_id,
                    project_id=project_id,
                )
            except Exception as exc:
                logger.error(
                    "processing_worker.handle_error",
                    subject=msg.subject,
                    error=str(exc),
                )
                # Nak so NATS re-delivers to another worker after backoff.
                try:
                    await msg.nak()
                except Exception:
                    pass
