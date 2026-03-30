{
  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-parts.url = "github:hercules-ci/flake-parts";
    systems.url = "github:nix-systems/default";
    treefmt-nix = {
      url = "github:numtide/treefmt-nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };
  };

  outputs =
    inputs@{
      self,
      nixpkgs,
      ...
    }:
    inputs.flake-parts.lib.mkFlake { inherit inputs; } {
      systems = import inputs.systems;
      imports = [ inputs.treefmt-nix.flakeModule ];

      perSystem =
        { pkgs, ... }:
        {
          treefmt = {
            projectRootFile = "flake.nix";
            programs = {
              nixfmt.enable = true;
              statix.enable = true;
              deadnix.enable = true;
              ruff-format.enable = true;
              ruff-check.enable = true;
            };
          };

          packages.default = pkgs.python3Packages.buildPythonApplication {
            pname = "installFonts-gen-list";
            version = "0.1.0";
            pyproject = true;
            src = ./.;

            nativeBuildInputs = with pkgs.python3Packages; [
							uv-build
              requests
            ];
          };

          devShells.default = pkgs.mkShell {
            packages = [
              (pkgs.python3.withPackages (
                ps: with ps; [
                  requests
                  pip
                ]
              ))
              pkgs.uv
            ];
          };
        };
    };
}
