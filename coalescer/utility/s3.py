import io
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from timeit import default_timer as timer

import boto3


def s3_client(use_localstack: bool):
    max_attempts = 4 if use_localstack else 25
    config = Config(
        retries = {
            'max_attempts': max_attempts,
            'mode': 'standard'
        }
    )
    return boto3.client(service_name="s3",
                        endpoint_url="http://localstack:4566",
                        use_ssl=False,
                        aws_access_key_id="ACCESS_KEY",
                        aws_secret_access_key="SECRET_KEY") if use_localstack \
        else boto3.client(service_name="s3", config=config)


class S3:
    def __init__(self, client):
        self.client = client

    def object_summaries(self, bucket: str, prefix: str, batch_size: int):
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

            if 'Contents' in results:
                objects += [{"Key": x['Key'], "Size": x['Size']} for x in results['Contents']]

            if len(objects) > batch_size:
                print(f"Fetched {len(objects)} summaries from {bucket}/{prefix}.")
                yield objects
                objects = []

            all_retrieved = not truncated

        yield objects

    def coalesce_batch(self, bucket: str, batch: list, manifests: bool):
        if batch and len(batch) > 0:
            start = timer()
            partition, start_offset, end_offset = batch[0]['partition'], batch[0]['start_offset'], batch[-1]['end_offset']

            start_topic = batch[0]['start_topic'] if 'start_topic' in batch[0] else None
            end_topic = batch[-1]['end_topic'] if 'end_topic' in batch[-1] else None
            topic = batch[0]['topic'] if 'topic' in batch[0] else None

            coalesced_filename = f"{start_topic}_{partition}_{start_offset}_{end_topic}_{partition}_{end_offset}.txt" if manifests \
                else f"{topic}_{partition}_{start_offset}_{end_offset}.jsonl.gz"

            prefix = re.compile(r"/[^/]+$").sub("", batch[0]['object_key'])
            coalesced_key = self.__coalesced_key(bucket, f"{prefix}/{coalesced_filename}")
            coalesced_contents = self.__coalesced(bucket, batch, manifests)
            if coalesced_contents:
                self.__upload(bucket, coalesced_key, coalesced_contents)
                end = timer()
                print(f"Put coalesced batch into s3 {coalesced_key}, "
                      f"size {len(coalesced_contents)}, time taken {end - start:.2f} seconds.")

    def delete_batch(self, bucket: str, batch: list):
        if batch and len(batch) > 0:
            start = timer()
            if len(batch) < self.MAX_DELETE_BATCH_SIZE + 1:
                deletes = [{'Key': item['object_key']} for item in batch]
                objects = {'Objects': deletes}
                self.client.delete_objects(Bucket=bucket, Delete=objects)
            else:
                sub_batches = [batch[i:i + self.MAX_DELETE_BATCH_SIZE]
                               for i in range(0, len(batch),
                                              self.MAX_DELETE_BATCH_SIZE)]
                for sub_batch in sub_batches:
                    if sub_batch:
                        print(f"Processing sub-batch: {len(sub_batch)}")
                        self.delete_batch(bucket, sub_batch)
            end = timer()
            print(f"Deleted batch of {len(batch)} items, time taken {end - start:.2f} seconds.")

    def __upload(self, bucket, key, contents):
        if contents:
            start = timer()
            self.client.upload_fileobj(io.BytesIO(contents), bucket, key)
            end = timer()
            print(f"Uploaded {bucket}/{key}, size {len(contents)} time taken {end - start:.2f} seconds.")

    def __coalesced(self, bucket: str, batch: list, manifests: bool) -> bytes:
        start = timer()
        coalesced = None

        results = []
        for future in self.__uncoalesced_objects(bucket, batch):
            try:
                results.append(future.result())
            except:
                print(f"Failed to fetch object '{future.exception()}', {future}")

        filename_re = re.compile(r"/[.\w]+_\d+_(\d+)-\d+\.jsonl\.gz$")

        sorted_contents = [xs[1] for xs in results] if manifests \
            else [xs[1] for xs in sorted(results, key=lambda x: int(filename_re.findall(x[0])[0]))]

        for contents in sorted_contents:
            coalesced = contents if not coalesced else coalesced + contents
        end = timer()

        if coalesced:
            print(f"Fetched and coalesced batch of {len(batch)} items, "
                  f"size {len(coalesced)}, "
                  f"time taken {end - start:.2f} seconds.")
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

    def __coalesced_key(self, bucket, key):
        if not self.__exists(bucket, key):
            return key
        filename_re = re.compile(r"\.jsonl\.gz\.(\d+)$")
        matches = filename_re.findall(key)
        next_index = int(matches[0]) + 1 if matches else 2
        next_key = re.compile(r"\.(\d+)$").sub("", key) + f".{next_index}"
        return self.__coalesced_key(bucket, next_key)

    @staticmethod
    def __object_contents(s3_object: dict) -> bytes:
        stream = s3_object['Body']
        try:
            return stream.read()
        finally:
            stream.close()

    def __exists(self, bucket: str, key: str) -> bool:
        try:
            head = self.client.head_object(Bucket=bucket, Key=key)
            return head is not None
        except:
            return False

    MAX_DELETE_BATCH_SIZE = 1_000
