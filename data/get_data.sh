#!/bin/sh

echo "Downloading swissTLMRegio 2025 dataset..."
wget https://data.geo.admin.ch/ch.swisstopo.swisstlmregio/swisstlmregio_2025/swisstlmregio_2025_2056.gdb.zip .

echo "Donwloading latest version of Veloland dataset..."
wget https://data.geo.admin.ch/ch.astra.veloland/veloland/veloland_2056.gdb.zip .