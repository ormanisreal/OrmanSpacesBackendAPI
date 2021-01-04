import json, base64, boto3, os, datetime, time, logging, sys, pickle
from botocore.exceptions import ClientError
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
db = boto3.resource('dynamodb') 
SPACES_TABLE_NAME = os.environ["SPACES_TABLE_NAME"]
Orman = db.Table(SPACES_TABLE_NAME)  

def init_namespace(alias, reg_code, pubKey):
    namespace={
        "alias": alias,
        "namespace": alias,
        "reg_code": reg_code,
        "pubKey": pubKey,
        "nspace": {
            "key": "",
            "space": ""
        }
    }
    return namespace

def create_namespace(namespace):
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(SPACES_TABLE_NAME)
    try:
        response = table.put_item(
            Item=namespace,
            ConditionExpression= 'attribute_not_exists(namespace)'
        )   
        statusCode = 201
        response = "Succesfully created namespace: %s" % (namespace["namespace"])
    except db.meta.client.exceptions.ConditionalCheckFailedException as e: 
        statusCode = 406
        response = ("Can't register namespace %s, it already exits" % (namespace["namespace"]))   
    return statusCode, response
    
def check_reg_code(alias, reg_code):
    aliass = Orman.get_item(Key={"namespace": "users"})['Item']['store']      
    if alias in aliass:
        if reg_code == aliass[alias]:
            return True
    logger.debug( "Failed reg_code %s" % (reg_code) )
    return False
    
def get_status_code(alias, reg_code):
    response = None
    valid = check_reg_code(alias, reg_code)
    if valid:
        statusCode = 200
    else:
        response = ( "Invalid registration code for %s" % (alias) )
        statusCode = 403
    return statusCode, response

def handler(event, context):
    body = dict()
    event_body =  event['body'] 
    payload = json.loads(event_body)

    alias = payload["alias"]
    reg_code = payload["reg_code"]
    pubKey = payload["pubKey"]

    statusCode, response = get_status_code(alias, reg_code)

    if statusCode == 200:
        namespace = init_namespace(alias, reg_code, pubKey)
        statusCode, response = create_namespace(namespace)
        
    if statusCode == 201:
        body["namespace"] = namespace

    body["response"] = response
    allow_origin = ( 'https://%s' % ( os.environ["PORTAL_DOMAIN_NAME"] ) )
    
    return {
        'statusCode': statusCode,
        'body': json.dumps(body),
        "headers": { 
            "Access-Control-Allow-Origin": '*'
        }
    }