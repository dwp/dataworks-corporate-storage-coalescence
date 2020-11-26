import unittest
from functools import reduce
from unittest.mock import Mock, MagicMock, call

from botocore.response import StreamingBody

from utility.s3 import S3, s3_client


class S3Spec(unittest.TestCase):

    def test_coalesce(self):
        batch = [self.__batch_item(i) for i in range(1000)]
        objects = [self.__s3_object_with_body(i) for i in range(1000)]
        contents = [self.__s3_object_contents(i) for i in range(1000)]
        coalesced = reduce(lambda acc, x: acc + x, contents, "")
        client = s3_client(True)
        client.get_object = Mock(side_effect=objects)
        client.put_object = Mock()
        s3 = S3(client)
        s3.coalesce_batch('bucket', batch)
        client.put_object.assert_called_once_with(Bucket="bucket",
                                                  Key="corporate_storage/ucfs_audit/2020/11/05/data/businessAudit/data.businessAudit_2_0_99999.jsonl.gz",
                                                  Body=coalesced,
                                                  ContentLength=len(coalesced),
                                                  ContentType="application/gzip")

    def test_object_summaries(self):
        client = s3_client(True)
        s3 = S3(client)
        objects = [self.__summaries(x) for x in range(10)]
        contents = [x['Contents'] for x in [xs for xs in [ys for ys in objects]]]
        expected = reduce(lambda acc, xs: acc + xs, contents)
        objects[-1]['IsTruncated'] = False
        client.list_objects_v2 = Mock(side_effect=objects)
        actual = s3.object_summaries('bucket', 'prefix')
        self.assertEqual(expected, actual)

    @staticmethod
    def test_batches_are_deleted():
        batch = [{'object_key': f'prefix/{i}'} for i in range(5)]
        deletes = [{'Key': x['object_key']} for x in batch]
        calls = [call(Bucket='bucket', Delete={'Objects': deletes})]
        client = s3_client(True)
        client.delete_objects = MagicMock(return_value={})
        s3 = S3(client)
        s3.delete_batch("bucket", batch)
        client.delete_objects.assert_has_calls(calls)

    @staticmethod
    def test_batches_are_deleted_in_chunks():
        batch = [{'object_key': f'prefix/{i}'} for i in range(3500)]
        sub_batch1 = [{'Key': f'prefix/{i}'} for i in range(1000)]
        sub_batch2 = [{'Key': f'prefix/{i}'} for i in range(1000, 2000)]
        sub_batch3 = [{'Key': f'prefix/{i}'} for i in range(2000, 3000)]
        sub_batch4 = [{'Key': f'prefix/{i}'} for i in range(3000, 3500)]
        calls = [call(Bucket='bucket', Delete={'Objects': x}) for x in [sub_batch1, sub_batch2, sub_batch3, sub_batch4]]
        client = s3_client(True)
        client.delete_objects = MagicMock(return_value={})
        s3 = S3(client)
        s3.delete_batch("bucket", batch)
        client.delete_objects.assert_has_calls(calls)

    def __summaries(self, index: int) -> dict:
        return {'IsTruncated': True, 'NextContinuationToken': index, 'Contents': self.__contents(index)}

    def __contents(self, index: int) -> list:
        return [self.__s3_object(index, x) for x in range(100)]

    @staticmethod
    def __s3_object(summary_index, content_index):
        return {'Key': f"{summary_index}/{content_index}", 'Size': 100}

    @staticmethod
    def __batch_item(i: int) -> dict:
        return {
            "object_key": "corporate_storage/ucfs_audit/2020/11/05/data/businessAudit/data.businessAudit_2_189200-190299.jsonl.gz",
            "topic": "data.businessAudit",
            "partition": 2,
            "start_offset": i * 100,
            "end_offset": i * 100 + 99,
            "size": 10_000
        }

    def __s3_object_with_body(self, i: int) -> dict:
        body = StreamingBody(raw_stream=MagicMock(), content_length=100)
        body.iter_chunks = MagicMock(return_value=self.__s3_object_contents(i))
        return dict(Body=body)

    @staticmethod
    def __s3_object_contents(i: int) -> str:
        return f"S3 OBJECT CONTENTS {i}\n"


if __name__ == '__main__':
    unittest.main()
