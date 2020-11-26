import re


def grouped_object_summaries(summaries: list) -> dict:
    filename_re = re.compile(r"/([.\w]+)_(\d+)_(\d+)-(\d+)\.jsonl\.gz$")
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
