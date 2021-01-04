import json, base64, boto3, os, datetime, time, logging
from botocore.exceptions import ClientError
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_v1_5 as Cipher_PKCS1_v1_5

db = boto3.resource('dynamodb') 
SPACES_TABLE_NAME = os.environ["SPACES_TABLE_NAME"]
Orman = db.Table(SPACES_TABLE_NAME)  

def get_namespace(namespace):
    try:
        response = Orman.get_item(Key={'namespace': namespace})
    except ClientError as e:
        print(e.response['Error']['Message'])
    else:
        return response['Item']

def update_db(token, namespace, expiration_minutes):
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table( os.environ['AUTH_TABLE_NAME'] )
    ttl = int( time.time() ) + ( 60 * expiration_minutes )
    response = table.put_item(
       Item={
            'token': token,
            'namespace': namespace,
            'request_date': str( datetime.datetime.now() ),
            'cleanup_time(TTL)': ttl
        }
    )      
    
def is_valid(namespace, reg_code):
    namespaces = Orman.get_item(Key={"namespace": "users"})['Item']['store']      
    if namespace in namespaces:
        if reg_code == namespaces[namespace]:
            return True
    return False
    
def check_namespace(namespace, reg_code):
    valid = is_valid(namespace, reg_code)
    if valid == True:
        statusCode = 200
        token = base64.b64encode( os.urandom(64) ).decode()
    else:
        logger.debug( "Failed login attempt by %s" % (namespace) )
        statusCode = 403
        token = None
    return token, statusCode

def encrypt_message(pubKey, message):
    keyPub = RSA.importKey(pubKey)  
    cipher = Cipher_PKCS1_v1_5.new(keyPub)      
    return cipher.encrypt(message.encode())

def encrpyt_token(token, namespace):
    namespace = get_namespace(namespace)
    pubKey = namespace['pubKey']
    cipher = encrypt_message(pubKey, token)
    return cipher

def handler(event, context):
    expiration_minutes = int( os.environ["TOKEN_EXP_MINUTES"] )
    
    logger.debug("################### BUSINESS")
    logger.debug(str(event))

    event_body = str( event['body'] )
    payload = json.loads(event_body)
    namespace = payload["namespace"]
    reg_code = payload["reg_code"]
    token, statusCode = check_namespace(namespace, reg_code)
    if statusCode == 200:
        update_db(token, namespace, expiration_minutes)
        token = encrpyt_token(token, namespace)
    allow_origin = ( 'https://%s' % ( os.environ["PORTAL_DOMAIN_NAME"] ) )
    return {
        'statusCode': statusCode,
        'body': json.dumps({
            'token': str(token),
            'expiration_minutes': expiration_minutes
        }),
        "headers": { 
            "Access-Control-Allow-Origin": '*'
        }
    }