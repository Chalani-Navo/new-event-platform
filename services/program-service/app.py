import os
import uuid

from dotenv import load_dotenv
from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy

load_dotenv()

app = Flask(__name__)

app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)


class Program(db.Model):
    __tablename__ = "programs"

    program_id = db.Column(
        db.String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )

    event_id = db.Column(db.String(36), nullable=False)
    day = db.Column(db.Integer, nullable=False)
    track = db.Column(db.String(150), nullable=False)
    session = db.Column(db.String(250), nullable=False)
    speaker_name = db.Column(db.String(200), nullable=False)
    start_time = db.Column(db.String(20), nullable=False)
    end_time = db.Column(db.String(20), nullable=False)

    def to_dict(self):
        return {
            "programId": self.program_id,
            "eventId": self.event_id,
            "day": self.day,
            "track": self.track,
            "session": self.session,
            "speakerName": self.speaker_name,
            "startTime": self.start_time,
            "endTime": self.end_time
        }


@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status": "UP",
        "service": "program-service"
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


@app.route("/api/v1/programs", methods=["GET"])
def get_programs():
    programs = Program.query.all()

    return jsonify([
        program.to_dict()
        for program in programs
    ])


@app.route("/api/v1/programs", methods=["POST"])
def create_program():
    data = request.get_json(silent=True)

    if not data:
        return jsonify({
            "error": "Request body must contain valid JSON"
        }), 400

    required_fields = [
        "eventId",
        "day",
        "track",
        "session",
        "speakerName",
        "startTime",
        "endTime"
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
        day = int(data["day"])

        if day <= 0:
            return jsonify({
                "error": "day must be greater than zero"
            }), 400

        if not str(data["track"]).strip():
            return jsonify({
                "error": "track cannot be empty"
            }), 400

        if not str(data["session"]).strip():
            return jsonify({
                "error": "session cannot be empty"
            }), 400

        if not str(data["speakerName"]).strip():
            return jsonify({
                "error": "speakerName cannot be empty"
            }), 400

        program = Program(
            event_id=str(data["eventId"]).strip(),
            day=day,
            track=str(data["track"]).strip(),
            session=str(data["session"]).strip(),
            speaker_name=str(data["speakerName"]).strip(),
            start_time=str(data["startTime"]).strip(),
            end_time=str(data["endTime"]).strip()
        )

        db.session.add(program)
        db.session.commit()

        return jsonify(program.to_dict()), 201

    except (TypeError, ValueError):
        return jsonify({
            "error": "day must be a valid number"
        }), 400

    except Exception as error:
        db.session.rollback()

        return jsonify({
            "error": "Unable to create program",
            "details": str(error)
        }), 500


if __name__ == "__main__":
    with app.app_context():
        db.create_all()

    app.run(
        host="0.0.0.0",
        port=5001,
        debug=True
    )