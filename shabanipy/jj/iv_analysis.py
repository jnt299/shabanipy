# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright 2020 by ShabaniPy Authors, see AUTHORS for more details.
#
# Distributed under the terms of the MIT license.
#
# The full license is in the file LICENCE, distributed with this software.
# -----------------------------------------------------------------------------
"""Utility functions to analyse V-I characteristic.

"""
from typing import Tuple

import numpy as np
import matplotlib.pyplot as plt
from lmfit.models import LinearModel

from .utils import correct_voltage_offset


def analyse_vi_curve(
    current_bias: np.ndarray,
    measured_voltage: np.ndarray,
    ic_voltage_threshold: float,
    high_bias_threshold: float,
    debug: bool = False,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Extract the critical and excess current along with the normal resistance.

    All values are extracted for cold and hot electrons. The cold side is the
    one on which the bias is ramped from 0 to large value, the hot one the one
    on which bias is ramped towards 0.

    Parameters
    ----------
    current_bias : np.ndarray
        N+1D array of the current bias applied on the junction in A.
    measured_voltage : np.ndarray
        N+1D array of the voltage accross the junction in V.
    ic_voltage_threshold : float
        Voltage threshold in V above which the junction is not considered to carry a
        supercurrent anymore. Used in the determination of the critical current.
    high_bias_threshold : float
        Positive bias value above which the data can be used to extract the
        normal resistance.
    debug : bool, optional
        Generate summary plots of the fitting.

    Returns
    -------
    voltage_offset_correction : np.ndarray
        Offset used to correct the measured voltage. ND array
    rn_c : np.ndarray
        Normal resistance evaluated on the cold electron side. ND array
    rn_h : np.ndarray
        Normal resistance evaluated on the hot electron side. ND array
    ic_c : np.ndarray
        Critical current evaluated on the cold electron side. ND array
    ic_h : np.ndarray
        Critical current evaluated on the hot electron side. ND array
    iexe_c : np.ndarray
        Excess current evaluated on the cold electron side. ND array
    iexe_h : np.ndarray
        Excess current evaluated on the hot electron side. ND array

    """
    ic_c = np.empty(current_bias.shape[:-1])
    ic_h = np.empty(current_bias.shape[:-1])
    rn_c = np.empty(current_bias.shape[:-1])
    rn_h = np.empty(current_bias.shape[:-1])
    ie_c = np.empty(current_bias.shape[:-1])
    ie_h = np.empty(current_bias.shape[:-1])

    # Iterate on additional dimensions
    it = np.nditer(current_bias[..., 0], ["multi_index"])

    for b in it:
        m_index = it.multi_index

        # Extract the relevant sweeps.
        cb = current_bias[m_index]
        mv = measured_voltage[m_index]

        # Determine the hot and cold electron side
        if cb[0] < 0.0:
            cold_value = lambda p, n: abs(p)
            hot_value = lambda p, n: abs(n)
        else:
            cold_value = lambda p, n: abs(n)
            hot_value = lambda p, n: abs(p)

        # Sort the data so that the bias always go from negative to positive
        sorting_index = np.argsort(cb)
        cb = cb[sorting_index]
        mv = mv[sorting_index]

        # Index at which the bias current is zero
        index = np.argmin(np.abs(cb))

        # Extract the critical current on the positive and negative branch
        ic_n = cb[np.max(np.where(np.less(mv[:index], -ic_voltage_threshold))[0])]
        ic_p = cb[
            np.min(np.where(np.greater(mv[index:], ic_voltage_threshold))[0]) + index
        ]

        # Fit the high positive/negative bias to extract the normal resistance
        # excess current and their product
        index_pos = np.argmin(np.abs(cb - high_bias_threshold))
        index_neg = np.argmin(np.abs(cb + high_bias_threshold))

        model = LinearModel()
        pars = model.guess(mv[index_pos:], x=cb[index_pos:])
        pos_results = model.fit(mv[index_pos:], pars, x=cb[index_pos:])

        pars = model.guess(mv[index_neg:], x=cb[index_neg:])
        neg_results = model.fit(mv[:index_neg], pars, x=cb[:index_neg])

        rn_p = pos_results.best_values["slope"]
        # Iexe p
        iexe_p = -pos_results.best_values["intercept"] / rn_p

        rn_n = neg_results.best_values["slope"]
        # Iexe n
        iexe_n = neg_results.best_values["intercept"] / rn_n

        if debug:
            # Prepare a summary plot: full scale
            fig = plt.figure(constrained_layout=True)
            ax = fig.gca()
            ax.plot(cb * 1e6, mv * 1e3)
            ax.plot(
                cb[index:] * 1e6,
                model.eval(pos_results.params, x=cb[index:]) * 1e3,
                "--k",
            )
            ax.plot(
                cb[: index + 1] * 1e6,
                model.eval(neg_results.params, x=cb[: index + 1]) * 1e3,
                "--k",
            )
            ax.set_xlabel("Bias current (µA)")
            ax.set_ylabel("Voltage drop (mV)")

            # Prepare a summary plot: zoomed in
            mask = np.logical_and(np.greater(cb, -3 * ic_p), np.less(cb, 3 * ic_p))
            if np.any(mask):
                fig = plt.figure(constrained_layout=True)
                ax = fig.gca()
                ax.plot(cb * 1e6, mv * 1e3)
                aux = model.eval(pos_results.params, x=cb[index:]) * 1e3
                ax.plot(
                    cb[index:] * 1e6,
                    model.eval(pos_results.params, x=cb[index:]) * 1e3,
                    "--",
                )
                ax.plot(
                    cb[: index + 1] * 1e6,
                    model.eval(neg_results.params, x=cb[: index + 1]) * 1e3,
                    "--",
                )
                ax.set_xlim(
                    (
                        -3 * cold_value(ic_p, ic_n) * 1e6,
                        3 * cold_value(ic_p, ic_n) * 1e6,
                    )
                )
                aux = mv[mask]
                ax.set_ylim((np.min(mv[mask]) * 1e3, np.max(mv[mask]) * 1e3,))
                ax.set_xlabel("Bias current (µA)")
                ax.set_ylabel("Voltage drop (mV)")

            plt.show()

        rn_c[m_index] = cold_value(rn_p, rn_n)
        rn_h[m_index] = hot_value(rn_p, rn_n)
        ic_c[m_index] = cold_value(ic_p, ic_n)
        ic_h[m_index] = hot_value(ic_p, ic_n)
        ie_c[m_index] = cold_value(iexe_p, iexe_n)
        ie_h[m_index] = hot_value(iexe_p, iexe_n)

    return (rn_c, rn_h, ic_c, ic_h, ie_c, ie_h)
