#!/bin/bash

cd frontend
npm run build
rm -rf static && cp -R dist static 
