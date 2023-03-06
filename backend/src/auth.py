import os
import re
import sys
import uuid
import hashlib
import json
import boto3
import datetime



from src.vendor import jwt
from src import utils

JWT_SECRET = os.getenv("JWT_SECRET")


def register(event, context):
    """
    register(event, context)

    Registers a new user with the given email, name, and password.

    Parameters:
        event (dict): A dictionary of data containing the user"s email, name, and password.
        context (object): An object containing information about the lambda function"s execution context.

    Returns:
        dict: A dictionary containing a status code and message indicating the result of the registration attempt.
    """
    client = boto3.client("dynamodb")
    post = utils.load_post_params(event)
    # simple validation
    required_fields = ["email", "name", "password"]
    for field in required_fields:
        if field not in post:
            return {
                "statusCode": 400,
                "body": json.dumps({
                    "message": f"{field} is required"
                })
            }
    data = client.get_item(
      TableName="users",
      Key={
          "email": {
            "S": post["email"]
          }
      }
    )
    if data.get("Item") is not None:
        return {
            "statusCode": 303,
            "body": json.dumps({
                "message": "User with this email already registered, do login instead"
            })
        }

    salt = uuid.uuid4().hex
    hash = hashlib.blake2b()
    hash.update(post["password"].encode())
    hash.update(salt.encode())
    password = hash.hexdigest()

    data = client.put_item(
        TableName="users",
        Item={
          "email": {
            "S": post["email"]
          },
          "name": {
            "S": post["name"]
          },
          "password": {
            "S": password
          },
          "salt": {
            "S": salt
          }
        }
    )
    return {
        "statusCode": 200,
        "body": json.dumps({
            "message":"User registered successfully"
        })
    }


def login(event, context):
    """
    login(event, context):
        Logs in a user with the given email and password.
        
        Parameters:
        event (dict): The event payload.
        context (dict): The context object.
        
        Returns:
        dict: A dict containing the status code and the message or token.
    """
    client = boto3.client("dynamodb")
    post = utils.load_post_params(event)
    required_fields = ["email", "password"]
    for field in required_fields:
        if field not in post:
            return {
                "statusCode": 400,
                "body": json.dumps({
                    "message": f"{field} is required"
                })
            }
    data = client.get_item(
      TableName="users",
      Key={
          "email": {
            "S": post["email"]
          }
      }
    )
    if data["Item"] is None:
        return {
            "statusCode": 204,
            "body": json.dumps({
                "message": "User with this email/password not found"
            })
        }

    user = utils.normalize_dynamodb_row(data["Item"])
    

    hash = hashlib.blake2b()
    hash.update(post["password"].encode())
    hash.update(user["salt"].encode())
    password = hash.hexdigest()
    if user["password"] != password:
        return {
            "statusCode": 204,
            "body": json.dumps({
                "message": "User with this email/password not found"
            })
        }

    token = jwt.encode({
        "email": user["email"],
        "exp": datetime.datetime.now(tz=datetime.timezone.utc) + datetime.timedelta(days=7)  # require login every 7 days
    }, JWT_SECRET, algorithm="HS256")
    return {
        "statusCode": 200,
        "body": json.dumps({
            "message": "Login successful",
            "token": token
        })
    }

def authorizer(event, context):
    """
    authorizer(event, context)

    This function is used to authorize a user based on the JWT token provided in the request header. It decodes the token using the secret key, extracts the email address and builds the authorization policy. The policy allows all methods if the token validation does not fail.

    Args:
        event (dict): Event object containing the request header.
        context (dict): Context object containing the request context.

    Returns:
        authResponse (dict): Authorization response containing the policy.
    """
    try:
        # event["headers"]["authorization"] example:
        # Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJlbWFpbCI6Inlhcm9zbGF2QHNhem9ub3YudGVhbSJ9.ELuqLVjBuX35mdGY03fTOKpVR-NRYxi7xkUZYJnMeFM
        auth_header = event["headers"]["authorization"].split(' ')
        token = jwt.decode(auth_header[1], JWT_SECRET, algorithms=["HS256"])
    except Exception as err:
        print(f"Unexpected {err=}, {type(err)=}")
        raise Exception("Unauthorized")
    principalId = f"user:{token['email']}"

    tmp = event["routeArn"].split(":")
    apiGatewayArnTmp = tmp[5].split("/")
    awsAccountId = tmp[4]

    policy = AuthPolicy(principalId, awsAccountId)
    policy.restApiId = apiGatewayArnTmp[0]
    policy.region = tmp[3]
    policy.stage = apiGatewayArnTmp[1]
    
    # just allowAll if token validation doesn't fail
    policy.allowAllMethods()

    # Finally, build the policy
    authResponse = policy.build({
        "email": token['email']
    })

    return authResponse


# source: https://github.com/awslabs/aws-apigateway-lambda-authorizer-blueprints/tree/master/blueprints/python

class HttpVerb:
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"
    HEAD = "HEAD"
    DELETE = "DELETE"
    OPTIONS = "OPTIONS"
    ALL = "*"


