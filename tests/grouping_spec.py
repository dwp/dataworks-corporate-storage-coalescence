import unittest
from utility.grouping import grouped_object_summaries


class GroupingSpec(unittest.TestCase):
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
    def __object_summary(collection: str, partition: str, i: int) -> dict:
        return {
            "Key": f"corporate_storage/ucfs_audit/2020/11/05/database/{collection}/db.database.{collection}_{partition}_{i * 100}-{i * 100 + 99}.jsonl.gz",
            "Size": 100
        }


if __name__ == '__main__':
    unittest.main()
