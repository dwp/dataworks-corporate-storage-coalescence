import unittest
from asyncio import Future

from utility.grouping import batched_object_summaries, grouped_object_summaries, successful_result


class GroupingSpec(unittest.TestCase):

    def test_successful_resolved_results(self):
        self.assertEqual(True, successful_result(self.__generators()))

    def test_failed_resolved_results(self):
        self.assertEqual(False, successful_result(self.__generators(with_failure=True)))

    @staticmethod
    def __future(has_failure=False):
        future = Future()
        result = [True] * 10
        result[5] = False if has_failure else True
        future.set_result(result)
        return future

    def test_batching(self):
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

    def test_grouping(self):
        object_summaries = []
        for collection in ["collection1", "collection2"]:
            for partition in range(10):
                for i in range(100):
                    object_summaries.append(self.__object_summary(collection, partition, i))
        result = grouped_object_summaries(object_summaries)
        self.assertEqual(["db.database.collection1", "db.database.collection2"], list(result.keys()))
        for topic in list(result.keys()):
            partition_batch = result[topic]
            self.assertEqual([0, 1, 2, 3, 4, 5, 6, 7, 8, 9], list(partition_batch.keys()))
            for partition in list(partition_batch.keys()):
                items = partition_batch[partition]
                for item in items:
                    self.assertEqual(topic, item['topic'])
                    self.assertEqual(partition, item['partition'])
                    start_offset = item['start_offset']
                    end_offset = item['end_offset']
                    collection = topic.replace("db.database.", "")
                    self.assertEqual(
                        f"corporate_storage/ucfs_audit/2020/11/05/database/{collection}/{topic}_{partition}_{start_offset}-{end_offset}.jsonl.gz",
                        item['object_key'])

    @staticmethod
    def __object_summary(collection: str, partition: int, i: int) -> dict:
        return {
            "Key": f"corporate_storage/ucfs_audit/2020/11/05/database/{collection}/db.database.{collection}_{partition}_{i * 100}-{i * 100 + 99}.jsonl.gz",
            "Size": 100
        }

    @staticmethod
    def __item(topic: str, partition: int, record: int) -> dict:
        return {
            "object_key": f"corporate_storage/ucfs_audit/2020/11/05/data/businessAudit/{topic}_{partition}_{record * 100}-{record * 100 + 99}.jsonl.gz",
            "topic": topic,
            "partition": partition,
            "start_offset": record * 100,
            "end_offset": record * 100 + 99,
            "size": 10_000
        }

    def __generators(self, with_failure=False):
        return [self.__generator(with_failure=with_failure) for _ in range(2)]

    def __generator(self, with_failure=False):
        for _ in range(10):
            yield self.__future(with_failure)


if __name__ == '__main__':
    unittest.main()
