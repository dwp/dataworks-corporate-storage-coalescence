Feature: Coalesces and does not lose any records

  Scenario: Coalesces the files, all records remain
    Given s3 has been populated
    And coalescing has been run
    Then there will be 190 files under corporate-data corporate_storage
    And there will be 110_000 records therein
