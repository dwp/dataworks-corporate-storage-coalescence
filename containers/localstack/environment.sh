#!/usr/bin/env bash

init() {
    aws_local configure set aws_access_key_id access_key_id
    aws_local configure set aws_secret_access_key secret_access_key
}


create_corporate_data_bucket() {
    make_bucket corporate-data
}

make_bucket() {
    local bucket_name=$1

    if ! aws_local s3 ls s3://$bucket_name 2>/dev/null; then
        echo Making $bucket_name
        aws_local s3 mb s3://$bucket_name
        aws_local s3api put-bucket-acl --bucket $bucket_name --acl public-read
    else
        echo Bucket \'$bucket_name\' exists.
    fi

}

put_objects_in_bucket() {
  ./populate.py
}

aws_local() {
  aws --endpoint-url http://localstack:4566 --region=eu-west-2 "$@"
}
