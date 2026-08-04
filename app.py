import os
import json
from datetime import datetime

from starlette.applications import Starlette
from starlette.responses import HTMLResponse, JSONResponse
from starlette.routing import Route, Mount
from starlette.requests import Request
from starlette.concurrency import run_in_threadpool

from pymongo import MongoClient, DESCENDING
from pymongo.errors import PyMongoError, ServerSelectionTimeoutError

from server import mcp

UPLOAD_FOLDER = "/tmp/uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

MONGO_URI = os.environ.get("MONGO_URI", "mongodb://localhost:27017/")
MONGO_DB = os.environ.get("MONGO_DB", "production_db")
MONGO_COLLECTION = os.environ.get("MONGO_COLLECTION", "production_records")

TEMPLATE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "manifest_template.html")


def _get_latest_report():
    try:
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        client.admin.command("ping")
        collection = client[MONGO_DB][MONGO_COLLECTION]
        doc = collection.find_one(sort=[("generated_at", DESCENDING)])
        client.close()
        return doc
    except ServerSelectionTimeoutError:
        return {"error": "Could not connect to MongoDB. Check MONGO_URI, network access, and Atlas IP whitelist."}
    except PyMongoError as e:
        return {"error": f"MongoDB error: {str(e)}"}


def _render_manifest(doc):
    if not os.path.exists(TEMPLATE_PATH):
        return "<h1>Error: manifest_template.html not found next to app.py</h1>", 500

    with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
        template = f.read()

    clean_doc = {k: v for k, v in doc.items() if k != "_id"}
    if isinstance(clean_doc.get("generated_at"), datetime):
        clean_doc["generated_at"] = clean_doc["generated_at"].isoformat()

    data_json = json.dumps(clean_doc, ensure_ascii=False, default=str)
    html = template.replace("__REPORT_DATA_JSON__", data_json)
    return html, 200


async def manifest(request: Request) -> HTMLResponse:
    doc = await run_in_threadpool(_get_latest_report)

    if not doc:
        return HTMLResponse(
            "<h1>No report found in MongoDB.</h1><p>Run production_analysis_mongodb.py first to populate data.</p>",
            status_code=404,
        )

    if "error" in doc:
        return HTMLResponse(f"<h1>Error</h1><p>{doc['error']}</p>", status_code=500)

    html, status = await run_in_threadpool(_render_manifest, doc)
    return HTMLResponse(html, status_code=status)


async def health(request: Request) -> JSONResponse:
    return JSONResponse({"status": "ok"})


async def upload(request: Request) -> JSONResponse:
    form = await request.form()
    file = form.get("file")

    if file is None:
        return JSONResponse({"error": "No file uploaded"}, status_code=400)

    if not file.filename:
        return JSONResponse({"error": "No filename"}, status_code=400)

    if not file.filename.lower().endswith(".xlsx"):
        return JSONResponse({"error": "Only .xlsx files are allowed"}, status_code=400)

    save_path = os.path.join(UPLOAD_FOLDER, file.filename)
    contents = await file.read()

    def _write():
        with open(save_path, "wb") as f:
            f.write(contents)

    await run_in_threadpool(_write)

    return JSONResponse({"status": "success", "path": save_path})


mcp_app = mcp.http_app(path="/mcp")

app = Starlette(
    routes=[
        Route("/", manifest, methods=["GET"]),
        Route("/health", health, methods=["GET"]),
        Route("/upload", upload, methods=["POST"]),
        Mount("/", app=mcp_app),
    ],
    lifespan=mcp_app.lifespan,
)