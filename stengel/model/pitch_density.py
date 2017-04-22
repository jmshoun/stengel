from __future__ import (absolute_import, division,
                        print_function, unicode_literals)

import sklearn
import numpy as np


class PitchDensityEstimator(object):
    """Create a kernel density estimate of the distribution of a few key pitch variables."""
    def __init__(self, bandwidth, scaler=None):
        """Default constructor.

        Args:
            bandwidth: Kernel bandwidth to use when fitting model.
            scaler: A sklearn StandardScaler() object for normalizing inputs.
        """
        self.kde = sklearn.neighbors.KernelDensity(bandwidth=bandwidth)
        self.scaler = scaler

    def fit(self, train):
        """Fit the KDE model to training data."""
        if self.scaler:
            train = self.scaler.transform(train)
        self.kde.fit(train)

    def score(self, test):
        """Get the mean score (log-likelihood) of the model on test data."""
        if self.scaler:
            test = self.scaler.transform(test)
        scores = self.kde.score_samples(test)
        return np.mean(scores)

    def render(self, mins, maxes, resolutions):
        """Get a three-dimensional voxel rendering of the kernel density estimate.

        Args:
            mins: List of minimum values for each axis
            maxes: List of maxmimum values for each axis
            resolutions: List of resolutions (voxels per side) for each axis.
        Returns:
            A NumPy array of shape (resolutions).
        """
        grid = self._get_rendering_grid(mins, maxes, resolutions)
        voxels = np.exp(self.kde.score_samples(grid))
        return voxels.reshape(resolutions)

    @staticmethod
    def _get_rendering_grid(mins, maxes, resolutions):
        grid_axes = [np.linspace(min_, max_, res)
                     for min_, max_, res in zip(mins, maxes, resolutions)]
        grid = np.array(np.meshgrid(*grid_axes))
        return grid.reshape(3, -1).transpose()
