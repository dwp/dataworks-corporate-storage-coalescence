#!/usr/bin/env python

import argparse
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

from botocore.exceptions import ClientError

from utility.grouping import batched_object_summaries, grouped_object_summaries, successful_result
from utility.s3 import S3, s3_client


def main():
    args = command_line_args()
    client = s3_client(args.localstack)
    s3 = S3(client)
    print(f"Bucket: '{args.bucket}', prefix: '{args.prefix}'.")
    summaries = s3.object_summaries(args.bucket, args.prefix)
    grouped = grouped_object_summaries(summaries)
    batched = batched_object_summaries(args.size, args.files, grouped)
    results = [coalesce_topic(s3, args.bucket, batched[topic], args.threads)
               for topic in batched.keys()]
    exit(0 if successful_result(results) else 5)


def coalesce_topic(s3, bucket: str, batched_topic, threads: int):
    with (ThreadPoolExecutor(max_workers=threads)) as executor:
        return as_completed([executor.submit(coalesce_partition, s3, bucket, batched_topic[partition])
                             for partition in batched_topic])


def coalesce_partition(s3, bucket, partition):
    return [coalesce_batch(s3, bucket, batch) for batch in partition]


def coalesce_batch(s3, bucket, batch) -> bool:
    try:
        if len(batch) > 1:
            s3.coalesce_batch(bucket, batch)
            s3.delete_batch(bucket, batch)
        else:
            print("Not processing batch of size 1")
        return True
    except ClientError as error:
        print(f"Error coalescing batch: '{error}'.", file=sys.stderr)
        return False


def command_line_args():
    parser = \
        argparse.ArgumentParser(description='Coalesces corporate data files.')

    parser.add_argument('-b', '--bucket', default="corporate-data", type=str,
                        help='The target bucket.')

    parser.add_argument('-f', '--files', default=10, type=int,
                        help='The maximum number of files '
                             'to coalesce into one.')

    parser.add_argument('-s', '--size', default=100_000, type=int,
                        help='The maximum size in bytes of a coalesced file.')

    parser.add_argument('-l', '--localstack', default=False,
                        action="store_true",
                        help='Target localstack instance.')

    parser.add_argument('-p', '--prefix',
                        default="corporate_storage/"
                                "ucfs_audit/2020/11/05/data/businessAudit",
                        type=str,
                        help='The common prefix.')

    parser.add_argument('-t', '--threads',
                        default=1,
                        choices=range(1, 11),
                        type=int,
                        help='The number of coalescing threads to run in parallel.')

    return parser.parse_args()


if __name__ == '__main__':
    main()
