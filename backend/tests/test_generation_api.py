"""API integration tests for generation endpoints.

Wave 0 stubs — unskipped and implemented in Task 3.
"""
import pytest
import pytest_asyncio


@pytest.mark.asyncio
@pytest.mark.skip(reason="Wave 0 stub — implementation in Task 3")
async def test_generate_minutes_requires_auth(test_client):
    """POST without auth returns 401/403."""
    response = await test_client.post(
        "/api/meetings/1/minutes",
        json={"transcript": "Test transcript."},
    )
    assert response.status_code in (401, 403)


@pytest.mark.asyncio
@pytest.mark.skip(reason="Wave 0 stub — implementation in Task 3")
async def test_generate_minutes_success(test_client, chair_user, sample_meeting, seeded_template):
    """POST with chair auth + transcript returns 200 with markdown."""
    response = await test_client.post(
        f"/api/meetings/{sample_meeting.id}/minutes",
        json={"transcript": "The meeting was called to order at 10:00 AM."},
        headers={"x-user-email": chair_user.email},
    )
    assert response.status_code == 200
    data = response.json()
    assert "content_markdown" in data
    assert data["meeting_id"] == sample_meeting.id


@pytest.mark.asyncio
@pytest.mark.skip(reason="Wave 0 stub — implementation in Task 3")
async def test_get_minutes_returns_stored(test_client, chair_user, sample_meeting, seeded_template):
    """GET returns previously generated minutes."""
    # First generate minutes
    post_response = await test_client.post(
        f"/api/meetings/{sample_meeting.id}/minutes",
        json={"transcript": "Test transcript."},
        headers={"x-user-email": chair_user.email},
    )
    assert post_response.status_code == 200

    # Then retrieve them
    get_response = await test_client.get(
        f"/api/meetings/{sample_meeting.id}/minutes",
        headers={"x-user-email": chair_user.email},
    )
    assert get_response.status_code == 200
    data = get_response.json()
    assert data["meeting_id"] == sample_meeting.id
    assert "content_markdown" in data


@pytest.mark.asyncio
@pytest.mark.skip(reason="Wave 0 stub — implementation in Task 3")
async def test_get_minutes_404_when_none(test_client, chair_user, sample_meeting):
    """GET returns 404 when no minutes exist."""
    response = await test_client.get(
        f"/api/meetings/{sample_meeting.id}/minutes",
        headers={"x-user-email": chair_user.email},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
@pytest.mark.skip(reason="Wave 0 stub — implementation in Task 3")
async def test_templates_list_requires_admin(test_client, chair_user):
    """GET /admin/templates without admin auth returns 403."""
    response = await test_client.get(
        "/api/admin/templates",
        headers={"x-user-email": chair_user.email},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
@pytest.mark.skip(reason="Wave 0 stub — implementation in Task 3")
async def test_templates_list_success(test_client, admin_user, seeded_template):
    """GET /admin/templates with admin auth returns template list."""
    response = await test_client.get(
        "/api/admin/templates",
        headers={"x-user-email": admin_user.email},
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    assert data[0]["template_type"] == "meeting_minutes"


@pytest.mark.asyncio
@pytest.mark.skip(reason="Wave 0 stub — implementation in Task 3")
async def test_template_update_success(test_client, admin_user, seeded_template):
    """PUT /admin/templates/{id} updates template."""
    response = await test_client.put(
        f"/api/admin/templates/{seeded_template.id}",
        json={"name": "Updated Template Name"},
        headers={"x-user-email": admin_user.email},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated Template Name"


@pytest.mark.asyncio
@pytest.mark.skip(reason="Wave 0 stub — implementation in Task 3")
async def test_template_update_invalid_jinja(test_client, admin_user, seeded_template):
    """PUT with bad Jinja2 returns 400."""
    response = await test_client.put(
        f"/api/admin/templates/{seeded_template.id}",
        json={"user_prompt_template": "{% for item in items %}{% if bad syntax %}"},
        headers={"x-user-email": admin_user.email},
    )
    assert response.status_code == 400
