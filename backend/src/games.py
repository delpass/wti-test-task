import boto3
import json

from src import utils
from boto3.dynamodb.conditions import Attr


def get_table():
    dynamodb = boto3.resource("dynamodb")
    table = dynamodb.Table("games")
    return table


def list(event, context):
    table = get_table()
    response = table.scan()
    data = response['Items']
    while 'LastEvaluatedKey' in response:
        response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
        data.extend(response['Items'])

    response = {"statusCode": 200, "body": json.dumps(data)}
    return response