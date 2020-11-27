#!/usr/bin/env python

import argparse
import sys

import botocore

from concurrent.futures import ThreadPoolExecutor, wait
from utility.batching import batched_object_summaries
from utility.grouping import grouped_object_summaries
from utility.s3 import S3, s3_client


def main():
    args = command_line_args()
    client = s3_client(args.localstack)
    s3 = S3(client)
    print(f"Bucket: '{args.bucket}', prefix: '{args.prefix}'.")
    summaries = s3.object_summaries(args.bucket, args.prefix)
    grouped = grouped_object_summaries(summaries)
    batched = batched_object_summaries(args.size, args.files, grouped)
    [coalesce_topic(s3, args.bucket, batched[topic])
     for topic in batched.keys()]


def coalesce_topic(s3, bucket, topic):
    [coalesce_partition(s3, bucket, topic[partition]) for partition in topic]


def coalesce_partition(s3, bucket, partition, chunk_size):
    if chunk_size > 1:
        for batch_chunk in list(get_chunked_batches(partition, chunk_size)):
            [result_input for result_input in coalesce_partition_async(s3, bucket, batch_chunk)]
    else:
        [coalesce_partition_sync(s3, bucket, batch) for batch in partition]


def coalesce_partition_sync(s3, bucket, partition):
    [coalesce_batch(s3, bucket, batch) for batch in partition]


def coalesce_partition_async(s3, bucket, batch_chunk):
    with ThreadPoolExecutor(max_workers=len(batch_chunk)) as executor_input:
        future_results_input = []

        for batch in batch_chunk:
            future_results_input.append(
                executor_input.submit(
                    coalesce_batch,
                    s3,
                    bucket,
                    batch,
                )
            )

        wait(future_results_input)
        for future in future_results_input:
            try:
                yield future.result()
            except Exception as error:
                print(f"Error coalescing batch async: {error}", file=sys.stderr)


def get_chunked_batches(batch_array, chunk_size):
    for count in range(0, len(batch_array), chunk_size):
        yield batch_array[count:count+chunk_size]


def coalesce_batch(s3, bucket, batch):
    try:
        s3.coalesce_batch(bucket, batch)
        s3.delete_batch(bucket, batch)
    except botocore.exceptions.ClientError as error:
        print(f"Error coalescing batch: {error}", file=sys.stderr)
        [print(f"Failed to coalesce object: {obj}", file=sys.stderr)
         for obj in batch]


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

    parser.add_argument('-c', '--chunk-size',
                        default=1,
                        type=int,
                        help='The number of batches to process in parallel.')

    return parser.parse_args()


if __name__ == '__main__':
    main()
