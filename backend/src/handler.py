import json


def index(event, context):
    body = {
        "message": "Welcome to test API",
    }

    response = {"statusCode": 200, "body": json.dumps(body)}

    return response
