#!/bin/sh

echo "Downloading swissTLMRegio 2022 dataset..."
wget https://data.geo.admin.ch/ch.swisstopo.swisstlmregio/swisstlmregio_2022/swisstlmregio_2022_2056.gdb.zip .

echo "Donwloading latest version of Veloland dataset..."
wget https://data.geo.admin.ch/ch.astra.veloland/veloland/veloland_2056.gdb.zip .