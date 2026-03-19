#!/bin/bash

# Run Online Bin Packing example with various methods
#
# Usage:
#   ./run_online_bin_packing.sh funsearch        # Run FunSearch
#   ./run_online_bin_packing.sh openevolve       # Run OpenEvolve
#   ./run_online_bin_packing.sh eoh             # Run EoH
#   ./run_online_bin_packing.sh one_plus_one_eps # Run (1+1)-EPS
#   ./run_online_bin_packing.sh randsample      # Run RandSample
#   ./run_online_bin_packing.sh behavesim       # Run BehaveSim
#
# For SwanLab version:
#   ./run_online_bin_packing.sh funsearch_swanlab
#
# Before running:
#   1. Copy config and fill in your API keys:
#      cp examples/online_bin_packing/configs/<method>.yaml examples/online_bin_packing/configs/my_config.yaml
#   2. Edit the config and replace "null" with your API keys
#
# Environment variables (alternative to editing config):
#   export OPENAI_API_KEY="your-openai-key"
#   export SWANLAB_API_KEY="your-swanlab-key"

METHOD="${1:-funsearch}"
CONFIG_FILE="examples/online_bin_packing/configs/${METHOD}.yaml"

# Map method names to their module paths
case "$METHOD" in
    funsearch|funsearch_swanlab)
        MODULE="adlab.methods.funsearch.main_funsearch"
        ;;
    openevolve)
        MODULE="adlab.methods.openevolve.main_openevolve"
        ;;
    eoh)
        MODULE="adlab.methods.eoh.main_eoh"
        ;;
    one_plus_one_eps)
        MODULE="adlab.methods.one_plus_one_eps.main_one_plus_one_eps"
        ;;
    randsample)
        MODULE="adlab.methods.randsample.main_randsample"
        ;;
    behavesim)
        MODULE="adlab.methods.behavesim_search.main_behavesim_search"
        ;;
    *)
        echo "Unknown method: $METHOD"
        echo "Available methods: funsearch, openevolve, eoh, one_plus_one_eps, randsample, behavesim, funsearch_swanlab"
        exit 1
        ;;
esac

echo "Running Online Bin Packing with $METHOD..."
echo "Config: $CONFIG_FILE"
echo "Module: $MODULE"
echo ""

python -m "$MODULE" --config "$CONFIG_FILE"
