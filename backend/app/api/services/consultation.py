"""
Consultation Service for Cinematic Universe Mode

This service handles the AI consultation phase where users can discuss
their multi-script projects before committing to generation.
"""

import uuid
import json
from typing import Dict, Any, List, Optional
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select
from sqlalchemy.orm import selectinload

from app.projects.models import Project, Artifact, ArtifactType
from app.core.services.openrouter import OpenRouterService
from app.core.model_config import ModelTier
from app.core.logging import get_logger

logger = get_logger()


class ConsultationService:
    """
    Handles the AI consultation phase for multi-script uploads.
    Analyzes scripts and provides recommendations for cinematic universe structure.
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.openrouter = OpenRouterService()

    async def analyze_scripts_for_cinematic_universe(
        self,
        project_id: uuid.UUID,
        user_prompt: str,
        user_tier: str = "free",
    ) -> Dict[str, Any]:
        """
        Analyze uploaded scripts and provide cinematic universe recommendations.

        Args:
            project_id: The project containing the uploaded scripts
            user_prompt: The user's creative direction/prompt
            user_tier: User's subscription tier for model selection

        Returns:
            Dict containing suggested names, phases, and AI commentary
        """
        # 1. Fetch project with artifacts
        statement = (
            select(Project)
            .where(Project.id == project_id)
            .options(selectinload(Project.artifacts))
        )
        result = await self.session.exec(statement)
        project = result.first()

        if not project:
            raise ValueError(f"Project {project_id} not found")

        # 2. Extract script summaries from artifacts
        script_summaries = []
        for artifact in project.artifacts:
            if artifact.artifact_type == ArtifactType.CHAPTER:
                content = artifact.content or {}
                script_summaries.append(
                    {
                        "filename": content.get(
                            "title", f"Script {len(script_summaries) + 1}"
                        ),
                        "summary": self._truncate_for_summary(
                            content.get("content", "")
                        ),
                        "artifact_id": str(artifact.id),
                        "source_file": artifact.source_file_url,
                    }
                )

        if not script_summaries:
            raise ValueError("No scripts found in project")

        # 3. Build the analysis prompt
        user_message = self._build_analysis_prompt(user_prompt, script_summaries)

        # 4. Call the LLM
        tier_enum = ModelTier(user_tier.lower()) if user_tier else ModelTier.FREE

        try:
            response = await self.openrouter.analyze_content(
                content=user_message,
                user_tier=tier_enum,
                analysis_type="cinematic_universe_analysis",
            )

            # 5. Parse the JSON response
            result_text = response.get("result", "")

            # Try to extract JSON from the response
            consultation_result = self._parse_llm_json_response(result_text)

            # 6. Store the consultation result in project metadata
            await self._store_consultation_result(project_id, consultation_result)

            return {
                "status": "success",
                "consultation": consultation_result,
                "model_used": response.get("model_used"),
                "scripts_analyzed": len(script_summaries),
            }

        except Exception as e:
            logger.error(f"Consultation analysis failed: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "scripts_analyzed": len(script_summaries),
            }

    def _truncate_for_summary(self, content: str, max_chars: int = 2000) -> str:
        """Truncate content for summary while preserving meaning."""
        if len(content) <= max_chars:
            return content

        # Try to find a sentence boundary
        truncated = content[:max_chars]
        last_period = truncated.rfind(".")
        if last_period > max_chars // 2:
            return truncated[: last_period + 1] + "..."
        return truncated + "..."

    def _build_analysis_prompt(
        self,
        user_prompt: str,
        script_summaries: List[Dict[str, Any]],
    ) -> str:
        """Build the prompt for cinematic universe analysis."""
        scripts_text = ""
        for i, script in enumerate(script_summaries, 1):
            scripts_text += f"\n\n--- SCRIPT {i}: {script['filename']} ---\n"
            scripts_text += script["summary"]

        prompt = f"""
USER'S CREATIVE DIRECTION:
{user_prompt}

NUMBER OF SCRIPTS: {len(script_summaries)}

SCRIPT CONTENTS:
{scripts_text}

