#!/usr/bin/env bash

source ./environment.sh

main() {
  init
  create_corporate_data_bucket
  put_objects_in_bucket
}

main
