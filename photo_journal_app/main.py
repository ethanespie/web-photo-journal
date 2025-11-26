r"""
UW Professional & Continuing Education - Python 330B - Summer 2025
Assignment 09: Full Stack Web Development with FastAPI
------------
This module: driver script
"""

# pylint: disable=import-error
# pylint: disable=anomalous-backslash-in-string


from datetime import datetime
import os
import time
from typing import Annotated
from pathlib import Path

import aiofiles
from fastapi import Depends, FastAPI, Form, Request, Response, UploadFile, Query
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from jinja2_fragments.fastapi import Jinja2Blocks
from PIL import Image
from tinydb import TinyDB

BASE_DIR = Path(__file__).resolve().parent

app = FastAPI()
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Blocks(directory=BASE_DIR / "templates")


def get_db():
    """
    Creates and returns a TinyDB database connection instance for storing photo journal entries.
    """
    return TinyDB(BASE_DIR / "db.json")


PHOTOS_PER_PAGE = 3


# Utility functions
def get_sorted_photos(all_photos, current_photo_count, new_photo_count):
    """
    Retrieves a paginated subset of photos sorted by upload date in desc order (newest first).
    """
    return sorted(
        all_photos,
        key=lambda d: datetime.strptime(d["uploaded_at"], "%m/%d/%Y %I:%M:%S%p"),
        reverse=True,
    )[current_photo_count:new_photo_count]


def resize_image_for_web(photo_file_path: str):
    """
    Resizes uploaded images to web-friendly dimensions, optimizing landscape and portrait photos
    differently.
    """
    full_path = BASE_DIR / "static" / photo_file_path.lstrip("/")
    image_file = Image.open(full_path)
    if image_file.width > image_file.height and image_file.width > 1920:
        image_file.thumbnail((1920, 1080))
    if image_file.width < image_file.height and image_file.width > 900:
        image_file.thumbnail((900, 1200))
    image_file.save(full_path)


# FastAPI routes
@app.get("/", response_class=HTMLResponse)
def photo_journal(request: Request, db: TinyDB = Depends(get_db)):
    """
    Renders the main photo journal page with the most recent photos and upload form.
    On a full-page load (not an HTMX request) render all photos so a browser refresh
    doesn't collapse the view back to only PHOTOS_PER_PAGE items.
    """
    all_photos = db.all()
    total_photos = len(all_photos)

    # HTMX sets the "HX-Request" header to "true" when making partial requests.
    is_htmx = request.headers.get("hx-request") == "true" or request.headers.get("HX-Request") == "true"

    # If this is a full page load, show all photos currently in the DB so refresh preserves what is visible.
    # If this is an HTMX request (partial), keep the paginated behaviour.
    if is_htmx:
        display_count = PHOTOS_PER_PAGE
    else:
        display_count = total_photos if total_photos > 0 else PHOTOS_PER_PAGE

    sorted_photos = get_sorted_photos(all_photos, 0, display_count)
    context = {
        "photos": sorted_photos,
        "photo_count": display_count,
        "next_skip": display_count,
        "total_photos": total_photos,
    }
    return templates.TemplateResponse(request, "photo_journal.html.jinja2", context)


@app.post("/post-photo", response_class=HTMLResponse)
async def post_photo(
    request: Request,
    entry: Annotated[str, Form()],
    photo_upload: UploadFile,
    db: TinyDB = Depends(get_db),
):
    """
    Processes photo uploads, validates image files, resizes them, and creates a new journal entry.
    """
    os.makedirs(BASE_DIR / "static" / "images", exist_ok=True)
    valid_image_file = True
    photo_file_path = f"images/{photo_upload.filename}"
    full_path = BASE_DIR / "static" / photo_file_path
    async with aiofiles.open(full_path, "wb") as out_file:
        content = await photo_upload.read()
        await out_file.write(content)
        try:
            with Image.open(full_path) as image_file:
                image_file.verify()
        except (IOError, SyntaxError):
            valid_image_file = False
            os.remove(full_path)

    if not valid_image_file:
        return templates.TemplateResponse(
            request,
            "photo_journal.html.jinja2",
            {"photos": [], "invalid_image_file": True},
            block_name="photos",
        )

    resize_image_for_web(photo_file_path)
    uploaded_at = time.strftime("%m/%d/%Y %I:%M:%S%p")
    inserted_id = db.insert(
        {"entry": entry, "file_path": photo_file_path, "uploaded_at": uploaded_at}
    )
    new_photo = db.get(doc_id=inserted_id)

    return templates.TemplateResponse(
        request, "photo_card.html.jinja2", {"photo": new_photo}
    )


@app.get("/get-edit-photo-form/{photo_id}", response_class=HTMLResponse)
async def get_edit_photo_form(request: Request, photo_id: int):
    """
    Retrieves and renders the edit form template for a specific photo entry by its ID.
    """
    db = get_db()
    photo = db.get(doc_id=photo_id)
    if not photo:
        return HTMLResponse(status_code=404)
    return templates.TemplateResponse(
        request, "edit_photo.html.jinja2", {"photo": photo}
    )


@app.put("/edit-photo/{photo_id}", response_class=HTMLResponse)
async def edit_photo(
    request: Request,
    photo_id: int,
    entry: str = Form(...),
    db: TinyDB = Depends(get_db),
):
    """
    Updates the text entry associated with a specific photo and returns the updated photo card.
    """
    if not db.get(doc_id=photo_id):
        return HTMLResponse(status_code=404)

    db.update({"entry": entry}, doc_ids=[photo_id])
    updated = db.get(doc_id=photo_id)

    return templates.TemplateResponse(
        request, "photo_card.html.jinja2", {"photo": updated}
    )


@app.get("/get-photo-card/{photo_id}", response_class=HTMLResponse)
async def get_photo_card(request: Request, photo_id: int):
    """
    Retrieves and renders the HTML template for a single photo card by its ID.
    """
    db = get_db()
    photo = db.get(doc_id=photo_id)
    if not photo:
        return HTMLResponse(status_code=404)
    return templates.TemplateResponse(
        request, "photo_card.html.jinja2", {"photo": photo}
    )


@app.delete("/delete-photo")
async def delete_photo(
    photo_id: int = Query(..., description="ID of the photo to delete"),
    db: TinyDB = Depends(get_db),
):
    """
    Removes a photo entry from the database and deletes its associated image file from storage.
    """
    photo = db.get(doc_id=photo_id)
    if not photo:
        return Response(status_code=404)

    file_path = BASE_DIR / "static" / photo["file_path"].lstrip("/")
    if file_path.exists():
        file_path.unlink()

    db.remove(doc_ids=[photo_id])
    return Response(status_code=200)


@app.get("/load-more", response_class=HTMLResponse)
async def load_more(request: Request, skip: int = 0, db: TinyDB = Depends(get_db)):
    """
    Handles infinite scroll functionality by loading additional photos when the user reaches the
    bottom of the page. Returns the next chunk and updated next_skip/total_photos for the template.
    """
    all_photos = db.all()
    total_photos = len(all_photos)
    new_photos = get_sorted_photos(all_photos, skip, skip + PHOTOS_PER_PAGE)
    next_skip = skip + len(new_photos)
    return templates.TemplateResponse(
        request,
        "photo_journal.html.jinja2",
        {"photos": new_photos, "next_skip": next_skip, "total_photos": total_photos},
        block_name="photos",
    )
