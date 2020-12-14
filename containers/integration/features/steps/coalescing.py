import gzip

from behave import given, then, step
import boto3


@given("s3 has been populated")
def step_impl(context):
    # Step already performed.
    pass


@step("coalescing has been run")
def step_impl(context):
    # Step already performed.
    pass


@then("there will be {num_files} files under {bucket} {prefix}")
def step_impl(context, num_files: int, bucket: str, prefix: str):
    client = s3_client()
    results = client.list_objects_v2(Bucket=bucket, Prefix=prefix)
    contents = results['Contents']
    print(f"{num_files}, {len(contents)}")
    assert int(num_files) == len(contents)
    context.contents = contents
    context.client = client
    context.bucket = bucket


@step("there will be {num_records} {type_of} records therein")
def step_impl(context, num_records, type_of):
    objects = []

    for obj in context.contents:
        if not obj['Key'].endswith('data.businessAudit_8_207899_261800.jsonl.gz') \
                and not obj['Key'].endswith('data.businessAudit_8_207899_261800.jsonl.gz.2'):
            objects.append(context.client.get_object(Bucket=context.bucket, Key=obj['Key']))

    accumulated = None
    for obj in objects:
        contents = object_contents(obj)
        accumulated = accumulated + contents if accumulated else contents

    uncompressed = gzip.decompress(accumulated) if type_of == "corporate" else accumulated
    lines = uncompressed.decode().split("\n")
    non_empty = [line for line in lines if len(line) > 0]
    print(f"non_empty: {len(non_empty)}, num_records: {num_records}, lines: {len(lines)}")
    assert len(non_empty) == int(num_records)


@step("there will be an object with key {key}")
def step_impl(context, key: str):
    print(f"{context.bucket}, key: {key}")
    assert context.client.get_object(Bucket=context.bucket, Key=key) is not None


def object_contents(s3_object: dict) -> bytes:
    stream = s3_object['Body']
    try:
        contents = None
        for chunk in stream.iter_chunks():
            contents = chunk if not contents else contents + chunk
        return contents
    finally:
        stream.close()


def s3_client():
    return boto3.client(service_name="s3",
                        endpoint_url="http://localstack:4566",
                        use_ssl=False,
                        aws_access_key_id="ACCESS_KEY",
                        aws_secret_access_key="SECRET_KEY")
