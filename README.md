# dataworks-corporate-storage-coalescence

## Coalesces corporate storage files into larger objects

### Background

#### The problem

Kafka-to-hbase polls the UC  broker and then groups the results by topic and partition.
Each of these topic/partition specific batch of records is then written to s3 as a 
single object.

These objects serve as the input to a disaster recovery mechanism. The corporate data
loader (hereinafter termed `CDL`) can load them back into hbase should a table become corrupted. 

CDL uses hbase/hadoop's off the shelf bulk loading capabilities and it adds each s3 object 
to the off-the-shelf job's inputs paths. However the shear volume of files means that when
the hbase library concatenates these into a csv (which it does) eventually java's own
limit on a string length is broken (it goes past 2 000 000 000 characters). 

#### The solution

A nightly job will coalesce these files into larger objects ensuring that there are fewer 
of them with the goal of ensuring that `CDL's` input path does not exceed the java limit 
for a string length.

## Scheduled execution

In the `dataworks-aws-ingest-consumers` repo, there are AWS batch jobs created which run this script for all our relevant storage and manifest locations in S3.

These jobs are kicked off via Cloudwatch Events on a scheduled cron.

## CI

There are two CI pipelines in this repo. Both pipelines are self updating on merges to master in GitHub but can be updated manually too for testing from branches.

### Infra pipeline

The first is the infrastructure pipeline which deploys the docker image for this script and can be updated using `aviator` command. The files for this pipeline are in the `ci/` folder.

### Execution pipeline

The second is the execution pipeline which contains jobs which allow the AWS batch jobs for this script to be kicked off ad-hoc outside of the scheduled executions. The files for this pipeline are in the `ci/utility/` folder and it can be updated by running `make update-corporate-storage-coalescer-pipeline`.

## Addendum
After cloning this repo, please run:
`make bootstrap`
