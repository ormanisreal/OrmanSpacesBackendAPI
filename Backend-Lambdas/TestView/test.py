import json, logging

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

def handler(event, context):
    authContext = event['requestContext']['authorizer']
    namespace = str(authContext['namespace'])
    token = str(authContext['token'])
    body = {
        "response": "Welcome to Orman live! You are authorized under: %s" % (namespace)
    }
    response = {
        "statusCode": 200,
        "body": json.dumps(body),
        "headers": { 
            "Access-Control-Allow-Origin": '*'
        }
    }
    return response
