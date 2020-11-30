import re
from concurrent.futures import ThreadPoolExecutor, as_completed

import boto3
import io


def s3_client(use_localstack: bool):
    return boto3.client(service_name="s3",
                        endpoint_url="http://localstack:4566",
                        use_ssl=False,
                        aws_access_key_id="ACCESS_KEY",
                        aws_secret_access_key="SECRET_KEY") if use_localstack \
        else boto3.client(service_name="s3")


class S3:
    def __init__(self, client):
        self.client = client

    def object_summaries(self, bucket: str, prefix: str):
        objects = []
        all_retrieved = False
        token = None

        while not all_retrieved:
            results = \
                self.client.list_objects_v2(Bucket=bucket,
                                            Prefix=prefix,
                                            ContinuationToken=token) if token else self.client.list_objects_v2(
                    Bucket=bucket, Prefix=prefix)

            truncated = results['IsTruncated'] \
                if 'IsTruncated' in results \
                else False

            token = results['NextContinuationToken'] \
                if 'NextContinuationToken' in results else None

            objects += results['Contents'] if 'Contents' in results else []
            all_retrieved = not truncated

        return objects

    def coalesce_batch(self, bucket: str, batch: list):
        if len(batch) > 0:
            topic, partition, start_offset, end_offset = \
                batch[0]['topic'], batch[0]['partition'], \
                batch[0]['start_offset'], batch[-1]['end_offset']

            coalesced_filename = \
                f"{topic}_{partition}_{start_offset}_{end_offset}.jsonl.gz"

            prefix = re.compile(r"/[^/]+$").sub("", batch[0]['object_key'])
            coalesced_key = f"{prefix}/{coalesced_filename}"
            coalesced_contents = self.__coalesced(bucket, batch)
            self.upload(bucket, coalesced_key, coalesced_contents)
            print(f"Put coalesced batch into s3 {coalesced_key}.")

    def upload(self, bucket, key, contents):
        def progress(x): print(f"Uploading {key}, sent {x}/{len(contents)} bytes.")
        self.client.upload_fileobj(io.BytesIO(contents), bucket, key, Callback=progress)

    def delete_batch(self, bucket: str, batch: list):
        if len(batch) > 0:
            if len(batch) < self.MAX_DELETE_BATCH_SIZE + 1:
                deletes = [{'Key': item['object_key']} for item in batch]
                objects = {'Objects': deletes}
                self.client.delete_objects(Bucket=bucket, Delete=objects)
                print(f"Deleted batch of {len(batch)} items")
            else:
                sub_batches = [batch[i:i + self.MAX_DELETE_BATCH_SIZE]
                               for i in range(0, len(batch),
                                              self.MAX_DELETE_BATCH_SIZE)]
                for sub_batch in sub_batches:
                    print(f"Processing sub-batch: {len(sub_batch)}")
                    self.delete_batch(bucket, sub_batch)

    def __coalesced(self, bucket: str, batch: list) -> bytes:
        coalesced = None
        results = [future.result() for future in self.__uncoalesced_objects(bucket, batch)]
        filename_re = re.compile(r"/[.\w]+_\d+_(\d+)-\d+\.jsonl\.gz$")
        sorted_contents = [xs[1] for xs in sorted(results, key=lambda x: int(filename_re.findall(x[0])[0]))]
        for contents in sorted_contents:
            coalesced = contents if not coalesced else coalesced + contents
        return coalesced

    def __uncoalesced_objects(self, bucket, batch):
        with (ThreadPoolExecutor()) as executor:
            return as_completed(
                [executor.submit(self.__uncoalesced_object_contents, bucket, item["object_key"]) for item in
                 batch])

    def __uncoalesced_object_contents(self, bucket, key):
        s3_object = self.client.get_object(Bucket=bucket, Key=key)
        contents = self.__object_contents(s3_object)
        return key, contents

    @staticmethod
    def __object_contents(s3_object: dict) -> bytes:
        stream = s3_object['Body']
        try:
            contents = None
            for chunk in stream.iter_chunks():
                contents = chunk if not contents else contents + chunk
            return contents
        finally:
            stream.close()

    MAX_DELETE_BATCH_SIZE = 1_000
