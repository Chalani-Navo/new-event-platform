import json
import os
from datetime import datetime, timezone

import boto3


s3_client = boto3.client("s3")
BUCKET_NAME = os.environ["BUCKET_NAME"]


def lambda_handler(event, context):
    event_id = event.get("eventId")
    remaining_seats = event.get("remainingSeats")

    if not event_id:
        return {
            "statusCode": 400,
            "body": json.dumps({
                "error": "eventId is required"
            })
        }

    if remaining_seats is None:
        return {
            "statusCode": 400,
            "body": json.dumps({
                "error": "remainingSeats is required"
            })
        }

    timestamp = event.get(
        "timestamp",
        datetime.now(timezone.utc).isoformat()
    )

    notification = {
        "eventId": event_id,
        "eventTitle": event.get("eventTitle", ""),
        "remainingSeats": int(remaining_seats),
        "timestamp": timestamp,
        "message": (
            f"Low-seat warning: event {event_id} has "
            f"{remaining_seats} seats remaining."
        )
    }

    safe_timestamp = timestamp.replace(":", "-").replace("+", "_")

    object_key = (
        f"low-seat-alerts/{event_id}/"
        f"{safe_timestamp}.json"
    )

    s3_client.put_object(
        Bucket=BUCKET_NAME,
        Key=object_key,
        Body=json.dumps(notification, indent=2),
        ContentType="application/json"
    )

    return {
        "statusCode": 201,
        "body": json.dumps({
            "message": "Low-seat notification written to S3",
            "bucket": BUCKET_NAME,
            "objectKey": object_key
        })
    }