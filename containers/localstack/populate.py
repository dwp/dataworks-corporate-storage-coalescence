#!/usr/bin/env python
import argparse
import boto3
from corporate import corporate_key, corporate_batch
from manifest import manifest_key, manifest_batch


def main():
    args = command_line_args()
    s3 = s3_client()
    print(f"batch_count: {args.batch_count}, record_count: {args.record_count}")
    for batch_number in range(args.batch_count):
        start_offset = args.batch_count * batch_number
        end_offset = args.batch_count * batch_number + (args.batch_count - 1)
        body = object_body(args, batch_number)
        key = object_key(args, batch_number, start_offset, end_offset)
        s3.put_object(Bucket=args.bucket, Body=body, Key=key)
        print(f"Put '{key}' into '{args.bucket}'.")

    if not args.manifests:
        s3.put_object(Bucket=args.bucket, Body="phoney_object_1".encode(),
                      Key="corporate_storage/ucfs_audit/2020/11/05/data/businessAudit/"
                          "data.businessAudit_8_207899_261800.jsonl.gz")
        s3.put_object(Bucket=args.bucket, Body="phoney_object_2".encode(),
                      Key="corporate_storage/ucfs_audit/2020/11/05/data/businessAudit/"
                          "data.businessAudit_8_207899_261800.jsonl.gz.2")


def object_key(args, batch_number: int, start_offset: int, end_offset: int) -> str:
    return manifest_key(args, batch_number, start_offset, end_offset) if args.manifests \
        else corporate_key(args, batch_number, start_offset, end_offset)


def object_body(args, batch_number):
    return manifest_batch(args, batch_number) if args.manifests else corporate_batch(args, batch_number)


def command_line_args():
    parser = argparse.ArgumentParser(description='Pre-populate hbase for profiling.')

    parser.add_argument('-b', '--bucket', default="corporate-data", type=str,
                        help='The target bucket.')

    parser.add_argument('-u', '--cluster', default=None, type=str,
                        help='The source cluster.')

    parser.add_argument('-d', '--database', default="data", type=str,
                        help='The source database.')

    parser.add_argument('-c', '--collection', default="businessAudit", type=str,
                        help='The source collection.')

    parser.add_argument('-p', '--prefix', default="corporate_storage/ucfs_audit/2020/11/05", type=str,
                        help='The common prefix.')

    parser.add_argument('-m', '--manifests', default=False,
                        action="store_true",
                        help='Coalesces streaming manifests.')

    parser.add_argument('-n', '--batch-count', default=1100, type=int,
                        help='The number of batches to create.')

    parser.add_argument('-r', '--record-count', default=100, type=int,
                        help='The number of records per batch.')
    return parser.parse_args()


def s3_client():
    return boto3.client(service_name="s3",
                        endpoint_url="http://localstack:4566",
                        use_ssl=False,
                        aws_access_key_id="ACCESS_KEY",
                        aws_secret_access_key="SECRET_KEY")


if __name__ == "__main__":
    main()
