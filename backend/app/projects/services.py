import uuid
from typing import List, Optional
from sqlmodel import select
from sqlalchemy.orm import selectinload
from app.projects.models import (
    Project,
    Artifact,
    ProjectType,
    WorkflowMode,
    ProjectStatus,
    ArtifactType,
)
from app.projects.schemas import (
    ProjectCreate,
    ProjectUpdate,
    IntentAnalysisRequest,
    IntentAnalysisResult,
)
from fastapi import UploadFile
from app.core.services.file import BookStructureDetector, FileService


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
            current_step="plot",
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
            .options(selectinload(Project.artifacts))
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

    async def create_project_from_upload(
        self,
        file: UploadFile,
        user_id: uuid.UUID,
        project_type: ProjectType = ProjectType.ENTERTAINMENT,
        input_prompt: Optional[str] = None,
    ) -> Project:
        import tempfile
        import os
        import fitz
        from app.core.services.file import FileService

        # 1. Save uploaded file to temp
        suffix = os.path.splitext(file.filename)[1] if file.filename else ""
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp:
            content = await file.read()
            temp.write(content)
            temp_path = temp.name

        try:
            # 2. Upload to storage using FileService
            file_service = FileService()
            # Generate a unique path
            remote_path = f"users/{user_id}/projects/{uuid.uuid4()}/{file.filename}"
            file_url = await file_service.upload_file(temp_path, remote_path)

            # 3. Extract text
            text_content = ""
            doc = fitz.open(temp_path)
            for page in doc:
                text_content += page.get_text() + "\n"
            doc.close()

            # 4. Detect Structure
            detector = BookStructureDetector()
            structure = detector.detect_structure(text_content)

            # 5. Create Project
            project = Project(
                title=(
                    os.path.splitext(file.filename)[0].replace("_", " ").title()
                    if file.filename
                    else "New Project"
                ),
                user_id=user_id,
                project_type=project_type,
                workflow_mode=WorkflowMode.CREATOR,
                status=ProjectStatus.DRAFT,
                source_material_url=file_url,
                pipeline_steps=["plot", "chapters", "script"],
                current_step="chapters",
                input_prompt=input_prompt or f"Uploaded from {file.filename}",
            )
            self.session.add(project)
            await self.session.commit()
            await self.session.refresh(project)

            # 6. Create Artifacts from Chapters
            chapters = structure.get("chapters", []) or []
            # If structure is hierarchical, flatten it
            if structure.get("sections"):
                for section in structure.get("sections"):
                    chapters.extend(section.get("chapters", []))

            for idx, chapter in enumerate(chapters):
                # Ensure content is not too large for JSONB if needed, but Artifact.content is JSON
                # Storing full chapter text in content dict
                artifact = Artifact(
                    project_id=project.id,
                    artifact_type=ArtifactType.CHAPTER,
                    version=1,
                    content={
                        "title": chapter.get("title", f"Chapter {idx+1}"),
                        "content": chapter.get("content", ""),
                        "chapter_number": chapter.get("number", idx + 1),
                    },
                    generation_metadata={
                        "source": "upload_extraction",
                        "original_structure": structure.get("structure_type", "flat"),
                    },
                )
                self.session.add(artifact)

            await self.session.commit()

            # Re-fetch with artifacts
            statement = (
                select(Project)
                .where(Project.id == project.id)
                .options(selectinload(Project.artifacts))
            )
            project = (await self.session.exec(statement)).first()

            return project
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
