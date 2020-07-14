import sys

from matplotlib import pyplot as plt
import numpy as np
from numpy.fft import fft
from scipy import constants as c

from shabanipy.jj.fraunhofer.generate_pattern import produce_fraunhofer_fast
from shabanipy.jj.fraunhofer.deterministic_reconstruction \
        import extract_theta, extract_current_distribution

# constants and junction dimensions
PHI0 = c.physical_constants['mag. flux quantum'][0]
a = 1e-6    # junction width
d = 100e-9  # junction length (really d + 2λ)

# tophat current distribution
x = np.linspace(-2e-6, 2e-6, 129)
jx = np.zeros_like(x)
jx[np.where(np.abs(x) < a/2)] = 1

# generate fraunhofer
b = np.linspace(-.05, .05, 129)
ic = produce_fraunhofer_fast(b, 2*np.pi*d/PHI0, jx, x)
sys.exit()

# reconstruct fraunhofer
theta = extract_theta(b, ic)
x2, jx2 = extract_current_distribution(b, ic, 2*np.pi*d/PHI0, a, 100)
