import boto3
import json

from src import utils
from boto3.dynamodb.conditions import Attr

### querieng by id
### event["pathParameters"] = {"id": "1234234"}

def get_table():
    dynamodb = boto3.resource("dynamodb")
    table = dynamodb.Table("favorites")
    return table


def add(event, context):
    table = get_table()
    user = utils.get_user(event)
    post = utils.load_post_params(event)
    item = {
        "title": post["title"],
        "email": user,
        "description": post["description"],
    }
    response = table.put_item(
        Item=item
    )
    response = {"statusCode": 200, "body": json.dumps(item)}

def delete(event, context):
    title = event["pathParameters"]["id"]
    table = get_table()
    user = utils.get_user(event)
    response = table.delete_item(Key={
        "email": user,
        "title": title,
    })
    response = {"statusCode": 204}
    return response

def list(event, context):
    table = get_table()
    body = []
    user = utils.get_user(event)
    response = table.scan(
        FilterExpression=Attr("email").eq(user)
    )
    data = response['Items']
    while 'LastEvaluatedKey' in response:
        response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
        data.extend(response['Items'])

    response = {"statusCode": 200, "body": json.dumps(data)}
    return response

def update(event, context):
    title = event["pathParameters"]["id"]
    table = get_table()
    user = utils.get_user(event)
    post = utils.load_post_params(event)
    upd = table.update_item(
        Key={
            "email": user,
            "title": title,
        },
        UpdateExpression="SET description = :new_description",
        ExpressionAttributeValues={
            ':new_description': post["description"]
        },
        ReturnValues="UPDATED_NEW"
    )
    response = {"statusCode": 200, "body": json.dumps(upd)}
    return response