Based on the above scripts and the user's creative direction, provide your cinematic universe analysis and recommendations in the specified JSON format.
"""
        return prompt

    def _parse_llm_json_response(self, response_text: str) -> Dict[str, Any]:
        """Extract and parse JSON from LLM response."""
        # Try direct JSON parse first
        try:
            return json.loads(response_text)
        except json.JSONDecodeError:
            pass

        # Try to find JSON in the response (often wrapped in markdown code blocks)
        import re

        # Look for ```json ... ``` blocks
        json_match = re.search(r"```(?:json)?\s*\n?([\s\S]*?)\n?```", response_text)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass

        # Look for { ... } block
        brace_match = re.search(r"\{[\s\S]*\}", response_text)
        if brace_match:
            try:
                return json.loads(brace_match.group(0))
            except json.JSONDecodeError:
                pass

        # Return a structured error response
        logger.warning(f"Could not parse LLM response as JSON: {response_text[:500]}")
        return {
            "suggested_names": ["Untitled Universe"],
            "ai_commentary": response_text,
            "parse_error": True,
        }

    async def _store_consultation_result(
        self,
        project_id: uuid.UUID,
        consultation_result: Dict[str, Any],
    ) -> None:
        """Store the consultation result as a project artifact."""
        artifact = Artifact(
            project_id=project_id,
            artifact_type=ArtifactType.DOCUMENT_SUMMARY,  # Using this type for consultation
            version=1,
            content={
                "type": "cinematic_universe_consultation",
                "consultation": consultation_result,
            },
            generated_by="ai",
            generation_metadata={
                "service": "consultation",
                "analysis_type": "cinematic_universe",
            },
        )
        self.session.add(artifact)
        await self.session.commit()

    async def accept_consultation(
        self,
        project_id: uuid.UUID,
        accepted_structure: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Accept the consultation recommendations and update project artifacts.

        Args:
            project_id: The project ID
            accepted_structure: The user-approved structure with any modifications
                Expected format:
                {
                    "universe_name": "Selected Name",
                    "content_type_label": "Film" | "Episode" | "Part",
                    "phases": [...],  # The approved phase structure
                }

        Returns:
            Dict with status and updated artifact info
        """
        # 1. Fetch project with artifacts
        statement = (
            select(Project)
            .where(Project.id == project_id)
            .options(selectinload(Project.artifacts))
        )
        result = await self.session.exec(statement)
        project = result.first()

        if not project:
            raise ValueError(f"Project {project_id} not found")

        # 2. Update project title to accepted universe name
        universe_name = accepted_structure.get("universe_name")
        if universe_name:
            project.title = universe_name
            self.session.add(project)

        # 3. Update artifacts with script metadata
        content_type_label = accepted_structure.get("content_type_label", "Film")
        phases = accepted_structure.get("phases", [])

        # Create a mapping from filename to artifact
        artifact_map = {}
        for artifact in project.artifacts:
            if artifact.artifact_type == ArtifactType.CHAPTER:
                content = artifact.content or {}
                title = content.get("title", "")
                artifact_map[title] = artifact
                # Also map by source file if available
                if artifact.source_file_url:
                    filename = artifact.source_file_url.split("/")[-1]
                    artifact_map[filename] = artifact

        # 4. Update each artifact based on accepted structure
        script_order = 1
        for phase in phases:
            for script in phase.get("scripts", []):
                original_filename = script.get("original_filename", "")
                suggested_title = script.get("suggested_title", "")

                # Find matching artifact
                artifact = artifact_map.get(original_filename) or artifact_map.get(
                    suggested_title
                )

                if artifact:
                    # Update artifact metadata
                    artifact.is_script = True
                    artifact.script_order = script_order
                    artifact.content_type_label = content_type_label

                    # Update content with suggested title
                    if artifact.content:
                        artifact.content["suggested_title"] = suggested_title
                        artifact.content["phase_number"] = phase.get("phase_number")
                        artifact.content["phase_title"] = phase.get("title")
                        artifact.content["role_in_universe"] = script.get(
                            "role_in_universe"
                        )

                    self.session.add(artifact)
                    script_order += 1

        await self.session.commit()

        return {
            "status": "success",
            "universe_name": universe_name,
            "scripts_updated": script_order - 1,
            "content_type_label": content_type_label,
        }

    async def generate_guided_analysis(
        self,
        file_contents: List[Dict[str, str]],
        user_prompt: str,
        user_tier: str = "free",
    ) -> Dict[str, Any]:
        """
        Analyze uploaded files and generate guided response with app-specific options.
        This is used BEFORE project creation to help users decide what to create.

        Args:
            file_contents: List of {filename, content} dicts
            user_prompt: User's optional prompt/description
            user_tier: Subscription tier for model selection

        Returns:
            Dict with content analysis, suggested actions, and follow-up questions
        """
        # Build the analysis prompt
        files_text = ""
        for i, file in enumerate(file_contents, 1):
            files_text += f"\n\n--- FILE {i}: {file['filename']} ---\n"
            files_text += self._truncate_for_summary(file["content"], max_chars=3000)

        system_prompt = """You are an intelligent creative assistant for a media production platform.
Your role is to analyze uploaded documents and guide users to the best creative options.

**PLATFORM CAPABILITIES:**
1. **Cinematic Universe** - Organize scripts into films/episodes with phases
2. **Script Expansion** - Develop high-concept ideas into full screenplays
3. **Storyboard Generation** - Create visual scene breakdowns with AI images
4. **Training Content** - Convert documents into educational videos
5. **Marketing/Ads** - Create promotional video content
6. **Video Production** - Generate AI-powered videos with narration

**ANALYSIS REQUIREMENTS:**
1. Identify the document type (script, concept, book, training material, pitch, etc.)
2. Assess the content quality (fully developed vs. needs expansion)
3. Recommend the most suitable platform capabilities
4. Ask clarifying questions if the user's intent is unclear

**RESPONSE FORMAT (JSON):**
{
    "content_analysis": {
        "document_type": "high_concept" | "full_script" | "book" | "training_manual" | "marketing_brief" | "other",
        "title": "Detected or suggested title",
        "summary": "2-3 sentence summary of the content",
        "quality_assessment": "needs_expansion" | "ready_for_production" | "requires_editing",
        "detected_elements": {
            "story_count": 0,
            "character_count": 0,
            "scene_count": 0,
            "themes": []
        }
    },
    "suggested_actions": [
        {
            "id": "cinematic_universe",
            "label": "Create Cinematic Universe",
            "description": "Organize into films with phases",
            "recommended": true,
            "disabled": false,
            "disabled_reason": null
        }
    ],
    "recommended_action": "cinematic_universe",
    "follow_up_questions": [
        "Which stories would you like to focus on first?"
    ],
    "ai_message": "I've analyzed your document... (conversational message for the user)"
}

Be conversational and helpful. Detect what the user needs based on their content."""

        user_message = f"""Analyze the following uploaded content and provide guidance:

USER'S PROMPT: {user_prompt or "(No prompt provided - ask what they want to do)"}

UPLOADED FILES:
{files_text}

Respond with your analysis in the JSON format specified."""

        tier_enum = ModelTier(user_tier.lower()) if user_tier else ModelTier.FREE

        try:
            response = await self.openrouter.analyze_content(
                content=f"{system_prompt}\n\n---\n\n{user_message}",
                user_tier=tier_enum,
                analysis_type="cinematic_universe_analysis",  # Uses special handling
            )

            result_text = response.get("result", "")
            parsed = self._parse_llm_json_response(result_text)

            return {
                "status": "success",
                **parsed,
                "model_used": response.get("model_used"),
            }

        except Exception as e:
            logger.error(f"Guided analysis failed: {str(e)}")
            # Return a fallback response
            return {
                "status": "error",
                "error": str(e),
                "content_analysis": {
                    "document_type": "other",
                    "title": (
                        file_contents[0]["filename"] if file_contents else "Unknown"
                    ),
                    "summary": "Unable to analyze content",
                    "quality_assessment": "unknown",
                },
                "suggested_actions": [
                    {
                        "id": "script_expansion",
                        "label": "Expand into Full Script",
                        "description": "Develop this content into a screenplay",
                        "recommended": True,
                        "disabled": False,
                    }
                ],
                "ai_message": "I had trouble analyzing your document. Would you like to expand it into a script?",
            }

    async def continue_conversation(
        self,
        message: str,
        context: Dict[str, Any],
        user_tier: str = "free",
    ) -> Dict[str, Any]:
        """
        Continue the consultation conversation with a follow-up message.

        Args:
            message: User's follow-up message
            context: Previous conversation context (messages, file info)
            user_tier: Subscription tier

        Returns:
            Dict with AI response and updated actions/questions
        """
        # Build conversation history
        history = context.get("messages", [])
        file_summary = context.get("file_summary", "")

        conversation_text = ""
        for msg in history[-6:]:  # Last 6 messages for context
            role = "User" if msg.get("role") == "user" else "Assistant"
            conversation_text += f"\n{role}: {msg.get('content', '')}"

        system_prompt = """You are continuing a consultation conversation about a media production project.
Maintain context from the previous messages and help guide the user to their next step.

Respond in JSON format:
{
    "ai_message": "Your conversational response",
    "action_to_take": "cinematic_universe" | "script_expansion" | "storyboard" | null,
    "follow_up_questions": ["Any clarifying questions"],
    "ready_to_proceed": true | false,
    "project_config": {
        "project_type": "entertainment" | "training" | "marketing",
        "content_type": "cinematic_universe" | "single_script" | "ad",
        "terminology": "Film" | "Episode" | "Part" | "Module",
        "universe_name": "If applicable"
    }
}"""

        user_message = f"""Previous context about uploaded files:
{file_summary}

Conversation history:
{conversation_text}

New user message: {message}

Respond helpfully and guide them toward their creative goal."""

        tier_enum = ModelTier(user_tier.lower()) if user_tier else ModelTier.FREE

        try:
            response = await self.openrouter.analyze_content(
                content=f"{system_prompt}\n\n---\n\n{user_message}",
                user_tier=tier_enum,
                analysis_type="cinematic_universe_analysis",
            )

            result_text = response.get("result", "")
            parsed = self._parse_llm_json_response(result_text)

            return {
                "status": "success",
                **parsed,
            }

        except Exception as e:
            logger.error(f"Conversation continuation failed: {str(e)}")
            return {
                "status": "error",
                "ai_message": "I'm having trouble processing that. Could you rephrase?",
                "error": str(e),
            }
