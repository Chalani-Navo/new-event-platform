import os
import uuid
from datetime import datetime

from dotenv import load_dotenv
from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy

load_dotenv()

app = Flask(__name__)

app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)


class Event(db.Model):
    __tablename__ = "events"

    event_id = db.Column(
        db.String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )
    title = db.Column(db.String(200), nullable=False)
    venue = db.Column(db.String(200), nullable=False)
    event_datetime = db.Column(db.DateTime, nullable=False)
    ticket_price = db.Column(db.Numeric(10, 2), nullable=False)
    capacity = db.Column(db.Integer, nullable=False)
    seats_available = db.Column(db.Integer, nullable=False)

    def to_dict(self):
        return {
            "eventId": self.event_id,
            "title": self.title,
            "venue": self.venue,
            "dateTime": self.event_datetime.isoformat(),
            "ticketPrice": float(self.ticket_price),
            "capacity": self.capacity,
            "seatsAvailable": self.seats_available
        }


@app.route("/health")
def health():
    return jsonify({
        "status": "UP",
        "service": "event-service"
    })


@app.route("/ready")
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


@app.route("/api/v1/events", methods=["GET"])
def get_events():
    events = Event.query.all()
    return jsonify([event.to_dict() for event in events])


@app.route("/api/v1/events", methods=["POST"])
def create_event():
    data = request.get_json(silent=True)

    required_fields = [
        "title",
        "venue",
        "dateTime",
        "ticketPrice",
        "capacity"
    ]

    if not data:
        return jsonify({
            "error": "Request body must contain valid JSON"
        }), 400

    missing_fields = [
        field for field in required_fields
        if field not in data
    ]

    if missing_fields:
        return jsonify({
            "error": "Missing required fields",
            "fields": missing_fields
        }), 400

    try:
        capacity = int(data["capacity"])
        ticket_price = float(data["ticketPrice"])
        event_datetime = datetime.fromisoformat(data["dateTime"])

        if capacity <= 0:
            return jsonify({
                "error": "capacity must be greater than zero"
            }), 400

        if ticket_price < 0:
            return jsonify({
                "error": "ticketPrice cannot be negative"
            }), 400

        event = Event(
            title=data["title"],
            venue=data["venue"],
            event_datetime=event_datetime,
            ticket_price=ticket_price,
            capacity=capacity,
            seats_available=capacity
        )

        db.session.add(event)
        db.session.commit()

        return jsonify(event.to_dict()), 201

    except (TypeError, ValueError):
        return jsonify({
            "error": (
                "capacity and ticketPrice must be valid numbers, "
                "and dateTime must use ISO format"
            )
        }), 400

    except Exception as error:
        db.session.rollback()

        return jsonify({
            "error": "Unable to create event",
            "details": str(error)
        }), 500


@app.route("/api/v1/events/<event_id>/reserve", methods=["POST"])
def reserve_seats(event_id):
    data = request.get_json(silent=True)

    if not data or "ticketCount" not in data:
        return jsonify({
            "error": "ticketCount is required"
        }), 400

    try:
        ticket_count = int(data["ticketCount"])

        if ticket_count <= 0:
            return jsonify({
                "error": "ticketCount must be greater than zero"
            }), 400

        event = db.session.get(Event, event_id)

        if event is None:
            return jsonify({
                "error": "Event not found"
            }), 404

        if event.seats_available < ticket_count:
            return jsonify({
                "error": "Insufficient seats",
                "seatsAvailable": event.seats_available
            }), 409

        event.seats_available -= ticket_count
        db.session.commit()

        return jsonify({
            "eventId": event.event_id,
            "reservedSeats": ticket_count,
            "seatsAvailable": event.seats_available,
            "lowSeatAlert": event.seats_available < 10
        }), 200

    except (TypeError, ValueError):
        return jsonify({
            "error": "ticketCount must be a valid number"
        }), 400

    except Exception as error:
        db.session.rollback()

        return jsonify({
            "error": "Unable to reserve seats",
            "details": str(error)
        }), 500


if __name__ == "__main__":
    with app.app_context():
        db.create_all()

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )