r"""
UW Professional & Continuing Education - Python 330B - Summer 2025
Assignment 09: Full Stack Web Development with FastAPI
------------
This module: unit tests
"""

# pylint: disable=import-error
# pylint: disable=unused-argument
# pylint: disable=consider-using-with

import os
import tempfile
from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient
from PIL import Image
from tinydb import TinyDB, Query

from photo_journal_app.main import app, get_db, PHOTOS_PER_PAGE, get_sorted_photos

# Shared in-memory test DB
test_db_file = tempfile.NamedTemporaryFile(delete=False)
test_db = TinyDB(test_db_file.name)

# Override dependency so app + tests share DB
app.dependency_overrides[get_db] = lambda: test_db

client = TestClient(app)


def post_photo_to_db(entry: str):
    """
    Helper to simulate posting a photo with an image + entry.
    """
    image = Image.new("RGB", size=(1, 1))
    tmp = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
    try:
        image.save(tmp.name)
        tmp.close()
        with open(tmp.name, "rb") as f:
            response = client.post(
                "/post-photo",
                data={"entry": entry},
                files={"photo_upload": ("test.jpg", f, "image/jpeg")},
            )
        return response
    finally:
        os.remove(tmp.name)


def test_get_photo_journal():
    """
    Test that the main photo journal page loads successfully and contains expected content.
    """
    response = client.get("/", headers={"HX-Request": "true"})
    assert response.status_code == 200
    assert b"My photos" in response.content


def test_refresh_script_scrolls_to_top_on_reload():
    """
    Test that the main page includes script logic to scroll to top on browser refresh.
    """
    response = client.get("/")
    assert response.status_code == 200
    assert b"performance.navigation.type === 1" in response.content
    assert b"history.scrollRestoration = 'manual'" in response.content
    assert b"window.scrollTo(0, 0)" in response.content


@patch("photo_journal_app.main.resize_image_for_web")
@patch("aiofiles.open")
@patch("PIL.Image.open")
def test_post_new_photo(mock_image_open, mock_aio_open, mock_resize):
    """
    Test that posting a new photo with entry text works correctly and returns expected response.
    """
    response = post_photo_to_db("my awesome photo")
    assert response.status_code == 200
    assert b"my awesome photo" in response.content


@pytest.fixture(autouse=True)
def setup_cleanup():
    """
    Fixture to ensure clean database state before and after each test.
    """
    test_db.truncate()
    yield
    test_db.truncate()


@patch("photo_journal_app.main.resize_image_for_web")
@patch("aiofiles.open")
@patch("PIL.Image.open")
def test_edit_photo(mock_image_open, mock_aio_open, mock_resize):
    """
    Test that editing a photo's entry text updates the database and returns successful response.
    """
    response = post_photo_to_db("my cool photo")
    assert response.status_code == 200

    photo = Query()
    photo_created = test_db.get(photo.entry == "my cool photo")
    assert photo_created is not None

    photo_id = photo_created.doc_id
    response = client.put(
        f"/edit-photo/{photo_id}",
        data={"entry": "my super cool photo"},  # Changed from json= to data=
    )

    assert response.status_code == 200
    updated_photo = test_db.get(doc_id=photo_id)
    assert updated_photo is not None
    assert updated_photo["entry"] == "my super cool photo"


@patch("os.remove")
@patch("photo_journal_app.main.resize_image_for_web")
@patch("aiofiles.open")
@patch("PIL.Image.open")
def test_delete_photo(mock_image_open, mock_aio_open, mock_resize, mock_remove):
    """
    Test that deleting a photo removes it from the database and returns successful response.
    """
    response = post_photo_to_db("my great photo")
    assert response.status_code == 200
    photo = Query()
    photo_created = test_db.get(photo.entry == "my great photo")
    response = client.request(
        "DELETE",
        "/delete-photo",
        params={"photo_id": str(photo_created.doc_id)},
    )
    assert response.status_code == 200
    response = client.get("/", headers={"HX-Request": "true"})
    assert b"my great photo" not in response.content


@patch("photo_journal_app.main.resize_image_for_web")
@patch("aiofiles.open")
@patch("PIL.Image.open")
def test_delete_button_has_confirmation_prompt(mock_image_open, mock_aio_open, mock_resize):
    """
    Test that delete buttons include a confirmation prompt before deleting.
    """
    response = post_photo_to_db("my confirm photo")
    assert response.status_code == 200

    page = client.get("/", headers={"HX-Request": "true"})
    assert page.status_code == 200
    assert b'hx-confirm="Are you sure you want to delete this photo?"' in page.content


@patch("photo_journal_app.main.resize_image_for_web")
@patch("aiofiles.open")
@patch("PIL.Image.open")
def test_load_photos(mock_image_open, mock_aio_open, mock_resize):
    """
    Test pagination functionality by verifying initial photo load and subsequent load-more
    requests.
    """
    photo_entries = [
        "my awesome photo",
        "my cool photo",
        "my great photo",
        "my sweet photo",
        "my groovy photo",
    ]
    for entry in photo_entries:
        post_photo_to_db(entry)

    # get 3 most recent
    photos_to_load = get_sorted_photos(test_db.all(), 0, PHOTOS_PER_PAGE)
    response = client.get("/", headers={"HX-Request": "true"})
    assert response.status_code == 200
    for photo in photos_to_load:
        assert photo["entry"].encode() in response.content

    remaining_entries = [
        entry
        for entry in photo_entries
        if entry not in [p["entry"] for p in photos_to_load]
    ]
    for entry in remaining_entries:
        assert entry.encode() not in response.content

    # now load the rest
    response = client.get("/load-more", params={"skip": PHOTOS_PER_PAGE})
    assert response.status_code == 200
    assert any(entry in response.text for entry in remaining_entries)
