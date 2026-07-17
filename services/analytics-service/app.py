import os
import uuid
from datetime import datetime, timezone

import clickhouse_connect
from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)

CORS(
    app,
    resources={
        r"/api/*": {
            "origins": [
                "http://localhost:8080",
                "http://127.0.0.1:8080"
            ]
        }
    }
)

CLICKHOUSE_HOST = os.getenv(
    "CLICKHOUSE_HOST",
    "clickhouse"
)

CLICKHOUSE_PORT = int(
    os.getenv(
        "CLICKHOUSE_PORT",
        "8123"
    )
)

CLICKHOUSE_DATABASE = os.getenv(
    "CLICKHOUSE_DATABASE",
    "new_event_analytics"
)

CLICKHOUSE_USER = os.getenv(
    "CLICKHOUSE_USER",
    "analytics_user"
)

CLICKHOUSE_PASSWORD = os.getenv(
    "CLICKHOUSE_PASSWORD",
    "analytics_password"
)


def get_clickhouse_client():
    return clickhouse_connect.get_client(
        host=CLICKHOUSE_HOST,
        port=CLICKHOUSE_PORT,
        username=CLICKHOUSE_USER,
        password=CLICKHOUSE_PASSWORD
    )


def initialize_clickhouse():
    client = get_clickhouse_client()

    client.command(
        f"CREATE DATABASE IF NOT EXISTS {CLICKHOUSE_DATABASE}"
    )

    client.command(
        f"""
        CREATE TABLE IF NOT EXISTS
        {CLICKHOUSE_DATABASE}.web_analytics
        (
            analytics_id String,
            session_id String,
            event_type String,
            section_name String,
            track_name String,
            page_path String,
            device_type String,
            occurred_at DateTime
        )
        ENGINE = MergeTree
        ORDER BY (occurred_at, event_type)
        """
    )


@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status": "UP",
        "service": "analytics-service"
    })


@app.route("/ready", methods=["GET"])
def ready():
    try:
        client = get_clickhouse_client()
        client.command("SELECT 1")

        return jsonify({
            "status": "READY",
            "clickhouse": "CONNECTED"
        })

    except Exception as error:
        return jsonify({
            "status": "NOT_READY",
            "clickhouse": "DISCONNECTED",
            "details": str(error)
        }), 503


@app.route("/api/v1/analytics", methods=["POST"])
def capture_analytics():
    data = request.get_json(silent=True)

    if not data:
        return jsonify({
            "error": "Request body must contain valid JSON"
        }), 400

    required_fields = [
        "sessionId",
        "eventType",
        "pagePath",
        "deviceType"
    ]

    missing_fields = [
        field
        for field in required_fields
        if field not in data
    ]

    if missing_fields:
        return jsonify({
            "error": "Missing required fields",
            "fields": missing_fields
        }), 400

    allowed_event_types = [
        "SECTION_VIEW",
        "PROGRAM_TRACK_CLICK",
        "REGISTRATION_STARTED",
        "REGISTRATION_SUBMITTED"
    ]

    event_type = str(data["eventType"]).strip()

    if event_type not in allowed_event_types:
        return jsonify({
            "error": "Invalid eventType",
            "allowedEventTypes": allowed_event_types
        }), 400

    try:
        analytics_id = str(uuid.uuid4())

        occurred_at = datetime.now(
            timezone.utc
        ).replace(
            tzinfo=None
        )

        row = [
            analytics_id,
            str(data["sessionId"]).strip(),
            event_type,
            str(data.get("sectionName", "")).strip(),
            str(data.get("trackName", "")).strip(),
            str(data["pagePath"]).strip(),
            str(data["deviceType"]).strip(),
            occurred_at
        ]

        client = get_clickhouse_client()

        client.insert(
            f"{CLICKHOUSE_DATABASE}.web_analytics",
            [row],
            column_names=[
                "analytics_id",
                "session_id",
                "event_type",
                "section_name",
                "track_name",
                "page_path",
                "device_type",
                "occurred_at"
            ]
        )

        return jsonify({
            "message": "Analytics event captured",
            "analyticsId": analytics_id
        }), 201

    except Exception as error:
        return jsonify({
            "error": "Unable to capture analytics event",
            "details": str(error)
        }), 500


@app.route("/api/v1/analytics", methods=["GET"])
def get_analytics():
    try:
        client = get_clickhouse_client()

        result = client.query(
            f"""
            SELECT
                analytics_id,
                session_id,
                event_type,
                section_name,
                track_name,
                page_path,
                device_type,
                occurred_at
            FROM {CLICKHOUSE_DATABASE}.web_analytics
            ORDER BY occurred_at DESC
            LIMIT 100
            """
        )

        analytics_events = []

        for record in result.result_rows:
            analytics_events.append({
                "analyticsId": record[0],
                "sessionId": record[1],
                "eventType": record[2],
                "sectionName": record[3],
                "trackName": record[4],
                "pagePath": record[5],
                "deviceType": record[6],
                "occurredAt": record[7].isoformat()
            })

        return jsonify(analytics_events)

    except Exception as error:
        return jsonify({
            "error": "Unable to retrieve analytics",
            "details": str(error)
        }), 500


if __name__ == "__main__":
    initialize_clickhouse()

    app.run(
        host="0.0.0.0",
        port=5003,
        debug=True
    )