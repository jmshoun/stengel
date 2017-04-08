# Stengel
## Granular Baseball Analysis and Simulation

Stengel is an ongoing attempt to build a stochastic Major League Baseball simulation from the ground up, using the most granular publicly available data. The ultimate goal is to build a pitch-by-pitch simulation that includes player fatigue, injuries, and other second-order player effects.

### Installation

Auto-installation of depedencies is on the project roadmap, but unfortunately, installation is manual for the time being. Stengel requires the following third-party Python modules:

- NumPy
- scikit-learn
- matplotlib
- Tensorflow
- progressbar2
- PyMongo

Stengel also requires access to the following non-Python dependencies:

- mongodb


### Potential Use Cases

- *Prediction*: Given a pair of opposing teams, a park, and a pair of starting lineups, Stengel will be able to produce very accurate simulaitons of the game outcome -- not just who won, but also predicted distributions of arbitrary metrics.
- *Inference*: It will be possible to use Stengel to evaluate counterfactuals. What if a pitcher's fastball were one mph faster? What if a batter had slightly more plate discipline?
- *Strategy*: It will be possible to use Stengel to find optimal managerial strategies: bullpen management, when to call for bunts and steals, what pitches to call when, and so forth.

