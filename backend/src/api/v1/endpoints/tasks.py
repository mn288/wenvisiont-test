from fastapi import APIRouter, Header, HTTPException, Request
from pydantic import BaseModel

from core.config import settings
from services.crew import CrewService
from services.infrastructure import InfrastructureService

router = APIRouter()
crew_service = CrewService()
infrastructure_service = InfrastructureService()


class TaskPayload(BaseModel):
    agent_name: str
    thread_id: str
    payload: str  # Input data
    created_at: str
    queue: str


@router.post("/execute")
async def execute_task(
    task_data: TaskPayload,
    request: Request,
    x_cloudtasks_queue: str = Header(None),
):
    """
    Webhook handler for Cloud Tasks execution.
    Secured by OIDC token validation (handled by Cloud Run IAM or internal middleware).
    """
    # 1. Verification
    # In Cloud Run, OIDC is handled at the ingress (Load Balancer/Service)
    # We can also check the Queue header to ensure it's from Cloud Tasks
    if settings.CLOUD_TASKS_ENABLED and not x_cloudtasks_queue:
        # If strict security is needed, we could block here.
        # For now, allow internal calls or testing.
        pass

    # 2. Setup Context
    thread_id = task_data.thread_id
    agent_name = task_data.agent_name

    # Initialize Infra
    infra_config = infrastructure_service.get_or_create_infrastructure(thread_id)

    # 3. Execution
    # We reconstruct a minimal Task object
    import uuid

    from models.state import AgentTask

    current_task = AgentTask(
        id=str(uuid.uuid4()),
        type="crew",
        name=agent_name,
        input_data=task_data.payload,
        assigned_to=agent_name,
    )

    try:
        result = await crew_service.execute_task(
            task=current_task, context=f"Async execution from queue {task_data.queue}", infra=infra_config
        )

        # 4. Result Handling
        # Since the graph execution has already "moved on" or "paused",
        # we need to decide how to persist this result.
        #
        # A) Update LangGraph State (requires checkpointer access)
        # B) Log to Database/History directly
        #
        # For this phase, we assume the `crew_service` or underlying DB calls
        # persist the "AgentResult" to the history table.
        # The frontend/orchestrator would need to poll history.

        return {"status": "success", "result": result.summary}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
