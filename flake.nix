{
  description = "lora-experiments";

  inputs = {
    nixpkgs.url = "nixpkgs/nixpkgs-unstable";
    flake-utils.url = "github:numtide/flake-utils";
    sillyORM = {
      url = "github:theverygaming/sillyORM/dev";
      inputs.nixpkgs.follows = "nixpkgs";
    };
  };

  outputs =
    {
      self,
      nixpkgs,
      flake-utils,
      sillyORM,
    }:
    { }
    // flake-utils.lib.eachDefaultSystem (
      system:
      let
        pkgs = import nixpkgs {
          inherit system;
        };
      in
      rec {
        devShells.default = pkgs.stdenv.mkDerivation {
          name = "lora-experiments";
          buildInputs =
            with pkgs;
            [
              python313

              # mesh-python
              python313Packages.meshtastic
              python313Packages.cryptography

              # lora_modem
              platformio
              # because platformio is broken idk
              python313Packages.packaging

              # rustymesh
              cargo
              rustc
              maturin

              # sdr-lora
              (gnuradio.override {
                extraPackages = [
                  gnuradioPackages.lora_sdr
                  gnuradioPackages.osmosdr
                ];
              })
              (gnuradio.override {
                extraPackages = [
                  gnuradioPackages.lora_sdr
                  gnuradioPackages.osmosdr
                ];
              }).pythonEnv
            ];
        };
      }
    );
}
