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
from app.core.services.embeddings import EmbeddingsService
from app.api.services.plot import PlotService


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

        # Re-fetch with artifacts loaded to avoid lazy loading issues
        statement = (
            select(Project)
            .where(Project.id == project.id)
            .options(selectinload(Project.artifacts))
        )
        result = await self.session.exec(statement)
        return result.first()

    async def get_project(self, project_id: uuid.UUID) -> Optional[Project]:
        statement = (
            select(Project)
            .where(Project.id == project_id)
            .options(selectinload(Project.artifacts))
        )
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

        # Re-fetch with artifacts loaded
        statement = (
            select(Project)
            .where(Project.id == project_id)
            .options(selectinload(Project.artifacts))
        )
        result = await self.session.exec(statement)
        return result.first()

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

            # 4. Extract Chapters using Robust Flow (TOC -> AI -> Regex)
            # Pass both content (for fallback) and storage_path (for TOC/EPUB)
            try:
                extracted_data = await file_service.extract_chapters_with_new_flow(
                    content=text_content,
                    book_type=(
                        project_type.value
                        if hasattr(project_type, "value")
                        else "entertainment"
                    ),
                    original_filename=file.filename or "unknown",
                    storage_path=remote_path,
                )
            except Exception as e:
                print(f"[PROJECT UPLOAD] Extraction failed: {e}")
                # Fallback to empty list or re-raise?
                # For now, let's log and proceed with whatever we have or fail.
                # Since this is the core value add, we should probably fail if extraction completely dies.
                raise e

            # 5. Create Book with source_mode='creator' for RAG integration
            # This allows Creator mode to use the same RAG/embedding pipeline as Explorer mode
            from app.books.models import Book as BookModel, Chapter as ChapterModel

            book = BookModel(
                title=(
                    os.path.splitext(file.filename)[0].replace("_", " ").title()
                    if file.filename
                    else "New Book"
                ),
                user_id=user_id,
                book_type=(
                    project_type.value
                    if hasattr(project_type, "value")
                    else "entertainment"
                ),
                source_mode="creator",  # Mark as Creator mode book (won't show in Explorer)
                status="ready",
                description=input_prompt or f"Uploaded from {file.filename}",
                original_file_storage_path=remote_path,
            )
            self.session.add(book)
            await self.session.commit()
            await self.session.refresh(book)

            # 6. Create Project and link to book
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
                book_id=book.id,  # Link project to book for RAG access
                pipeline_steps=["plot", "chapters", "script"],
                current_step="chapters",
                input_prompt=input_prompt or f"Uploaded from {file.filename}",
            )
            self.session.add(project)
            await self.session.commit()
            await self.session.refresh(project)

            # Update book with project_id (bi-directional link)
            book.project_id = project.id
            self.session.add(book)
            await self.session.commit()

            # 7. Create Chapters in Book (for RAG) AND Artifacts in Project
            try:
                chapters = []
                structure_type = "flat"

                # Standardize output (Handle Sections vs Flat Chapters)
                if extracted_data and isinstance(extracted_data, list):
                    first_item = extracted_data[0] if extracted_data else {}

                    if "chapters" in first_item:
                        # It's a list of Sections
                        structure_type = "hierarchical"
                        for section in extracted_data:
                            section_chapters = section.get("chapters", [])
                            # Add section metadata to chapters if needed?
                            # For now, just flatten them as requested by Project structure
                            chapters.extend(section_chapters)
                    else:
                        # It's a flat list of Chapters
                        chapters = extracted_data

                print(
                    f"[PROJECT UPLOAD] Creating {len(chapters)} chapters + artifacts..."
                )

                for idx, chapter in enumerate(chapters):
                    chapter_title = chapter.get("title", f"Chapter {idx+1}")
                    chapter_content = chapter.get("content", "")
                    chapter_number = chapter.get("number", idx + 1)
                    chapter_summary = chapter.get("summary", "")

                    # Create Chapter in Book table (for RAG/embeddings)
                    book_chapter = ChapterModel(
                        book_id=book.id,
                        title=chapter_title,
                        content=chapter_content,
                        chapter_number=chapter_number,
                        summary=chapter_summary,
                    )
                    self.session.add(book_chapter)
                    await self.session.flush()  # Flush to get ID

                    # Generate embeddings for the chapter (RAG)
                    try:
                        embeddings_service = EmbeddingsService(self.session)
                        await embeddings_service.create_chapter_embeddings(
                            book_chapter.id, chapter_content
                        )
                        print(
                            f"[PROJECT UPLOAD] Generated embeddings for chapter {chapter_number}"
                        )
                    except Exception as e:
                        print(
                            f"[PROJECT UPLOAD] Error generating embeddings for chapter {chapter_number}: {e}"
                        )

                    # Create Artifact in Project (for UI display)
                    # Include the actual chapter_id from books.chapters table for API calls
                    artifact = Artifact(
                        project_id=project.id,
                        artifact_type=ArtifactType.CHAPTER.value,
                        version=1,
                        content={
                            "title": chapter_title,
                            "content": chapter_content,
                            "chapter_number": chapter_number,
                            "summary": chapter_summary,
                            "chapter_id": str(
                                book_chapter.id
                            ),  # Actual Chapter ID for API calls
                        },
                        generation_metadata={
                            "source": "upload_extraction",
                            "original_structure": structure_type,
                            "section_title": chapter.get(
                                "section_title"
                            ),  # if available
                            "book_chapter_id": str(
                                book_chapter.id
                            ),  # Also store in metadata
                        },
                    )
                    self.session.add(artifact)

                # Update book's total_chapters
                book.total_chapters = len(chapters)
                self.session.add(book)

                await self.session.commit()
                print(f"[PROJECT UPLOAD] {len(chapters)} chapters + artifacts saved.")

                # 8. Generate Plot Overview if input_prompt is provided
                if input_prompt:
                    try:
                        print(
                            f"[PROJECT UPLOAD] Generating plot overview with prompt: {input_prompt[:50]}..."
                        )
                        plot_service = PlotService(self.session)
                        project_type_str = (
                            project_type.value
                            if hasattr(project_type, "value")
                            else str(project_type)
                        )

                        await plot_service.generate_plot_from_prompt(
                            user_id=user_id,
                            project_id=project.id,
                            input_prompt=input_prompt,
                            project_type=project_type_str,
                            book_id=book.id,
                        )
                        print("[PROJECT UPLOAD] Plot generation successful.")
                    except Exception as e:
                        print(f"[PROJECT UPLOAD] Plot generation failed: {e}")
                        # Continue without failing the whole upload
            except Exception as e:
                print(f"[PROJECT UPLOAD] Error creating artifacts: {e}")
                # Use verify_partial_success or raise?
                # If we made the project but failed artifacts, user sees empty project.
                # Better to raise so FE gets 500 and user knows to retry.
                raise e

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
