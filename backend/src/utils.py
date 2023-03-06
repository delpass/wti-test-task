import json
import base64

def load_post_params(event):
	if event["isBase64Encoded"]:
		return json.loads(base64.b64decode(event["body"]).decode("utf-8"))
	return json.loads(event["body"])


def normalize_dynamodb_row(row):
	out = {}
	for field in row:
		out[field] = row[field]["S"]
	return out

def get_user(event):
	return event["requestContext"]["authorizer"]["lambda"]["email"]