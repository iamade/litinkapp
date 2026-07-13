from unittest.mock import patch

import pytest

from app.api.routes.auth.oauth import callback


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("error", "code"),
    [("access_denied", None), (None, None)],
)
async def test_google_callback_redirects_provider_failure_to_friendly_auth_page(
    error, code
):
    with patch("app.api.routes.auth.oauth.settings.FRONTEND_URL", "https://app.test"):
        response = await callback(
            provider="google",
            code=code,
            response=None,
            request=None,
            error=error,
            error_description="The selected account does not exist",
            session=None,
        )

    assert response.status_code == 303
    assert response.headers["location"] == (
        "https://app.test/auth?oauth_error=account_unavailable"
    )
