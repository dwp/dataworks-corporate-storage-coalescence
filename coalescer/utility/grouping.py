import re
import sys
import traceback
from typing import Optional


def grouped_object_summaries(summaries: list, partition_number: Optional[int], manifests: bool) -> dict:
    filename_re = re.compile(manifest_filename_pattern(partition_number) if manifests
                             else filename_pattern(partition_number))
    grouped = {}
    for summary in summaries:
        object_key = summary['Key']
        match = filename_re.findall(object_key)
        if match and len(match) == 1:
            start_topic, end_topic, topic = (None, None, None)

            if manifests:
                start_topic, partition, start, end_topic, end = filename_re.findall(object_key)[0]
            else:
                topic, partition, start, end = filename_re.findall(object_key)[0]

            partition = int(partition)

            grouping_key = "manifests" if manifests else topic

            if grouping_key not in grouped:
                grouped[grouping_key] = {}

            if partition not in grouped[grouping_key]:
                grouped[grouping_key][partition] = []

            grouped[grouping_key][partition].append({
                'object_key': object_key,
                'topic': topic,
                'start_topic': start_topic,
                'end_topic': end_topic,
                'partition': partition,
                'start_offset': int(start),
                'end_offset': int(end),
                'size': summary['Size']})

    for topic in grouped.keys():
        for partition in grouped[topic]:
            keys = grouped[topic][partition]
            grouped[topic][partition] = \
                sorted(keys, key=lambda x: x['start_offset'])

    return grouped


def filename_pattern(partition: Optional[int]) -> str:
    return r"/([.\w]+)_(\d+)_(\d+)-(\d+)\.jsonl\.gz$" if partition is None or partition < 0 \
        else r"/([.\w]+)_" + f"({partition})" + r"_(\d+)-(\d+)\.jsonl\.gz$"


def manifest_filename_pattern(partition: Optional[int]) -> str:
    return r"([-.\w]+)_(\d+)_(\d+)-([-.\w]+)_\d+_(\d+).txt" if partition is None or partition < 0 \
        else r"([-.\w]+)_" + f"({partition})" + r"_(\d+)-([-.\w]+)_" + f"{partition}" + r"_(\d+).txt"


def batched_object_summaries(max_size: int,
                             max_count: int,
                             grouped: dict) -> dict:
    batches = {}
    for topic in grouped.keys():
        print(f"Creating batches for {topic}")
        batches[topic] = {}
        for partition in grouped[topic].keys():
            print(f"Creating batches for {topic}/{partition}")
            current_batch, current_batch_size, current_batch_count = [], 0, 0
            objects = grouped[topic][partition]
            batches[topic][partition] = []

            for obj in objects:
                current_batch.append(obj)
                current_batch_size += obj['size']
                current_batch_count += 1
                if current_batch_size >= max_size or \
                        current_batch_count >= max_count:
                    batches[topic][partition].append(current_batch)
                    print(f"Appending batch of size {len(current_batch)} to {topic}/{partition}, no. of batches is {len(batches[topic][partition])}")
                    current_batch, current_batch_size, current_batch_count = \
                        [], 0, 0

            if len(current_batch) > 0:
                batches[topic][partition].append(current_batch)
                print(f"Appending batch of size {len(current_batch)} to {topic}/{partition}, no. of batches is {len(batches[topic][partition])}")

    return batches


def successful_result(results, parallel_batches):
    all_succeeded = True
    for futures in results:
        for future in futures:
            try:
                result = future.result()
                failures_exist = result if parallel_batches else any(x is False for x in result)
                if failures_exist:
                    all_succeeded = False
            except:
                traceback.print_exc(file=sys.stdout)
                print(f"Future failed with exception: '{future.exception()}'")
                all_succeeded = False

    return all_succeeded
