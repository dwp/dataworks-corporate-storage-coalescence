#!/usr/bin/env python

import argparse
import sys
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, wait
from timeit import default_timer as timer

from utility.grouping import batched_object_summaries, grouped_object_summaries, successful_result
from utility.s3 import S3, s3_client


def main():
    start = timer()
    args = command_line_args()
    client = s3_client(args.localstack)
    s3 = S3(client)
    print(f"Bucket: '{args.bucket}', prefix: '{args.prefix}', partition: {args.partition}, "
          f"threads: {args.threads}, multiprocessor: {args.multiprocessor}.")
    summaries = s3.object_summaries(args.bucket, args.prefix)
    print(f"Fetch summaries, size {len(summaries)}")
    grouped = grouped_object_summaries(summaries, args.partition, args.manifests)
    print(f"Grouped, size {len(grouped)}")
    batched = batched_object_summaries(args.size, args.files, grouped)
    print("Created batches, coalescing")
    results = [coalesce_topic(args.bucket, batched[topic], args.threads, args.multiprocessor, args.localstack, args.manifests)
               for topic in batched.keys()]
    for result in results:
        print(f"Result: {result}")
    end = timer()
    print(f"Time taken: {end - start:.2f} seconds.")
    exit(0 if successful_result(results) else 2)


def coalesce_topic(bucket: str, batched_topic, threads: int, use_multiprocessor, use_localstack: bool, manifests: bool):
    with (pooled_executor(use_multiprocessor, threads)) as executor:
        start = timer()
        futures = [executor.submit(coalesce_partition, bucket, batched_topic[partition], use_localstack, manifests)
                   for partition in batched_topic]
        for future in futures:
            print(f"Future: {future}")

        wait(futures)
        executor.shutdown()
        end = timer()
        print(f"Done all batches, time taken {end - start:.2f} seconds.")
        return futures


def pooled_executor(multiprocessor, threads):
    threads_qualified = threads if threads and threads > 0 else None
    return ProcessPoolExecutor(max_workers=threads_qualified) if multiprocessor else ThreadPoolExecutor(max_workers=threads_qualified)


def coalesce_partition(bucket, partition, use_localstack: bool, manifests: bool):
    client = s3_client(use_localstack)
    s3 = S3(client)
    return [coalesce_batch(s3, bucket, batch, manifests) for batch in partition]


def coalesce_batch(s3, bucket, batch, manifests) -> bool:
    try:
        if len(batch) > 1:
            s3.coalesce_batch(bucket, batch, manifests)
            s3.delete_batch(bucket, batch)
        else:
            print("Not processing batch of size 1")
        return True
    except:
        e = sys.exc_info()[0]
        print(f"Error coalescing batch: '{e}'.", file=sys.stderr)
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

    parser.add_argument('-m', '--multiprocessor', default=False,
                        action="store_true",
                        help='Use the process pool executor.')

    parser.add_argument('-n', '--partition',
                        choices=range(-1, 19),
                        default=-1,
                        type=int,
                        help='The partition to coalesce.')

    parser.add_argument('-p', '--prefix',
                        default="corporate_storage/"
                                "ucfs_audit/2020/11/05/data/businessAudit",
                        type=str,
                        help='The common prefix.')

    parser.add_argument('-a', '--manifests', default=False,
                        action="store_true",
                        help='Coalesces streaming manifests.')

    parser.add_argument('-t', '--threads',
                        choices=range(0, 11),
                        default=0,
                        type=int,
                        help='The number of coalescing threads to run in parallel.')

    return parser.parse_args()


if __name__ == '__main__':
    main()
