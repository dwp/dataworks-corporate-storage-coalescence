import gzip
import base64
import binascii
import gzip
import json

from Crypto import Random
from Crypto.Cipher import AES
from Crypto.Util import Counter


def corporate_key(args, batch_number, end_offset, start_offset):
    cluster = f"{args.cluster}." if args.cluster else ""
    return f"{args.prefix}/{args.database}/{args.collection}/" \
           f"{cluster}{args.database}.{args.collection}_{batch_number % 10}_{start_offset}-{end_offset}.jsonl.gz"


def corporate_batch(args, batch_number):
    batch = [kafka_message(args.database, args.collection, batch_number, record_number) for record_number in
             range(args.record_count)]
    accumulated = "\n".join([f"{x}" for x in batch])
    return gzip.compress(f"{accumulated}\n".encode("ASCII"))


def kafka_message(database: str, collection: str, batch_number: int, record_number: int):
    key = "53Et7AKlQa1ifNCb/PY5iA=="
    db_object = plaintext_db_object(batch_number, record_number)
    iv, encrypted = encrypt(key, json.dumps(db_object))
    return {
        "traceId": f"{batch_number:05d}/{record_number:05d}",
        "unitOfWorkId": f"{record_number:05d}",
        "@type": "V4",
        "message": {
            "db": f"{database}",
            "collection": f"{collection}",
            "_id": {
                "record_id": f"{record_number:05d}",
                "batch_id": f"{batch_number:05d}"
            },
            "_timeBasedHash": "hash",
            "@type": "MONGO_INSERT",
            "_lastModifiedDateTime": "2018-12-14T15:01:02.000+0000",
            "encryption": {
                "encryptionKeyId": "cloudhsm:1,2",
                "encryptedEncryptionKey": key,
                "initialisationVector": iv,
                "keyEncryptionKeyId": "cloudhsm:1,2"
            },
            "dbObject": f'"{encrypted}"'
        },
        "version": "core-4.master.9790",
        "timestamp": "2019-07-04T07:27:35.104+0000"
    }


def plaintext_db_object(batch_number: int, record_number: int):
    return {
        "_id": {
            "record_id": f"{record_number:05d}",
            "batch_id": f"{batch_number:05d}"
        },
        "createdDateTime": "2015-03-20T12:23:25.183Z",
        "_lastModifiedDateTime": "2018-12-14T15:01:02.000+0000"
    }


def encrypt(key, plaintext):
    initialisation_vector = Random.new().read(AES.block_size)
    iv_int = int(binascii.hexlify(initialisation_vector), 16)
    counter = Counter.new(AES.block_size * 8, initial_value=iv_int)
    aes = AES.new(base64.b64decode(key), AES.MODE_CTR, counter=counter)
    ciphertext = aes.encrypt(plaintext.encode("utf8"))
    return (base64.b64encode(initialisation_vector).decode("ASCII"),
            base64.b64encode(ciphertext).decode("ASCII"))