class AuthPolicy(object):
    # The AWS account id the policy will be generated for. This is used to create the method ARNs.
    awsAccountId = ""
    # The principal used for the policy, this should be a unique identifier for the end user.
    principalId = ""
    # The policy version used for the evaluation. This should always be "2012-10-17"
    version = "2012-10-17"
    # The regular expression used to validate resource paths for the policy
    pathRegex = "^[/.a-zA-Z0-9-\*]+$"

    """Internal lists of allowed and denied methods.
    These are lists of objects and each object has 2 properties: A resource
    ARN and a nullable conditions statement. The build method processes these
    lists and generates the approriate statements for the final policy.
    """
    allowMethods = []
    denyMethods = []

    # The API Gateway API id. By default this is set to "*"
    restApiId = "*"
    # The region where the API is deployed. By default this is set to "*"
    region = "*"
    # The name of the stage used in the policy. By default this is set to "*"
    stage = "*"

    def __init__(self, principal, awsAccountId):
        self.awsAccountId = awsAccountId
        self.principalId = principal
        self.allowMethods = []
        self.denyMethods = []

    def _addMethod(self, effect, verb, resource, conditions):
        """Adds a method to the internal lists of allowed or denied methods. Each object in
        the internal list contains a resource ARN and a condition statement. The condition
        statement can be null."""
        if verb != "*" and not hasattr(HttpVerb, verb):
            raise NameError("Invalid HTTP verb " + verb + ". Allowed verbs in HttpVerb class")
        resourcePattern = re.compile(self.pathRegex)
        if not resourcePattern.match(resource):
            raise NameError("Invalid resource path: " + resource + ". Path should match " + self.pathRegex)

        if resource[:1] == "/":
            resource = resource[1:]

        resourceArn = "arn:aws:execute-api:{}:{}:{}/{}/{}/{}".format(self.region, self.awsAccountId, self.restApiId, self.stage, verb, resource)

        if effect.lower() == "allow":
            self.allowMethods.append({
                "resourceArn": resourceArn,
                "conditions": conditions
            })
        elif effect.lower() == "deny":
            self.denyMethods.append({
                "resourceArn": resourceArn,
                "conditions": conditions
            })

    def _getEmptyStatement(self, effect):
        """Returns an empty statement object prepopulated with the correct action and the
        desired effect."""
        statement = {
            "Action": "execute-api:Invoke",
            "Effect": effect[:1].upper() + effect[1:].lower(),
            "Resource": []
        }

        return statement

    def _getStatementForEffect(self, effect, methods):
        """This function loops over an array of objects containing a resourceArn and
        conditions statement and generates the array of statements for the policy."""
        statements = []

        if len(methods) > 0:
            statement = self._getEmptyStatement(effect)

            for curMethod in methods:
                if curMethod["conditions"] is None or len(curMethod["conditions"]) == 0:
                    statement["Resource"].append(curMethod["resourceArn"])
                else:
                    conditionalStatement = self._getEmptyStatement(effect)
                    conditionalStatement["Resource"].append(curMethod["resourceArn"])
                    conditionalStatement["Condition"] = curMethod["conditions"]
                    statements.append(conditionalStatement)

            if statement["Resource"]:
                statements.append(statement)

        return statements

    def allowAllMethods(self):
        """Adds a "*" allow to the policy to authorize access to all methods of an API"""
        self._addMethod("Allow", HttpVerb.ALL, "*", [])

    def denyAllMethods(self):
        """Adds a "*" allow to the policy to deny access to all methods of an API"""
        self._addMethod("Deny", HttpVerb.ALL, "*", [])

    def allowMethod(self, verb, resource):
        """Adds an API Gateway method (Http verb + Resource path) to the list of allowed
        methods for the policy"""
        self._addMethod("Allow", verb, resource, [])

    def denyMethod(self, verb, resource):
        """Adds an API Gateway method (Http verb + Resource path) to the list of denied
        methods for the policy"""
        self._addMethod("Deny", verb, resource, [])

    def allowMethodWithConditions(self, verb, resource, conditions):
        """Adds an API Gateway method (Http verb + Resource path) to the list of allowed
        methods and includes a condition for the policy statement. More on AWS policy
        conditions here: http://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies_elements.html#Condition"""
        self._addMethod("Allow", verb, resource, conditions)

    def denyMethodWithConditions(self, verb, resource, conditions):
        """Adds an API Gateway method (Http verb + Resource path) to the list of denied
        methods and includes a condition for the policy statement. More on AWS policy
        conditions here: http://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies_elements.html#Condition"""
        self._addMethod("Deny", verb, resource, conditions)

    def build(self, context=None):
        """Generates the policy document based on the internal lists of allowed and denied
        conditions. This will generate a policy with two main statements for the effect:
        one statement for Allow and one statement for Deny.
        Methods that includes conditions will have their own statement in the policy."""
        if ((self.allowMethods is None or len(self.allowMethods) == 0) and
                (self.denyMethods is None or len(self.denyMethods) == 0)):
            raise NameError("No statements defined for the policy")

        policy = {
            "principalId": self.principalId,
            "policyDocument": {
                "Version": self.version,
                "Statement": []
            }
        }

        policy["policyDocument"]["Statement"].extend(self._getStatementForEffect("Allow", self.allowMethods))
        policy["policyDocument"]["Statement"].extend(self._getStatementForEffect("Deny", self.denyMethods))

        if context is not None:
            policy["context"] = context

        return policy