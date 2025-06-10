{
  description = "Projeto Final de Laboratório de Base de Dados";

  inputs = {
    flake-utils.url = "github:numtide/flake-utils";

    nixpkgs.url = "github:nixos/nixpkgs/nixos-24.11";
  };

  outputs = {
    self,
    nixpkgs,
    flake-utils,
    ...
  } @ inputs:
    flake-utils.lib.eachDefaultSystem (system: let
      pkgs = inputs.nixpkgs.legacyPackages.${system};
    in {
      devShells.default = pkgs.mkShell {
        packages = with pkgs; [
          (pkgs.python311.withPackages (python-pkgs: [
            python-pkgs.psycopg2
            python-pkgs.psycopg2-binary

            python-pkgs.seaborn
            python-pkgs.numpy
            python-pkgs.matplotlib
            python-pkgs.pandas
            python-pkgs.transformers
            python-pkgs.datasets
            python-pkgs.seqeval
            python-pkgs.torch
            python-pkgs.wandb
            python-pkgs.wordcloud
            python-pkgs.accelerate
            python-pkgs.nltk
            python-pkgs.pyzipper
            python-pkgs.glob2
          ]))
        ];
      };
    });
}
