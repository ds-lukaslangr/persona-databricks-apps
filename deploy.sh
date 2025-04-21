#!/bin/bash

source build_frontend.sh

databricks sync . /Workspace/Users/lukas.langr@datasentics.com/persona-demo

databricks apps deploy persona-demo --source-code-path /Workspace/Users/lukas.langr@datasentics.com/persona-demo
