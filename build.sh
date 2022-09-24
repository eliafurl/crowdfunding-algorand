#!/usr/bin/env bash

BUILD_PATH="./build/" 

mkdir -p $BUILD_PATH
# clean
rm -f $BUILD_PATH*.teal

#set -e # die on error

python3 ./contracts/"$1" "$BUILD_PATH"approval.teal "$BUILD_PATH"clear.teal "$BUILD_PATH"interface.json