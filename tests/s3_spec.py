import unittest
from datetime import datetime
from functools import reduce
from unittest.mock import Mock, MagicMock, call, ANY

from botocore.exceptions import ClientError
from botocore.response import StreamingBody

from utility.s3 import S3, s3_client

date_format = "%Y-%m-%d"
test_prefix = "test-prefix-1"


class S3Spec(unittest.TestCase):

    def setUp(self):
        self.bucket = 'bucket'

    def test_coalesce(self):
        client = self.__client()
        s3 = S3(client)
        s3.coalesce_batch(self.bucket, self.__batch(), False)
        key = "corporate_storage/ucfs_audit/2020/11/05/data/businessAudit/data.businessAudit_2_0_99999.jsonl.gz"
        client.upload_fileobj.assert_called_once_with(ANY, self.bucket, key)

    def test_no_overwrite(self):
        client = self.__client()
        s3 = S3(client)

        def exists(**kwargs):
            if kwargs['Key'].endswith("gz") or kwargs['Key'].endswith("gz.2"):
                return MagicMock()
            raise MagicMock(ClientError)

        client.head_object = Mock(side_effect=exists)
        s3.coalesce_batch(self.bucket, self.__batch(), False)
        key = "corporate_storage/ucfs_audit/2020/11/05/data/businessAudit/data.businessAudit_2_0_99999.jsonl.gz.3"
        client.upload_fileobj.assert_called_once_with(ANY, self.bucket, key)

    def test_object_summaries(self):
        client = s3_client(True)
        s3 = S3(client)
        objects = [self.__summaries(x) for x in range(10)]
        contents = [x['Contents'] for x in [xs for xs in [ys for ys in objects]]]
        expected = reduce(lambda acc, xs: acc + xs, contents)
        objects[-1]['IsTruncated'] = False
        client.list_objects_v2 = Mock(side_effect=objects)
        actual = []
        for sub_batch in s3.object_summaries(self.bucket, 'prefix', 5):
            actual += sub_batch
        self.assertEqual(expected, actual)

    def test_batches_are_deleted(self):
        batch = [{'object_key': f'prefix/{i}'} for i in range(5)]
        deletes = [{'Key': x['object_key']} for x in batch]
        calls = [call(Bucket=self.bucket, Delete={'Objects': deletes})]
        client = s3_client(True)
        client.delete_objects = MagicMock(return_value={})
        s3 = S3(client)
        s3.delete_batch(self.bucket, batch)
        client.delete_objects.assert_has_calls(calls)

    def test_batches_are_deleted_in_chunks(self):
        batch = [{'object_key': f'prefix/{i}'} for i in range(3500)]
        sub_batch1 = [{'Key': f'prefix/{i}'} for i in range(1000)]
        sub_batch2 = [{'Key': f'prefix/{i}'} for i in range(1000, 2000)]
        sub_batch3 = [{'Key': f'prefix/{i}'} for i in range(2000, 3000)]
        sub_batch4 = [{'Key': f'prefix/{i}'} for i in range(3000, 3500)]
        calls = [call(Bucket=self.bucket, Delete={'Objects': x}) for x in
                 [sub_batch1, sub_batch2, sub_batch3, sub_batch4]]
        client = s3_client(True)
        client.delete_objects = MagicMock(return_value={})
        s3 = S3(client)
        s3.delete_batch(self.bucket, batch)
        client.delete_objects.assert_has_calls(calls)

    def test_get_full_prefix_when_not_set(self):
        prefix = test_prefix
        expected = test_prefix
        date_to_add = "NOT_SET"
        today = datetime.strptime("2020-09-01", date_format)
        client = s3_client(True)
        s3 = S3(client)
        actual = s3.get_full_s3_prefix(prefix, date_to_add, today)
        self.assertEqual(expected, actual)

    def test_get_full_prefix_when_not_set_with_end_slash(self):
        prefix = f"{test_prefix}/"
        expected = f"{test_prefix}/"
        date_to_add = "NOT_SET"
        today = datetime.strptime("2020-09-01", date_format)
        client = s3_client(True)
        s3 = S3(client)
        actual = s3.get_full_s3_prefix(prefix, date_to_add, today)
        self.assertEqual(expected, actual)

    def test_get_full_prefix_when_set_to_today(self):
        prefix = test_prefix
        expected = f"{test_prefix}/2020/09/01"
        date_to_add = "today"
        today = datetime.strptime("2020-09-01", date_format)
        client = s3_client(True)
        s3 = S3(client)
        actual = s3.get_full_s3_prefix(prefix, date_to_add, today)
        self.assertEqual(expected, actual)

    def test_get_full_prefix_when_set_to_today_with_end_slash(self):
        prefix = f"{test_prefix}/"
        expected = f"{test_prefix}/2020/09/01"
        date_to_add = "today"
        today = datetime.strptime("2020-09-01", date_format)
        client = s3_client(True)
        s3 = S3(client)
        actual = s3.get_full_s3_prefix(prefix, date_to_add, today)
        self.assertEqual(expected, actual)

    def test_get_full_prefix_when_set_to_yesterday(self):
        prefix = test_prefix
        expected = f"{test_prefix}/2020/08/31"
        date_to_add = "yesterday"
        today = datetime.strptime("2020-09-01", date_format)
        client = s3_client(True)
        s3 = S3(client)
        actual = s3.get_full_s3_prefix(prefix, date_to_add, today)
        self.assertEqual(expected, actual)

    def test_get_full_prefix_when_set_to_yesterday_with_end_slash(self):
        prefix = f"{test_prefix}/"
        expected = f"{test_prefix}/2020/08/31"
        date_to_add = "yesterday"
        today = datetime.strptime("2020-09-01", date_format)
        client = s3_client(True)
        s3 = S3(client)
        actual = s3.get_full_s3_prefix(prefix, date_to_add, today)
        self.assertEqual(expected, actual)

    def __client(self):
        objects = [self.__s3_object_with_body(i) for i in range(1000)]
        client = s3_client(True)
        client.get_object = Mock(side_effect=objects)
        client.upload_fileobj = Mock()
        return client

    def __batch(self):
        return [self.__batch_item(i) for i in range(1000)]

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
            "object_key": f"corporate_storage/ucfs_audit/2020/11/05/data/businessAudit/"
                          f"data.businessAudit_2_{i}-190299.jsonl.gz",
            "topic": "data.businessAudit",
            "partition": 2,
            "start_offset": i * 100,
            "end_offset": i * 100 + 99,
            "size": 10_000
        }

    def __s3_object_with_body(self, i: int) -> dict:
        body = StreamingBody(raw_stream=MagicMock(), content_length=100)
        rv = self.__s3_object_contents(i)
        body.read = MagicMock(return_value=rv)
        return dict(Body=body)

    @staticmethod
    def __s3_object_contents(i: int) -> bytes:
        return f"S3 OBJECT CONTENTS {i}\n".encode()


if __name__ == '__main__':
    unittest.main()
