#!/bin/bash

# Run Online Bin Packing example with various methods
#
# Usage:
#   ./run_online_bin_packing.sh funsearch        # Run FunSearch
#   ./run_online_bin_packing.sh openevolve       # Run OpenEvolve
#   ./run_online_bin_packing.sh eoh             # Run EoH
#   ./run_online_bin_packing.sh one_plus_one_eps # Run (1+1)-EPS
#   ./run_online_bin_packing.sh mcts_ahd        # Run MCTS-AHD
#   ./run_online_bin_packing.sh partevo         # Run PartEvo
#   ./run_online_bin_packing.sh randsample      # Run RandSample
#   ./run_online_bin_packing.sh reevo           # Run ReEvo
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

echo "Running Online Bin Packing with $METHOD..."
echo "Config: $CONFIG_FILE"
echo ""

algodisco run "$METHOD" --config "$CONFIG_FILE" "${@:2}"
