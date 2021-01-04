import json, base64, boto3, os, datetime, time, logging, sys, pickle
from botocore.exceptions import ClientError
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
db = boto3.resource("dynamodb") 
SPACES_TABLE_NAME = os.environ["SPACES_TABLE_NAME"]
Orman = db.Table(SPACES_TABLE_NAME)  

spaces_bucket = os.environ["SPACES_BUCKET_NAME"]
s3 = boto3.resource("s3").Bucket(spaces_bucket)
json.load_s3 = lambda f: json.load(s3.Object(key=f).get()["Body"])
json.dump_s3 = lambda obj, f: s3.Object(key=f).put(Body=json.dumps(obj))

def get_namespace_item(namespace):
    try:
        response = Orman.get_item(Key={"namespace": namespace})
    except ClientError as e:
        print(e.response["Error"]["Message"])
    else:
        return response["Item"]

def create_namespace(namespace):
    if type(namespace) == str:
        namespace = json.loads(namespace)
    dynamodb = boto3.resource("dynamodb")
    table = dynamodb.Table( SPACES_TABLE_NAME )
    response = table.put_item(Item=namespace)     
    logger.debug( "Created namespace %s" % ( str(namespace) ) )
    
def check_reg_code(alias, reg_code):
    registry = \
        Orman.get_item(
            Key={
                "namespace": "users"
            }
        )["Item"]["store"]      
    if alias in registry:
        if reg_code == registry[alias]:
            return True
    logger.debug( "Invalid registration code %s" % (reg_code) )
    return False
    
def get_status_code(alias, reg_code):
    valid = check_reg_code(alias, reg_code)
    if valid:
        statusCode = 200
    else:
        logger.debug( "Failed login attempt by %s" % (alias) )
        statusCode = 403
    return statusCode

def save_space_to_s3(alias, space):
    file_name = ( "/tmp/%s.orman" % (alias))
    file_key = ( "spaces/%s.orman" % (alias) )
    s3_client = boto3.client("s3")
    with open(file_name, "wb") as output:
        pickle.dump(space, output, pickle.HIGHEST_PROTOCOL)
    s3_client.upload_file(file_name, spaces_bucket, file_key)

def load_space_from_s3(alias):
    ile_name = ( "/tmp/%s.orman" % (alias))
    file_key = ( "spaces/%s.orman" % (alias) )
    s3_client = boto3.client("s3")
    with open(ile_name, "wb") as f:
        s3_client.download_fileobj(spaces_bucket, file_key, f)
    with open(ile_name, "rb") as f:
        return pickle.load(f)  

def delete_space_from_s3(alias):
    s3 = boto3.resource("s3")
    key = ( "spaces/%s.orman" % (alias) )
    try:
        obj = s3.Object("orman", key)
        obj.delete()
    except ClientError as e:
        logger.debug("No namespace stored in s3: \n%s" % (e))

def update_namespace(alias, space):
    delete_unused_space = False
    db = boto3.resource("dynamodb") 
    table = db.Table(SPACES_TABLE_NAME)  
    if "aeskey" not in space:
        raise ValueError("Namespace not encrypted")
    if sys.getsizeof(space["space"]) >= 400000:
        save_space_to_s3(alias, space["space"])
        space = {
            "space": ( "s3://orman/spaces/%s.orman" % (alias) ),
            "aeskey": space["aeskey"]
        }
    else:
        delete_unused_space = True
    response = table.update_item(
        Key={
            "namespace": alias
        },
        UpdateExpression="set nspace=:s",
        ExpressionAttributeValues={
            ":s": space
        },
        ReturnValues="UPDATED_NEW"
    )
    if delete_unused_space == True:
        delete_space_from_s3(alias)
    return response

def delete_namespace(alias):
    delete_space_from_s3(alias)
    return Orman.delete_item(Key={"namespace":alias})

def get_namespace(alias):
    from urllib.parse import urlparse  
    namespace = get_namespace_item(alias)
    nspace = namespace["nspace"]
    space = nspace["space"]
    if space[:2] == "s3":
        nspace["space"] = load_space_from_s3(alias)
    return nspace

def handler(event, context):
    event_body =  event["body"] 
    payload = json.loads(event_body)
    alias = payload["alias"]
    authContext = event["requestContext"]["authorizer"]
    auth_alias = str(authContext["namespace"])
    if alias != auth_alias:
        return {"statusCode":406,"body":None}
    action = payload["action"]
    statusCode = get_status_code(alias, payload["reg_code"])
    if statusCode == 200:
        if action == "get":
            namespace = get_namespace(alias)
        if action == "update":
            namespace = payload["namespace"]
            update_namespace(alias, namespace)
        elif action == "delete":
            if payload["namespace"] == "delete":
                delete_namespace(alias)
                statusCode = 203
                namespace="Deleted namespace %s" % (alias)
            else:
                statusCode = 501
                namespace="Namespace in payload must equal 'delete'"
        else:
            statusCode == 406
    allow_origin = ( "https://%s" % ( os.environ["PORTAL_DOMAIN_NAME"] ) )
    return {
        "statusCode": statusCode,
        "body": json.dumps(namespace),
        "headers": { 
            "Access-Control-Allow-Origin": "*"
        }
    }