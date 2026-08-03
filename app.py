import os
import json
from datetime import datetime

from flask import Flask, Response
from pymongo import MongoClient, DESCENDING
from pymongo.errors import PyMongoError, ServerSelectionTimeoutError

app = Flask(__name__)

MONGO_URI = os.environ.get("MONGO_URI", "mongodb://localhost:27017/")
MONGO_DB = os.environ.get("MONGO_DB", "production_db")
MONGO_COLLECTION = os.environ.get("MONGO_COLLECTION", "production_records")

TEMPLATE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "manifest_template.html")


def get_latest_report():
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


def render_manifest(doc):
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


@app.route("/")
def manifest():
    doc = get_latest_report()

    if not doc:
        return "<h1>No report found in MongoDB.</h1><p>Run production_analysis_mongodb.py first to populate data.</p>", 404

    if "error" in doc:
        return f"<h1>Error</h1><p>{doc['error']}</p>", 500

    html, status = render_manifest(doc)
    return Response(html, status=status, mimetype="text/html")


@app.route("/health")
def health():
    return {"status": "ok"}, 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
