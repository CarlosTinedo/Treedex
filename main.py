import pandas as pd
import argparse
import sys
from pathlib import Path
from ete4 import PhyloTree
from .app import create_app

# Aqui tenim una funció per parsejar arguments de línia de comandes
def parse_args():
    parser = argparse.ArgumentParser(
        description="Treedex dashboard"
    )
    parser.add_argument(
        "-d", "--data",
        required=True,
        help="Path to species information CSV file"
    )
    parser.add_argument(
        "-t", "--tree",
        required=False,
        help="Path to Newick tree file"
    )
    return parser.parse_args()


def main():

    # Reading the data
    args = parse_args()
    data_path = Path(args.data)
    tree_path = args.tree

    if not data_path.exists():
        print(f"ERROR: File not found: {data_path}")
        sys.exit(1)

    # Reading input
    df_table = pd.read_csv(data_path)
    t = PhyloTree(tree_path)

    # Initialize Dash app
    app = create_app(df_table, t)

    # Run server
    app.run(debug=True)

if __name__ == '__main__':
    main()
