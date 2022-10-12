"""An AWS Python Pulumi program"""

import pulumi
import pulumi_aws as aws
import pulumi_terraform as terraform

# Create an AWS resource (S3 Bucket)
bucket = aws.s3.Bucket('pulumi-bucket',
                   website=aws.s3.BucketWebsiteArgs(
                       index_document="index.html",
                   ))

# Add an object to the bucket
bucketObject = aws.s3.BucketObject(
    'index.html',
    acl='public-read',
    content_type='text/html',
    bucket=bucket.id,
    source=pulumi.FileAsset('index.html')
)

# Create iam role for lambda
iam_for_lambda = aws.iam.Role("pulumiLambdaRole", assume_role_policy="""{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Action": "sts:AssumeRole",
            "Principal": {
            "Service": "lambda.amazonaws.com"
        },
        "Effect": "Allow",
        "Sid": ""
        }
    ]
}
""")

# Create the lambda
lambda_func = aws.lambda_.Function("pulumiLambda",
                                   code=pulumi.FileArchive("lambda_function.zip"),
                                   role=iam_for_lambda.arn,
                                   handler="hello_pulumi",
                                   runtime="python3.7")

# Add permission for bucket to lambda
allow_bucket = aws.lambda_.Permission("allowBucket",
                                      action="lambda:InvokeFunction",
                                      function=lambda_func.arn,
                                      principal="s3.amazonaws.com",
                                      source_arn=bucket.arn)

# Trigger lambda on bucket notification
bucket_notification = aws.s3.BucketNotification("bucketNotification",
                                                bucket=bucket.id,
                                                lambda_functions=[aws.s3.BucketNotificationLambdaFunctionArgs(
                                                    lambda_function_arn=lambda_func.arn,
                                                    events=["s3:ObjectCreated:*"],
                                                    filter_prefix="AWSLogs/",
                                                    filter_suffix=".log",
                                                )],
                                                opts=pulumi.ResourceOptions(depends_on=[allow_bucket]))

# Accessing resources created in terraform 

# Get the tfstate file from s3
tf_state = terraform.state.RemoteStateReference("xspm-terraform",
                                                backend_type='s3',
                                                args=terraform.state.S3BackendArgs(bucket='tcell-stage-terraform',
                                                                                   key='env://tcell-stage-1/stage/xspm-vpc.tfstate',
                                                                                   region='us-east-1'))

# Use RemoteStateReference to access outputs specified in the .tfstate and reference existing resources managed by tf
vpc_id = tf_state.get_output('vpc_id')

# Export the name of the bucket
pulumi.export('bucket_name', bucket.id)
pulumi.export('bucket_endpoint', pulumi.Output.concat('http://', bucket.website_endpoint))
pulumi.export('lambda_arn', lambda_func.arn)
pulumi.export('vpc_id_from_tf', vpc_id)
