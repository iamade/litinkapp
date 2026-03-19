import asyncio
import os
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


def _extract_text_content(temp_path: str, suffix: str) -> str:
    """Synchronous extractor used via asyncio.to_thread to avoid event-loop stalls."""
    import fitz

    text_content = ""
    lower_suffix = (suffix or "").lower()

    if lower_suffix == ".pdf":
        doc = fitz.open(temp_path)
        try:
            for page in doc:
                text_content += page.get_text() + "\n"
        finally:
            doc.close()
        return text_content

    if lower_suffix in [".txt", ".docx"]:
        try:
            doc = fitz.open(temp_path)
            try:
                for page in doc:
                    text_content += page.get_text() + "\n"
                return text_content
            finally:
                doc.close()
        except Exception:
            with open(temp_path, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()

    try:
        doc = fitz.open(temp_path)
        try:
            for page in doc:
                text_content += page.get_text() + "\n"
        finally:
            doc.close()
    except Exception:
        return ""

    return text_content


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


async def _update_project_progress(
    session: AsyncSession,
    project_id: uuid.UUID,
    **kwargs,
) -> None:
    """Update upload progress fields on a project record."""
    stmt = select(Project).where(Project.id == project_id)
    result = await session.exec(stmt)
    project = result.first()
    if not project:
        return
    for key, value in kwargs.items():
        setattr(project, key, value)
    session.add(project)
    await session.commit()


async def _process_project_upload_background(
    project_id: str,
    book_id: str,
    user_id: str,
    file_data: list,
    project_type_value: str,
    input_prompt: Optional[str],
    is_multi_script: bool,
    consultation_config: Optional[dict],
) -> None:
    """Background task: extract text, parse chapters, generate embeddings, save artifacts."""
    from app.core.database import async_session
    from app.core.services.file import FileService
    from app.core.services.embeddings import EmbeddingsService
    from app.books.models import Book as BookModel, Chapter as ChapterModel
    from app.api.services.plot import PlotService

    project_uuid = uuid.UUID(project_id)
    book_uuid = uuid.UUID(book_id)
    user_uuid = uuid.UUID(user_id)

    async with async_session() as session:
        try:
            file_service = FileService()

            # Stage: parsing - extract text from temp files
            await _update_project_progress(
                session, project_uuid, upload_stage="parsing", upload_progress=10
            )

            file_data_list = []
            for fd in file_data:
                suffix = os.path.splitext(fd["filename"])[1] if fd["filename"] else ""
                try:
                    text_content = await asyncio.to_thread(
                        _extract_text_content, fd["temp_path"], suffix
                    )
                except Exception as e:
                    print(f"[BG UPLOAD] Text extraction failed for {fd['filename']}: {e}")
                    text_content = ""
                file_data_list.append(
                    {
                        "filename": fd["filename"],
                        "text_content": text_content,
                        "file_url": fd["file_url"],
                        "temp_path": fd["temp_path"],
                    }
                )

            await _update_project_progress(
                session, project_uuid, upload_stage="structuring", upload_progress=20
            )

            if is_multi_script:
                total = len(file_data_list)
                await _update_project_progress(
                    session,
                    project_uuid,
                    upload_stage="embeddings",
                    upload_progress=25,
                    upload_total_chapters=total,
                )

                for idx, fd in enumerate(file_data_list):
                    script_title = (
                        os.path.splitext(fd["filename"])[0].replace("_", " ").title()
                    )
                    book_chapter = ChapterModel(
                        book_id=book_uuid,
                        title=script_title,
                        content=fd["text_content"],
                        chapter_number=idx + 1,
                        summary=f"Script file: {fd['filename']}",
                    )
                    session.add(book_chapter)
                    await session.flush()

                    try:
                        embeddings_service = EmbeddingsService(session)
                        await embeddings_service.create_chapter_embeddings(
                            book_chapter.id, fd["text_content"]
                        )
                    except Exception as e:
                        print(f"[BG UPLOAD] Embeddings error for script {idx + 1}: {e}")

                    artifact = Artifact(
                        project_id=project_uuid,
                        artifact_type=ArtifactType.CHAPTER.value,
                        version=1,
                        content={
                            "title": script_title,
                            "content": fd["text_content"],
                            "chapter_number": idx + 1,
                            "summary": f"Uploaded script from {fd['filename']}",
                            "chapter_id": str(book_chapter.id),
                            "original_filename": fd["filename"],
                        },
                        generation_metadata={
                            "source": "upload_multi_script",
                            "original_structure": "script_file",
                            "book_chapter_id": str(book_chapter.id),
                            "source_files": [fd["filename"]],
                        },
                        source_file_url=fd["file_url"],
                        is_script=True,
                        script_order=idx + 1,
                        content_type_label="Script",
                    )
                    session.add(artifact)

                    chapters_done = idx + 1
                    progress_pct = 25 + int((chapters_done / total) * 65)
                    await _update_project_progress(
                        session,
                        project_uuid,
                        upload_chapters_processed=chapters_done,
                        upload_progress=progress_pct,
                    )

                # Save consultation artifact if provided
                if consultation_config and consultation_config.get("consultation_data"):
                    consultation_artifact = Artifact(
                        project_id=project_uuid,
                        artifact_type=ArtifactType.DOCUMENT_SUMMARY.value,
                        version=1,
                        content={
                            "type": "cinematic_universe_consultation",
                            "consultation": consultation_config.get(
                                "consultation_data", {}
                            ).get("agreements", {}),
                            "conversation": consultation_config.get(
                                "consultation_data", {}
                            ).get("conversation", []),
                            "agreements": consultation_config.get(
                                "consultation_data", {}
                            ).get("agreements", {}),
                        },
                        generation_metadata={
                            "source": "ai_consultation_modal",
                            "universe_name": consultation_config.get("universe_name"),
                            "content_terminology": consultation_config.get(
                                "content_terminology"
                            ),
                        },
                    )
                    session.add(consultation_artifact)

                stmt = select(BookModel).where(BookModel.id == book_uuid)
                result = await session.exec(stmt)
                book = result.first()
                if book:
                    book.total_chapters = len(file_data_list)
                    session.add(book)
                await session.commit()

            else:
                # Single file: LLM chapter extraction
                all_text = file_data_list[0]["text_content"]

                try:
                    extracted_data = await file_service.extract_chapters_with_new_flow(
                        content=all_text,
                        book_type=project_type_value,
                        original_filename=file_data_list[0]["filename"],
                        storage_path=file_data_list[0]["file_url"],
                    )
                except Exception as e:
                    print(f"[BG UPLOAD] Chapter extraction failed: {e}")
                    raise e

                chapters = []
                structure_type = "flat"
                if extracted_data and isinstance(extracted_data, list):
                    first_item = extracted_data[0] if extracted_data else {}
                    if "chapters" in first_item:
                        structure_type = "hierarchical"
                        for section in extracted_data:
                            chapters.extend(section.get("chapters", []))
                    else:
                        chapters = extracted_data

                total = len(chapters)
                await _update_project_progress(
                    session,
                    project_uuid,
                    upload_stage="embeddings",
                    upload_progress=30,
                    upload_total_chapters=total,
                )

                file_names = [fd["filename"] for fd in file_data_list]

                for idx, chapter in enumerate(chapters):
                    chapter_title = chapter.get("title", f"Chapter {idx + 1}")
                    chapter_content = chapter.get("content", "")
                    chapter_number = chapter.get("number", idx + 1)
                    chapter_summary = chapter.get("summary", "")

                    book_chapter = ChapterModel(
                        book_id=book_uuid,
                        title=chapter_title,
                        content=chapter_content,
                        chapter_number=chapter_number,
                        summary=chapter_summary,
                    )
                    session.add(book_chapter)
                    await session.flush()

                    try:
                        embeddings_service = EmbeddingsService(session)
                        await embeddings_service.create_chapter_embeddings(
                            book_chapter.id, chapter_content
                        )
                    except Exception as e:
                        print(
                            f"[BG UPLOAD] Embeddings error for chapter {chapter_number}: {e}"
                        )

                    artifact = Artifact(
                        project_id=project_uuid,
                        artifact_type=ArtifactType.CHAPTER.value,
                        version=1,
                        content={
                            "title": chapter_title,
                            "content": chapter_content,
                            "chapter_number": chapter_number,
                            "summary": chapter_summary,
                            "chapter_id": str(book_chapter.id),
                        },
                        generation_metadata={
                            "source": "upload_extraction",
                            "original_structure": structure_type,
                            "section_title": chapter.get("section_title"),
                            "book_chapter_id": str(book_chapter.id),
                            "source_files": file_names,
                        },
                    )
                    session.add(artifact)

                    chapters_done = idx + 1
                    progress_pct = 30 + int((chapters_done / total) * 55)
                    await _update_project_progress(
                        session,
                        project_uuid,
                        upload_chapters_processed=chapters_done,
                        upload_progress=progress_pct,
                    )

                stmt = select(BookModel).where(BookModel.id == book_uuid)
                result = await session.exec(stmt)
                book = result.first()
                if book:
                    book.total_chapters = len(chapters)
                    session.add(book)
                await session.commit()

                # Generate plot if input_prompt provided
                await _update_project_progress(
                    session, project_uuid, upload_stage="finalizing", upload_progress=87
                )
                if input_prompt:
                    try:
                        plot_service = PlotService(session)
                        await plot_service.generate_plot_from_prompt(
                            user_id=user_uuid,
                            project_id=project_uuid,
                            input_prompt=input_prompt,
                            project_type=project_type_value,
                            book_id=book_uuid,
                        )
                    except Exception as e:
                        print(f"[BG UPLOAD] Plot generation failed: {e}")

            await _update_project_progress(
                session,
                project_uuid,
                upload_status="completed",
                upload_stage="finalizing",
                upload_progress=100,
            )
            print(f"[BG UPLOAD] Project {project_id} processing complete.")

        except Exception as e:
            print(f"[BG UPLOAD] Processing failed for project {project_id}: {e}")
            try:
                await session.rollback()
                await _update_project_progress(
                    session,
                    project_uuid,
                    upload_status="failed",
                    upload_error=str(e)[:500],
                )
            except Exception as err:
                print(f"[BG UPLOAD] Could not save error status: {err}")
        finally:
            for fd in file_data:
                temp_path = fd.get("temp_path", "")
                if temp_path and os.path.exists(temp_path):
                    try:
                        os.unlink(temp_path)
                    except OSError:
                        pass


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

    async def create_project_shell(
        self,
        files: List[UploadFile],
        user_id: uuid.UUID,
        project_type: ProjectType = ProjectType.ENTERTAINMENT,
        input_prompt: Optional[str] = None,
        consultation_config: Optional[dict] = None,
    ) -> tuple:
        """Upload files to storage, create Book + Project shell, return (project, file_data, is_multi_script).

        File data contains {filename, file_url, temp_path} for each file.
        The caller is responsible for kicking off _process_project_upload_background.
        """
        import tempfile
        from app.core.services.file import FileService
        from app.books.models import Book as BookModel

        file_service = FileService()
        project_uuid = uuid.uuid4()  # used for storage paths

        file_data = []
        temp_paths = []

        for file in files:
            suffix = os.path.splitext(file.filename)[1] if file.filename else ""
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp:
                content = await file.read()
                temp.write(content)
                temp_path = temp.name
                temp_paths.append(temp_path)

            remote_path = f"users/{user_id}/projects/{project_uuid}/{file.filename}"
            try:
                file_url = await file_service.upload_file(temp_path, remote_path)
            except Exception as upload_err:
                for tp in temp_paths:
                    if os.path.exists(tp):
                        os.unlink(tp)
                raise ValueError(
                    f"Failed to upload file '{file.filename}' to storage: {upload_err}"
                ) from upload_err

            if not file_url:
                for tp in temp_paths:
                    if os.path.exists(tp):
                        os.unlink(tp)
                raise ValueError(
                    f"Failed to upload file '{file.filename}' to storage. Upload returned no URL."
                )

            file_data.append(
                {
                    "filename": file.filename or "unknown",
                    "file_url": file_url,
                    "temp_path": temp_path,
                }
            )

        is_multi_script = len(files) > 1
        primary_filename = file_data[0]["filename"]
        file_urls = [fd["file_url"] for fd in file_data]
        file_names = [fd["filename"] for fd in file_data]

        if len(files) == 1:
            project_title = (
                os.path.splitext(primary_filename)[0].replace("_", " ").title()
                if primary_filename
                else "New Project"
            )
        else:
            project_title = (
                f"Cinematic Universe - {os.path.splitext(primary_filename)[0].replace('_', ' ').title()} (+{len(files)-1} more)"
                if primary_filename
                else "Multi-Script Project"
            )

        book = BookModel(
            title=project_title,
            user_id=user_id,
            book_type=(
                project_type.value if hasattr(project_type, "value") else "entertainment"
            ),
            source_mode="creator",
            status="ready",
            description=(
                input_prompt
                if input_prompt
                else f"Project from {len(files)} file(s): {', '.join(file_names[:3])}{'...' if len(file_names) > 3 else ''}"
            ),
            original_file_storage_path=file_urls[0] if file_urls else None,
        )
        self.session.add(book)
        await self.session.commit()
        await self.session.refresh(book)

        if is_multi_script:
            pipeline_steps = ["consultation", "plot", "chapters", "script"]
            current_step = "consultation"
        else:
            pipeline_steps = ["plot", "chapters", "script"]
            current_step = "chapters"

        project = Project(
            title=project_title,
            user_id=user_id,
            project_type=project_type,
            workflow_mode=WorkflowMode.CREATOR,
            status=ProjectStatus.DRAFT,
            source_material_url=", ".join(file_urls),
            book_id=book.id,
            pipeline_steps=pipeline_steps,
            current_step=current_step,
            input_prompt=input_prompt if input_prompt else None,
            upload_status="processing",
            upload_stage="parsing",
            upload_progress=5,
        )
        self.session.add(project)
        await self.session.commit()
        await self.session.refresh(project)

        book.project_id = project.id
        self.session.add(book)
        await self.session.commit()

        return project, file_data, is_multi_script

    async def create_project_from_upload(
        self,
        files: List[UploadFile],
        user_id: uuid.UUID,
        project_type: ProjectType = ProjectType.ENTERTAINMENT,
        input_prompt: Optional[str] = None,
        consultation_config: Optional[dict] = None,
    ) -> Project:
        import tempfile
        import os
        from app.core.services.file import FileService

        file_service = FileService()
        project_uuid = uuid.uuid4()

        # Process all uploaded files - store individual file data
        file_data_list = []  # List of {filename, text_content, file_url, temp_path}
        temp_paths = []

        for file in files:
            # 1. Save uploaded file to temp
            suffix = os.path.splitext(file.filename)[1] if file.filename else ""
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp:
                content = await file.read()
                temp.write(content)
                temp_path = temp.name
                temp_paths.append(temp_path)

            # 2. Upload to storage using FileService
            remote_path = f"users/{user_id}/projects/{project_uuid}/{file.filename}"
            try:
                file_url = await file_service.upload_file(temp_path, remote_path)
            except Exception as upload_err:
                raise ValueError(
                    f"Failed to upload file '{file.filename}' to storage: {upload_err}"
                ) from upload_err

            if not file_url:
                raise ValueError(
                    f"Failed to upload file '{file.filename}' to storage. "
                    "Upload returned no URL."
                )

            # 3. Extract text off the event loop to reduce Gunicorn worker timeout risk
            try:
                text_content = await asyncio.to_thread(
                    _extract_text_content, temp_path, suffix
                )
            except Exception as e:
                print(f"[PROJECT UPLOAD] Could not extract text from {file.filename}: {e}")
                text_content = ""

            file_data_list.append(
                {
                    "filename": file.filename or "unknown",
                    "text_content": text_content,
                    "file_url": file_url,
                    "temp_path": temp_path,
                }
            )

        try:
            # Determine if this is a multi-script upload (Cinematic Universe Mode)
            is_multi_script = len(files) > 1

            # Use first file for primary reference
            primary_file = file_data_list[0]
            file_names = [f["filename"] for f in file_data_list]
            file_urls = [f["file_url"] for f in file_data_list]

            # Generate project title
            if len(files) == 1:
                project_title = (
                    os.path.splitext(primary_file["filename"])[0]
                    .replace("_", " ")
                    .title()
                    if primary_file["filename"]
                    else "New Project"
                )
            else:
                # Multi-file: use descriptive title indicating universe mode
                project_title = (
                    f"Cinematic Universe - {os.path.splitext(primary_file['filename'])[0].replace('_', ' ').title()} (+{len(files)-1} more)"
                    if primary_file["filename"]
                    else "Multi-Script Project"
                )

            # 5. Create Book with source_mode='creator' for RAG integration
            from app.books.models import Book as BookModel, Chapter as ChapterModel

            book = BookModel(
                title=project_title,
                user_id=user_id,
                book_type=(
                    project_type.value
                    if hasattr(project_type, "value")
                    else "entertainment"
                ),
                source_mode="creator",
                status="ready",
                description=(
                    input_prompt
                    if input_prompt
                    else f"Project from {len(files)} file(s): {', '.join(file_names[:3])}{'...' if len(file_names) > 3 else ''}"
                ),
                original_file_storage_path=file_urls[0] if file_urls else None,
            )
            self.session.add(book)
            await self.session.commit()
            await self.session.refresh(book)

            # 6. Create Project and link to book
            # For multi-script projects, add consultation step to pipeline
            if is_multi_script:
                pipeline_steps = ["consultation", "plot", "chapters", "script"]
                current_step = (
                    "consultation"  # Start with consultation for multi-scripts
                )
            else:
                pipeline_steps = ["plot", "chapters", "script"]
                current_step = "chapters"

            project = Project(
                title=project_title,
                user_id=user_id,
                project_type=project_type,
                workflow_mode=WorkflowMode.CREATOR,
                status=ProjectStatus.DRAFT,
                source_material_url=", ".join(file_urls),
                book_id=book.id,
                pipeline_steps=pipeline_steps,
                current_step=current_step,
                input_prompt=input_prompt if input_prompt else None,
            )
            self.session.add(project)
            await self.session.commit()
            await self.session.refresh(project)

            # Update book with project_id (bi-directional link)
            book.project_id = project.id
            self.session.add(book)
            await self.session.commit()

            # 7. Create Artifacts - DIFFERENT HANDLING FOR MULTI-SCRIPT vs SINGLE FILE
            if is_multi_script:
                # MULTI-SCRIPT MODE: Create one artifact per uploaded file
                print(
                    f"[PROJECT UPLOAD] Multi-script mode: Creating {len(file_data_list)} script artifacts..."
                )

                for idx, file_data in enumerate(file_data_list):
                    script_title = (
                        os.path.splitext(file_data["filename"])[0]
                        .replace("_", " ")
                        .title()
                    )

                    # Create Chapter in Book table (for RAG/embeddings)
                    book_chapter = ChapterModel(
                        book_id=book.id,
                        title=script_title,
                        content=file_data["text_content"],
                        chapter_number=idx + 1,
                        summary=f"Script file: {file_data['filename']}",
                    )
                    self.session.add(book_chapter)
                    await self.session.flush()  # Flush to get ID

                    # Generate embeddings for the script (RAG)
                    try:
                        embeddings_service = EmbeddingsService(self.session)
                        await embeddings_service.create_chapter_embeddings(
                            book_chapter.id, file_data["text_content"]
                        )
                        print(
                            f"[PROJECT UPLOAD] Generated embeddings for script {idx + 1}"
                        )
                    except Exception as e:
                        print(
                            f"[PROJECT UPLOAD] Error generating embeddings for script {idx + 1}: {e}"
                        )

                    # Create Artifact in Project with SCRIPT-SPECIFIC FIELDS
                    artifact = Artifact(
                        project_id=project.id,
                        artifact_type=ArtifactType.CHAPTER.value,
                        version=1,
                        content={
                            "title": script_title,
                            "content": file_data["text_content"],
                            "chapter_number": idx + 1,
                            "summary": f"Uploaded script from {file_data['filename']}",
                            "chapter_id": str(book_chapter.id),
                            "original_filename": file_data["filename"],
                        },
                        generation_metadata={
                            "source": "upload_multi_script",
                            "original_structure": "script_file",
                            "book_chapter_id": str(book_chapter.id),
                            "source_files": [file_data["filename"]],
                        },
                        # NEW FIELDS for script tracking
                        source_file_url=file_data["file_url"],
                        is_script=True,
                        script_order=idx + 1,
                        content_type_label="Script",  # Will be updated after consultation (Film/Episode/Part)
                    )
                    self.session.add(artifact)

                # Update book's total_chapters
                book.total_chapters = len(file_data_list)
                self.session.add(book)

                await self.session.commit()
                print(f"[PROJECT UPLOAD] {len(file_data_list)} script artifacts saved.")

                # Save consultation data if provided (multi-script mode)
                if consultation_config and consultation_config.get("consultation_data"):
                    consultation_artifact = Artifact(
                        project_id=project.id,
                        artifact_type=ArtifactType.DOCUMENT_SUMMARY.value,
                        version=1,
                        content={
                            "type": "cinematic_universe_consultation",
                            "consultation": consultation_config.get(
                                "consultation_data", {}
                            ).get("agreements", {}),
                            "conversation": consultation_config.get(
                                "consultation_data", {}
                            ).get("conversation", []),
                            "agreements": consultation_config.get(
                                "consultation_data", {}
                            ).get("agreements", {}),
                        },
                        generation_metadata={
                            "source": "ai_consultation_modal",
                            "universe_name": consultation_config.get("universe_name"),
                            "content_terminology": consultation_config.get(
                                "content_terminology"
                            ),
                        },
                    )
                    self.session.add(consultation_artifact)
                    await self.session.commit()
                    print(f"[PROJECT UPLOAD] Consultation data saved as artifact.")

            else:
                # SINGLE FILE MODE: Use existing chapter extraction logic
                all_text_content = file_data_list[0]["text_content"]

                try:
                    extracted_data = await file_service.extract_chapters_with_new_flow(
                        content=all_text_content,
                        book_type=(
                            project_type.value
                            if hasattr(project_type, "value")
                            else "entertainment"
                        ),
                        original_filename=primary_file["filename"],
                        storage_path=file_urls[0] if file_urls else "",
                    )
                except Exception as e:
                    print(f"[PROJECT UPLOAD] Extraction failed: {e}")
                    raise e

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
                            chapters.extend(section_chapters)
                    else:
                        # It's a flat list of Chapters
                        chapters = extracted_data

                print(
                    f"[PROJECT UPLOAD] Creating {len(chapters)} chapters + artifacts from single file..."
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
                    artifact = Artifact(
                        project_id=project.id,
                        artifact_type=ArtifactType.CHAPTER.value,
                        version=1,
                        content={
                            "title": chapter_title,
                            "content": chapter_content,
                            "chapter_number": chapter_number,
                            "summary": chapter_summary,
                            "chapter_id": str(book_chapter.id),
                        },
                        generation_metadata={
                            "source": "upload_extraction",
                            "original_structure": structure_type,
                            "section_title": chapter.get("section_title"),
                            "book_chapter_id": str(book_chapter.id),
                            "source_files": file_names,
                        },
                    )
                    self.session.add(artifact)

                # Update book's total_chapters
                book.total_chapters = len(chapters)
                self.session.add(book)

                await self.session.commit()
                print(f"[PROJECT UPLOAD] {len(chapters)} chapters + artifacts saved.")

                # 8. Generate Plot Overview if input_prompt is provided (single file mode only)
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

            # Re-fetch with artifacts
            statement = (
                select(Project)
                .where(Project.id == project.id)
                .options(selectinload(Project.artifacts))
            )
            project = (await self.session.exec(statement)).first()

            return project
        finally:
            # Clean up all temp files
            for temp_path in temp_paths:
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
