import re
from typing import Optional


def grouped_object_summaries(summaries: list, partition_number: Optional[int]) -> dict:
    filename_re = re.compile(filename_pattern(partition_number))
    grouped = {}
    for summary in summaries:
        object_key = summary['Key']
        match = filename_re.findall(object_key)
        if match and len(match) == 1:
            topic, partition, start, end = filename_re.findall(object_key)[0]
            partition = int(partition)
            if topic not in grouped:
                grouped[topic] = {}

            if partition not in grouped[topic]:
                grouped[topic][partition] = []

            grouped[topic][partition].append({
                'object_key': object_key,
                'topic': topic,
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


def filename_pattern(partition: int):
    return r"/([.\w]+)_" + f"({partition})" + r"_(\d+)-(\d+)\.jsonl\.gz$" if partition \
        else r"/([.\w]+)_(\d+)_(\d+)-(\d+)\.jsonl\.gz$"


def batched_object_summaries(max_size: int,
                             max_count: int,
                             grouped: dict) -> dict:
    batches = {}
    for topic in grouped.keys():
        batches[topic] = {}
        for partition in grouped[topic].keys():
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
                    current_batch, current_batch_size, current_batch_count = \
                        [], 0, 0

            if len(current_batch) > 0:
                batches[topic][partition].append(current_batch)

    return batches


def successful_result(results):
    all_succeeded = True
    for futures in results:
        for future in futures:
            try:
                result = future.result()
                failures_exist = any(x is False for x in result)
                if failures_exist:
                    all_succeeded = False
            except:
                print(f"Future failed with exception: '{future.exception()}'")
                all_succeeded = False

    return all_succeeded
