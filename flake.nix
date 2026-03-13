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
              python313Packages.fastapi
              fastapi-cli
              sillyORM.packages.${system}.default

              # mesh-python-frontend
              flutter

              # lora_modem
              platformio
              # because platformio is broken idk
              python313Packages.packaging
              # portduino stuff
              pkg-config
              libuv
              libgpiod
              i2c-tools
              (lgpio.overrideAttrs (final: prev: {
                src = fetchFromGitHub {
                  owner = "joan2937";
                  repo = "lg";
                  rev = "bcccd782eceedc5b278b3056ea81d5fbbb89c489";
                  hash = "sha256-v8zh2x9eU2iAzD8MXCmBWvI3vFSGds9TFzHXorFjeqk=";
                };
              }))

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
