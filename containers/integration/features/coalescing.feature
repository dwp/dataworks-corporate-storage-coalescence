Feature: Coalesces and does not lose any records

  Scenario: Coalesces the corporate data files, all records remain
    Given s3 has been populated
    And coalescing has been run
    Then there will be 192 files under corporate-data corporate_storage
    And there will be 110_000 corporate records therein
    And there will be an object with key corporate_storage/ucfs_audit/2020/11/05/data/businessAudit/data.businessAudit_8_207899_261800.jsonl.gz.3

  Scenario: Coalesces the manifest data files, all records remain
    Given s3 has been populated
    And coalescing has been run
    Then there will be 110 files under manifest-data business-data
    And there will be 110_000 manifest records therein
