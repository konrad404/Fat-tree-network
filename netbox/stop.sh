#!/bin/bash

docker stop $(docker ps | awk '{print $1}' | tail -n +2)
