# Introduction
This was an assignment from my 2025 Python Programming certificate program at the University of WA.

Key purposes/actions of this app:
* Photo journal / photo stream type site that allows the to upload their pics and give them captions.
* Users can edit captions of pics they've uploaded, and delete pics they've uploaded.

Technologies used:
* Python and FastAPI for backend code
* Jinja HTML templating engine
* TailwindCSS framework 
* htmx JavaScript library


# Set Up / Prerequisites

1. Clone repo and `cd` into it
2. Create virtual environment and activate it

    `python -m venv .venv`
    
    `.\venv\Scripts\activate`
3. Install requirements
    
    `pip install -r photo_journal_app\requirements.txt`



# Running the App Locally

From repo root folder, start dev server with:

`fastapi dev .\photo_journal_app\main.py`

OR

`uvicorn photo_journal_app.main:app --reload`

Then go to http://127.0.0.1:8000 and upload some pics!


# Running Tests + Coverage Report

Ensure the Setup steps above have been done, then run this from project root (with Command Prompt, not PS):

`pytest .\photo_journal_app\test_main.py  -vv --cov --cov-report term-missing`


# Resetting the DB

To reset the DB to delete all pics and get a clean slate: delete or rename `db.json` and also the `.\static\images` directory.