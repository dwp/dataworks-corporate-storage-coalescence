#!/usr/bin/env bash

./main.py -lm

for partition in {0..9}; do
  ./main.py -lma -b manifest-data -n $partition -p business-data/manifest/streaming/main
done
