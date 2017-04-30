# Stengel
## Granular Baseball Analysis and Simulation

Stengel is an ongoing attempt to build a stochastic Major League Baseball simulation from the ground up, using the most granular publicly available data. The ultimate goal is to build a pitch-by-pitch simulation that includes player fatigue, injuries, and other second-order player effects.

### Installation

If you're running Python 3.6 on Linux, installing Stengel is as easy as running `make install`. Otherwise, you'll have to manually copy the stengel/ directory to wherever you keep your local libraries.

Auto-installation of depedencies is on the project roadmap, but unfortunately, it is manual for the time being. Stengel requires the following third-party Python modules:

- NumPy
- scikit-learn
- matplotlib
- Tensorflow
- progressbar2
- PyMongo
- BeautifulSoup (bs4)
- coverage (only if you want to run make test)

Stengel also requires access to the following non-Python dependencies:

- mongodb

### Project Structure

Here's a brief overview of the project structure:
- **`stengel/`**: Python module with all of the core functionality for the project.
- **`test/`**: Unit tests for the stengel module.
- **`test_data/`**: Data used by unit tests. The actual data used by the project is in the `data/` folder, which is not kept on GitHub for obvious reasons. The scripts in this repo should make recreating the full data relatively easy.
- **`notebooks/`**: Jupyter notebooks with documentation of some of the key statistical decisions made in the project.
- **`scripts/`**: Python scripts to handle common tasks associated with managing Stengel, such as downloading and parsing data. Eventually, scripts for fitting production models will also go in this folder.

### Potential Use Cases

- *Prediction*: Given a pair of opposing teams, a park, and a pair of starting lineups, Stengel will be able to produce very accurate simulaitons of the game outcome -- not just who won, but also predicted distributions of arbitrary metrics.
- *Inference*: It will be possible to use Stengel to evaluate counterfactuals. What if a pitcher's fastball were one mph faster? What if a batter had slightly more plate discipline?
- *Strategy*: It will be possible to use Stengel to find optimal managerial strategies: bullpen management, when to call for bunts and steals, what pitches to call when, and so forth.

