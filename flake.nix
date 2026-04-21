{
  description = "jx — skill library and marimo notebook catalog for JUMP Cell Painting";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixpkgs-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = import nixpkgs { inherit system; };
      in
      {
        devShells.default = pkgs.mkShell {
          packages = with pkgs; [
            python312
            uv
            git
            just
            duckdb
            # System dependencies for binary wheels
            zlib
            stdenv.cc.cc.lib
          ];

          shellHook = ''
            unset PYTHONPATH
          '';

          LD_LIBRARY_PATH = "${pkgs.lib.makeLibraryPath [
            pkgs.zlib
            pkgs.stdenv.cc.cc.lib
          ]}";
        };
      });
}
