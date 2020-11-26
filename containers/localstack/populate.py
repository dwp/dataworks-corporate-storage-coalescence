#!/usr/bin/env python
import argparse
import base64
import binascii
import gzip
import json
from functools import reduce
from Crypto import Random
from Crypto.Cipher import AES
from Crypto.Util import Counter
import boto3


def main():
    args = command_line_args()
    s3 = s3_client()
    for batch_number in range(args.batch_count):
        batch = [kafka_message(args.database, args.collection, batch_number, record_number)
                 for record_number in range(args.record_count)]
        accumulated = reduce(lambda acc, x: f"{acc}\n{x}", batch, "")
        compressed = gzip.compress(accumulated.encode("ASCII"))
        start_offset = args.batch_count * batch_number
        end_offset = args.batch_count * batch_number + (args.batch_count - 1)
        prefix = f"{args.cluster}." if args.cluster else ""

        key = f"{args.prefix}/{args.database}/{args.collection}/{prefix}{args.database}.{args.collection}_{batch_number % 10}_{start_offset}-{end_offset}.jsonl.gz"
        s3.put_object(Bucket=args.bucket, Body=compressed, Key=key)
        print(f"Put '{key}' into '{args.bucket}'.")


def kafka_message(database: str, collection: str, batch_number: int, record_number: int):
    key = "53Et7AKlQa1ifNCb/PY5iA=="
    db_object = plaintext_db_object(batch_number, record_number)
    iv, encrypted = encrypt(key, json.dumps(db_object))
    return {
        "traceId": f"{batch_number:05d}/{record_number:05d}",
        "unitOfWorkId": f"{record_number:05d}",
        "@type": "V4",
        "message": {
            "db": f"{database}",
            "collection": f"{collection}",
            "_id": {
                "record_id": f"{record_number:05d}",
                "batch_id": f"{batch_number:05d}"
            },
            "_timeBasedHash": "hash",
            "@type": "MONGO_INSERT",
            "_lastModifiedDateTime": "2018-12-14T15:01:02.000+0000",
            "encryption": {
                "encryptionKeyId": "cloudhsm:1,2",
                "encryptedEncryptionKey": key,
                "initialisationVector": iv,
                "keyEncryptionKeyId": "cloudhsm:1,2"
            },
            "dbObject": f'"{encrypted}"'
        },
        "version": "core-4.master.9790",
        "timestamp": "2019-07-04T07:27:35.104+0000"
    }


def plaintext_db_object(batch_number: int, record_number: int):
    return {
        "_id": {
            "record_id": f"{record_number:05d}",
            "batch_id": f"{batch_number:05d}"
        },
        "createdDateTime": "2015-03-20T12:23:25.183Z",
        "_lastModifiedDateTime": "2018-12-14T15:01:02.000+0000"
    }


def encrypt(key, plaintext):
    initialisation_vector = Random.new().read(AES.block_size)
    iv_int = int(binascii.hexlify(initialisation_vector), 16)
    counter = Counter.new(AES.block_size * 8, initial_value=iv_int)
    aes = AES.new(base64.b64decode(key), AES.MODE_CTR, counter=counter)
    ciphertext = aes.encrypt(plaintext.encode("utf8"))
    return (base64.b64encode(initialisation_vector).decode("ASCII"),
            base64.b64encode(ciphertext).decode("ASCII"))


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
