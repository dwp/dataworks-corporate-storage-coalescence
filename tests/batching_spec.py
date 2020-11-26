import unittest

from utility.batching import batched_object_summaries


class BatchingSpec(unittest.TestCase):
    def test_something(self):
        topics = ["data.businessAudit", "db.database.collection"]
        partition_keys = range(9)
        record_range = range(500)
        grouped = {}
        expected_total = 0
        for topic in topics:
            grouped[topic] = {}
            for partition in partition_keys:
                grouped[topic][partition] = []
                for record in record_range:
                    expected_total += 1
                    grouped[topic][partition].append(self.__item(topic, partition, record))

        batches = batched_object_summaries(100_000, 5, grouped)
        self.assertEqual(topics, list(batches.keys()))
        actual_total = 0
        for batch in batches.keys():
            partitions = batches[batch]
            self.assertEqual(list(partition_keys), list(partitions.keys()))
            for partition_batch_key in partitions.keys():
                partition_batch = partitions[partition_batch_key]
                self.assertEqual(100, len(partition_batch))
                for sub_batch in partition_batch:
                    actual_total += len(sub_batch)
                    self.assertEqual(5, len(sub_batch))
        self.assertEqual(expected_total, actual_total)


    def __item(self, topic: str, partition: str, record: int) -> dict:
        return {
            "object_key": f"corporate_storage/ucfs_audit/2020/11/05/data/businessAudit/{topic}_{partition}_{record * 100}-{record * 100 + 99}.jsonl.gz",
            "topic": topic,
            "partition": partition,
            "start_offset": record * 100,
            "end_offset": record * 100 + 99,
            "size": 10_000
        }


if __name__ == '__main__':
    unittest.main()
