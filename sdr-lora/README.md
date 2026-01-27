nix:
gui env:
`nix-shell -p '(gnuradio.override { extraPackages = [ gnuradioPackages.lora_sdr gnuradioPackages.osmosdr ]; })'`
python env:
`nix-shell -p '(gnuradio.override { extraPackages = [ gnuradioPackages.lora_sdr gnuradioPackages.osmosdr ]; }).pythonEnv'`
