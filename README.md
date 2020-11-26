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

## Addendum
After cloning this repo, please run:
`make bootstrap`
