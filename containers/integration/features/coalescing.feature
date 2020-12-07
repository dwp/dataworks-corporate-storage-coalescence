Feature: Coalesces and does not lose any records

  Scenario: Coalesces the files, all records remain
    Given s3 has been populated
    And coalescing has been run
    Then there will be 192 files under corporate-data corporate_storage
    And there will be 110_000 records therein
    And there will be an object with key corporate_storage/ucfs_audit/2020/11/05/data/businessAudit/data.businessAudit_8_272800_328899.jsonl.gz.3
