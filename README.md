## Note: WIP

This README is very much WIP. More info/instructions to come.  
App is working as intended though.


## Introduction
This was an assignment from my 2025 Python Programming certificate program at the University of WA.

Key purposes/actions of this app include:
* Users can upload their pics and give them captions
* Users can edit captions of pics they've uploaded, and delete pics they've uploaded

Technologies used:
* Python and FastAPI for backend code
* Jinja HTML templating engine
* TailwindCSS framework 
* htmx JavaScript library


## Running the app locally

From repo root folder, start dev server with:

`fastapi dev .\photo_journal_app\main.py`

OR

`uvicorn photo_journal_app.main:app --reload
`

Then go to http://127.0.0.1:8000 and upload some pics!

