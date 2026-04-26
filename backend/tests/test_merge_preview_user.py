import uuid
from types import SimpleNamespace

import pytest
from fastapi import BackgroundTasks, HTTPException

from app.api.routes.merge.routes import generate_merge_preview, get_current_user_id
from app.auth.models import User
from app.merges.schemas import MergePreviewRequest


@pytest.mark.asyncio
async def test_merge_preview_accepts_authenticated_user_object():
    user_id = uuid.uuid4()
    request = MergePreviewRequest(
        input_sources=[
            {
                "url": "https://example.com/test-video.mp4",
                "type": "video",
                "duration": 10.0,
            }
        ],
        quality_tier="web",
        preview_duration=10.0,
    )
    background_tasks = BackgroundTasks()
    current_user = SimpleNamespace(id=user_id, is_active=True)

    response = await generate_merge_preview(
        request=request,
        background_tasks=background_tasks,
        session=None,
        current_user=current_user,
    )

    assert response.status == "processing"
    assert response.preview_duration == 10.0
    assert len(background_tasks.tasks) == 1
    assert background_tasks.tasks[0].args[1] is request
    assert background_tasks.tasks[0].args[2] == str(user_id)


def test_get_current_user_id_keeps_legacy_dict_compatibility():
    user_id = uuid.uuid4()

    assert get_current_user_id({"id": user_id}) == str(user_id)


def test_get_current_user_id_rejects_missing_id():
    with pytest.raises(HTTPException) as exc_info:
        get_current_user_id(SimpleNamespace())

    assert exc_info.value.status_code == 401


def test_user_model_supports_legacy_dict_access_for_auth_paths():
    user_id = uuid.uuid4()
    user = User(
        id=user_id,
        email="kan259@example.com",
        hashed_password="unused",
        is_active=True,
    )

    assert user["id"] == user_id
    assert user.get("id") == user_id
    assert user.get("missing", "fallback") == "fallback"

    with pytest.raises(KeyError):
        _ = user["missing"]
