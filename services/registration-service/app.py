import os
import uuid
from datetime import datetime, timezone

import requests
from dotenv import load_dotenv
from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy

load_dotenv()

app = Flask(__name__)

app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

EVENT_SERVICE_URL = os.getenv(
    "EVENT_SERVICE_URL",
    "http://127.0.0.1:5000"
)


class Registration(db.Model):
    __tablename__ = "registrations"

    registration_id = db.Column(
        db.String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )

    event_id = db.Column(
        db.String(36),
        nullable=False
    )

    attendee_name = db.Column(
        db.String(200),
        nullable=False
    )

    attendee_email = db.Column(
        db.String(255),
        nullable=False
    )

    ticket_count = db.Column(
        db.Integer,
        nullable=False
    )

    registration_timestamp = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )

    def to_dict(self):
        timestamp = self.registration_timestamp

        if timestamp is not None:
            timestamp = timestamp.isoformat()

        return {
            "registrationId": self.registration_id,
            "eventId": self.event_id,
            "name": self.attendee_name,
            "email": self.attendee_email,
            "ticketCount": self.ticket_count,
            "timestamp": timestamp
        }


@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status": "UP",
        "service": "registration-service"
    })


@app.route("/ready", methods=["GET"])
def ready():
    try:
        db.session.execute(db.text("SELECT 1"))

        return jsonify({
            "status": "READY",
            "database": "CONNECTED"
        })

    except Exception:
        return jsonify({
            "status": "NOT_READY",
            "database": "DISCONNECTED"
        }), 503


@app.route("/api/v1/registrations", methods=["GET"])
def get_registrations():
    registrations = Registration.query.all()

    return jsonify([
        registration.to_dict()
        for registration in registrations
    ])


@app.route("/api/v1/registrations", methods=["POST"])
def create_registration():
    data = request.get_json(silent=True)

    if not data:
        return jsonify({
            "error": "Request body must contain valid JSON"
        }), 400

    required_fields = [
        "eventId",
        "name",
        "email",
        "ticketCount"
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

    try:
        ticket_count = int(data["ticketCount"])

        if ticket_count <= 0:
            return jsonify({
                "error": "ticketCount must be greater than zero"
            }), 400

        attendee_name = str(data["name"]).strip()
        attendee_email = str(data["email"]).strip()
        event_id = str(data["eventId"]).strip()

        if not attendee_name:
            return jsonify({
                "error": "name cannot be empty"
            }), 400

        if not attendee_email or "@" not in attendee_email:
            return jsonify({
                "error": "A valid email is required"
            }), 400

        reserve_response = requests.post(
            f"{EVENT_SERVICE_URL}/api/v1/events/{event_id}/reserve",
            json={
                "ticketCount": ticket_count
            },
            timeout=10
        )

        reserve_data = reserve_response.json()

        if reserve_response.status_code != 200:
            return jsonify({
                "error": "Seat reservation failed",
                "eventServiceResponse": reserve_data
            }), reserve_response.status_code

        registration = Registration(
            event_id=event_id,
            attendee_name=attendee_name,
            attendee_email=attendee_email,
            ticket_count=ticket_count
        )

        db.session.add(registration)
        db.session.commit()

        response = registration.to_dict()
        response["seatsAvailable"] = reserve_data["seatsAvailable"]
        response["lowSeatAlert"] = reserve_data["lowSeatAlert"]

        return jsonify(response), 201

    except requests.RequestException as error:
        return jsonify({
            "error": "Event Service is unavailable",
            "details": str(error)
        }), 503

    except (TypeError, ValueError):
        return jsonify({
            "error": "ticketCount must be a valid number"
        }), 400

    except Exception as error:
        db.session.rollback()

        return jsonify({
            "error": "Unable to create registration",
            "details": str(error)
        }), 500


if __name__ == "__main__":
    with app.app_context():
        db.create_all()

    app.run(
        host="0.0.0.0",
        port=5002,
        debug=True
    )