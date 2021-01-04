#########################################################################
# Template Parameters                                                   # 
#########################################################################
# Name for stack                                                        #
StackName='OrmanSpacesStack'
# Name of an existing s3 bucket to store deployment artifacts           #
DeploymentBucket='orman-deployment-bucket-files-get-deleted-daily'
# How many minutes before token is deleted                              #
TokenExpMinutes=600
# Orman spaces bucket name
OrmanSpacesBucketName='orman-spaces'
#########################################################################
# Package mainstack                                                     # 
#########################################################################
TZ=$(date +%m%d%y%H%M)                                                  #
aws cloudformation package                                              \
    --template-file deploy.yml                                          \
    --s3-bucket $DeploymentBucket                                       \
    --s3-prefix $TZ                                                     \
    --output-template-file packaged-mainstack.yml                       # 
#########################################################################
# Deploy packaged mainstack                                             # 
#########################################################################
aws cloudformation deploy                                               \
    --template-file packaged-mainstack.yml                              \
    --stack-name $StackName                                             \
    --parameter-overrides                                               \
        "pEnvironmentTag=${StackName}"                                  \
        "pTimeStamp=${TZ}"                                              \
        "pTokenExpMinutes=${TokenExpMinutes}"                           \
        "pOrmanSpacesBucketName=${OrmanSpacesBucketName}"               \
    --capabilities CAPABILITY_NAMED_IAM CAPABILITY_AUTO_EXPAND          #
#########################################################################

