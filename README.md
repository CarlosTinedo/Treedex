# Treedex

Treedex is an interactive Dash application for exploring phylogenetic trees
together with tables and other data visualizations. Tree rendering is provided
by the Dashview backend from the ETE fork maintained for Treedex.

## Requirements

- Git
- Python 3.12 or newer
- Conda or another Python virtual-environment tool
- A modern web browser such as Firefox, Chrome, or Safari

## Installation with Conda

Clone Treedex and enter the repository:

```bash
git clone https://github.com/maxtico/Treedex.git
cd Treedex
```

Create and activate an isolated environment:

```bash
conda create --name treedex python=3.12
conda activate treedex
```

Install the `ete4` branch of the ETE fork used by Treedex:

```bash
python -m pip install "ete4 @ git+https://github.com/maxtico/ete.git@ete4"
```

Install Treedex and its remaining dependencies in editable mode:

```bash
python -m pip install -e .
```

Editable mode means changes made under `src/treedex` are used the next time
the application starts, without reinstalling Treedex.

## Run the included example

The repository includes both example inputs:

- `mammal_tree.nw`: phylogenetic tree in Newick format
- `species_information.csv`: metadata used by the table and plots

From the root of the Treedex repository, run:

```bash
treedex \
  --tree mammal_tree.nw \
  --data species_information.csv
```

Dash will print the local address in the terminal. It is normally:

```text
http://127.0.0.1:8050
```

Open that address in a browser. Move the pointer over the **Controls** handle
at the top of the page to open the control panel. The **Rectangular** and
**Circular** options change the tree shape using ETE's Dashview renderer.

Stop the application with `Ctrl+C` in the terminal.

## Part-of-Whole plots

In **Controls → Plots → Plot type → Part-of-Whole**, choose **Pie**, **Sunburst**,
**Treemap**, or **Icicle**. Pie keeps its existing slice and donut controls.

For the other three charts, select **Hierarchy levels** from root to leaves,
such as `Order`, `Family`, then `Species`. The selection order defines the
hierarchy; remove and reselect a level to change its position. A single
`Species` level also works with the included example table. Choose a numeric
**Sector values** column to size sectors by a measure, or leave it empty to
count rows. **Root label** adds an optional common root. These charts use
the uploaded table's metadata columns as levels.

For a table that already describes nodes, choose **Node and parent rows** as
the hierarchy source, then select node names, optional unique node IDs, and
the parent column. Parent references must match IDs (or names when IDs are
omitted); empty parents identify roots. **Total** parent values include their
children, while **Additional to children** values are added to child values.

The numbered option pages provide colors, hover fields, titles, visible depth,
and sizing. Settings and page positions are saved separately for each chart.
Click **Build plot** to apply edits. Clicking a sector selects all species in
that branch in the table and tree; tree and table selections highlight the
corresponding sectors using the last built settings.

## Verify the installation

These commands confirm that ETE, Treedex, and the command-line entry point are
available in the active environment:

```bash
python -c "import ete4, treedex; print('ETE and Treedex are available')"
treedex --help
```

## Editable development of both ETE and Treedex

Use this setup when changing the ETE Dashview code and testing those changes
immediately in Treedex. Clone both repositories into the same parent directory:

```bash
mkdir treedex-development
cd treedex-development

git clone --branch ete4 https://github.com/maxtico/ete.git ete4
git clone https://github.com/maxtico/Treedex.git

conda create --name treedex python=3.12
conda activate treedex

python -m pip install -e ./ete4
python -m pip install -e ./Treedex
```

Then start the example from the Treedex directory:

```bash
cd Treedex
treedex --tree mammal_tree.nw --data species_information.csv
```

With both packages installed in editable mode, source changes in either
repository are picked up after restarting the application.

## Alternative virtual environment

If Conda is unavailable, create a standard Python environment instead:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install "ete4 @ git+https://github.com/maxtico/ete.git@ete4"
python -m pip install -e .
```

On Windows, activate it with:

```powershell
.venv\Scripts\Activate.ps1
```

Then use the same `treedex --tree ... --data ...` command shown above.
