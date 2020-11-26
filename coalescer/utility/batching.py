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
