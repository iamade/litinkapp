import uuid
from typing import List, Optional
from sqlmodel import select
from app.projects.models import (
    Project,
    Artifact,
    ProjectType,
    WorkflowMode,
    ProjectStatus,
)
from app.projects.schemas import (
    ProjectCreate,
    ProjectUpdate,
    IntentAnalysisRequest,
    IntentAnalysisResult,
)


class IntentService:
    @staticmethod
    async def analyze_intent(
        request: IntentAnalysisRequest, user_is_explorer: bool
    ) -> IntentAnalysisResult:
        # Simple heuristic based logic for now.
        # In production this would call an LLM.

        prompt_lower = request.prompt.lower()
        file_ext = request.file_name.split(".")[-1].lower() if request.file_name else ""

        intent = ProjectType.ENTERTAINMENT
        pipeline = ["plot", "script", "video"]
        mode = WorkflowMode.EXPLORER if user_is_explorer else WorkflowMode.CREATOR
        reasoning = "Defaulting to entertainment."

        if (
            "training" in prompt_lower
            or "course" in prompt_lower
            or "onboarding" in prompt_lower
        ):
            intent = ProjectType.TRAINING
            pipeline = ["summary", "script", "video"]
            reasoning = "Detected educational keywords."
        elif "advert" in prompt_lower or "commercial" in prompt_lower:
            intent = ProjectType.ADVERT
            pipeline = ["script", "storyboard", "video"]
            reasoning = "Detected advertising keywords."
        elif "music" in prompt_lower:
            intent = ProjectType.MUSIC_VIDEO
            pipeline = ["lyrics", "audio", "video"]
            reasoning = "Detected music keywords."

        return IntentAnalysisResult(
            primary_intent=intent,
            confidence=0.85,
            reasoning=reasoning,
            suggested_mode=mode,
            detected_pipeline=pipeline,
        )


from sqlmodel.ext.asyncio.session import AsyncSession


class ProjectService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_project(
        self, project_in: ProjectCreate, user_id: uuid.UUID
    ) -> Project:
        project = Project(
            **project_in.model_dump(),
            user_id=user_id,
            status=ProjectStatus.DRAFT,
            pipeline_steps=["plot", "script"],  # Placeholder default
            current_step="plot"
        )
        self.session.add(project)
        await self.session.commit()
        await self.session.refresh(project)
        return project

    async def get_project(self, project_id: uuid.UUID) -> Optional[Project]:
        statement = select(Project).where(Project.id == project_id)
        result = await self.session.exec(statement)
        return result.first()

    async def get_user_projects(self, user_id: uuid.UUID) -> List[Project]:
        statement = (
            select(Project)
            .where(Project.user_id == user_id)
            .order_by(Project.updated_at.desc())
        )
        result = await self.session.exec(statement)
        return result.all()

    async def update_project(
        self, project_id: uuid.UUID, project_update: ProjectUpdate
    ) -> Optional[Project]:
        project = await self.get_project(project_id)
        if not project:
            return None

        update_data = project_update.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(project, key, value)

        self.session.add(project)
        await self.session.commit()
        await self.session.refresh(project)
        return project

    async def delete_project(self, project_id: uuid.UUID) -> bool:
        project = await self.get_project(project_id)
        if not project:
            return False
        await self.session.delete(project)
        await self.session.commit()
        return True
