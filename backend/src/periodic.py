import json
import boto3
import urllib.request

API_URL = "https://www.gamerpower.com/api/giveaways"

def game_list_updater(event, context):
    """
    game_list_updater(event, context)

    This function updates a DynamoDB table with a list of games retrieved from a given API. It takes in two arguments, 
    event and context, and returns nothing.

    Args:
        event: The event that triggers the function.
        context: The context of the function.

    Returns:
        None
    """
    dynamodb = boto3.resource("dynamodb")
    table = dynamodb.Table('games')

    response = urllib.request.urlopen(API_URL)
    games_list = json.loads(response.read().decode("utf-8"))
    with table.batch_writer() as bw:
        for game in games_list:
            bw.put_item(Item={
                "title": game["title"],
                "image": game["image"],
                "description": game["description"],
                "type": game["type"],
                "platforms": game["platforms"],
            })