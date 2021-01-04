import json,os,boto3,logging,time
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
dynamodb = boto3.resource('dynamodb')
AuthTable = dynamodb.Table( os.environ['AUTH_TABLE_NAME'] )

def is_authorized(token):
    authorize_action = 'Deny'
    namespace = None
    key = {
        'token': str(token),
        }
    response = AuthTable.get_item(
        Key=key
    )
    n = len(response)
    if n <= 1:
        logger.debug( '(AUTH) Token Invalid (%s)' % (token) )
        return authorize_action, namespace
    namespace = response["Item"]["namespace"]
    ttl = response["Item"]["cleanup_time(TTL)"]
    if int( time.time() ) > ttl:
        message = ( '(AUTH) Token Expired (%s:%s)' % (token, namespace) )
        AuthTable.delete_item(Key=key)
    else:
        authorize_action = 'Allow'
        message = ( '(AUTH) Token Valid (%s:%s)' % (token, namespace) )
    logger.debug(message)   
    return authorize_action, namespace
    
def handler(event, context):
    authorize_action = 'Deny'
    authorizationToken = str(event['authorizationToken'])
    authorize_action, namespace = is_authorized(authorizationToken)
    arn = ( "%s/*" % '/'.join( event['methodArn'].split("/")[0:2] ) )
    authResponse = {
        'principalId': 'authorizer',
        'usageIdentifierKey': 'token',
        'policyDocument': {
            'Version': '2012-10-17',
            'Statement': [{
                'Action': 'execute-api:Invoke',
                'Effect': authorize_action,
                'Resource': arn
            }]
        },
        'context': {
            "namespace": namespace,
            'token': authorizationToken
        }
    }
    return authResponse

