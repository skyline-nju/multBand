""" Read data from .npz file and yield generators. """

import os
import sys
import numpy as np
import glob
from collections import defaultdict
from fractions import Fraction
sys.path.append("../")

try:
    import common
    from handle import plot_serials
except ImportError:
    raise


def time_average(file, rate_min=0.3):
    """ Get time-averaged variables from a given sample.

        parameters:
        --------
        file: str
            Input file.
        rate_min: float, optional
            Minimum rate to accept a state of nb at given Lx.

        Returns:
        --------
        res: dict
            Key: nb, subkeys: "mean_phi", "rate", "ave_peak", "std_gap",
            "mean_v".
    """
    buff = np.load(file)
    print(file)
    # for key in buff.keys():
    #     print(key)
    sum_phi = defaultdict(float)
    count = defaultdict(int)
    for i, nb in enumerate(buff["seg_num"]):
        if nb > 0:
            dt = buff["seg_idx1"][i] - buff["seg_idx0"][i]
            sum_phi[nb] += buff["seg_phi"][i] * dt
            count[nb] += dt

    res = defaultdict(dict)
    tot = buff["seg_idx1"][-1] - buff["seg_idx0"][0]
    for i, nb in enumerate(buff["nb_set"]):
        if nb > 0:
            rate = count[nb] / tot
            if rate >= rate_min:

                res[nb] = {
                    "mean_phi": sum_phi[nb] / count[nb],
                    "rate": rate,
                    "ave_peak": buff["mean_rhox"][i],
                    "std_gap": buff["std_gap"][i],
                    "mean_v": buff["mean_v"][i],
                }
    return res


def sample_average(Lx, eps, eta=350, Ly=200, rate_min=0.3):
    """ Get sample-averaged variables for give parameters.

        Parameters:
        --------
        Lx, eps, eta, Ly: int
            Parameters.
        rate_min: float
            Minimum rate to accept a nb at given Lx

        Returns:
        --------
        phi: dict
            Sample-averaged order parameters for Lx, nb
        rate: dict
            Rate of nb at given Lx
    """
    files = glob.glob("mb_%d.%d.%d.%d.*.npz" % (eta, eps, Lx, Ly))
    sum_phi = defaultdict(float)
    weight = defaultdict(float)
    tot = 0

    for file in files:
        dict0 = time_average(file, rate_min)
        for nb in dict0:
            sum_phi[nb] += dict0[nb]["mean_phi"] * dict0[nb]["rate"]
            weight[nb] += dict0[nb]["rate"]
        tot += 1
    phi = {nb: sum_phi[nb] / weight[nb] for nb in sum_phi}
    rate = {nb: weight[nb] / tot for nb in weight}
    return phi, rate


def read_matched_file(para: dict = {}, path=None, rate_min=0.3) -> dict:
    pat = "mb_%s.npz" % (common.dict2str(para, "eta", "eps", "Lx", "Ly",
                                         "seed"))
    if path is None:
        files = glob.glob(pat)
    elif isinstance(path, str):
        files = glob.glob(path + pat)
    elif isinstance(path, list):
        files = []
        for my_path in path:
            files += glob.glob(my_path + pat)
    res = defaultdict(dict)
    for file in files:
        para = common.get_para(file)
        Lx = para[2]
        seed = para[4]
        res[Lx].update({seed: time_average(file, rate_min)})
    return res


def fixed_para(*args, **kwargs):
    """ Generator of *args with given fixed parameter.

        *arg: The values need to yield.
        **kwargs: parameters that keep constant.

        Parameters:
        --------
            *"mean_phi": str
                Yield mean of phi
            *"rate": str
                Yield  rate
            *"ave_peak": str
                Yield time-averaged peak
            *"std_gap": str
                Yield standard deviation of gaps between two nearest peak.
            **Lx: int
                System size along x direction
            **nb: int
                Number of bands
            **seed: int
                Random seed
            **Lr_over_nb_lambda: Fraction
                Ratio of Lr to nb*lambda
            **lamb: int
                Wave length of bands
            **dictLSN: int
                Dict of data

        Yields:
        --------
            res: float or int or list
                if len(args) == 1, yield a value, elsewise yield a list
    """
    if "Lx" in kwargs:
        flag_Lx = True
        Lx0 = kwargs["Lx"]
    else:
        flag_Lx = False
    if "seed" in kwargs:
        flag_seed = True
        seed0 = kwargs["seed"]
    else:
        flag_seed = False
    if "nb" in kwargs:
        flag_nb = True
        nb0 = kwargs["nb"]
    else:
        flag_nb = False
    if "Lr_over_nb_lambda" in kwargs:
        if "lamb" not in kwargs:
            print("Error, need input lambda")
            sys.exit()
        else:
            flag_ratio = True
            ratio0 = kwargs["Lr_over_nb_lambda"]
            lambda0 = kwargs["lamb"]
    else:
        flag_ratio = False

    if "dictLSN" in kwargs:
        dictLSN = kwargs["dictLSN"]
    else:
        para = {}
        if flag_Lx:
            para["Lx"] = Lx0
        if flag_seed:
            para["seed"] = seed0
        dictLSN = read_matched_file(para)

    if flag_Lx:
        if Lx0 in dictLSN:
            Lxs = [Lx0]
        else:
            print("Wrong Lx")
            sys.exit()
    else:
        Lxs = sorted(dictLSN.keys())
    for Lx in Lxs:
        dictSN = dictLSN[Lx]
        if flag_seed:
            if seed0 in dictSN:
                seeds = [seed0]
            else:
                continue
        else:
            seeds = sorted(dictSN.keys())
        for seed in seeds:
            dictN = dictSN[seed]
            if flag_nb:
                if nb0 in dictN:
                    res = [dictN[nb0][arg] for arg in args]
                    if not flag_Lx:
                        res.append(Lx)
                    yield res
                else:
                    continue
            elif flag_ratio:
                for nb in sorted(dictN.keys()):
                    Lr = Lx - nb * lambda0
                    if Lr == ratio0 * nb * lambda0:
                        res = [dictN[nb][arg] for arg in args]
                        res.append(Lx)
                        res.append(nb)
                        yield res


def eq_Lx_and_nb(Lx, nb, *args, dictLSN: dict = None):
    if dictLSN is None:
        dictLSN = read_matched_file({"Lx": Lx})
    dictSN = dictLSN[Lx]
    seed_sorted = sorted(dictSN.keys())
    if len(args) == 1:
        for seed in seed_sorted:
            if nb in dictSN[seed]:
                res = dictSN[seed][nb][args[0]]
                yield res
    else:
        for seed in seed_sorted:
            if nb in dictSN[seed]:
                res = [dictSN[seed][nb][arg] for arg in args]
                yield res


def eq_Lr_over_nb_lambda(Lr_over_nb_lambda: Fraction, lamb: int,
                         dictLSN: dict):
    """ Generator for Lx, nb, peak, phi with equal Lr/(nb*lambda)

        Parameters:
        --------
            Lr_over_nb_lambda: Fraction
                Ratio between Lr and nb * lambda
            lamb: int
                Wave length
            dictLSN: dict
                Dict of data with key Lx->seed->nb.

        Yields:
        --------
            Lx: int
                System size in x direction
            nb: int
                Number of bands
            peak: np.ndarray
                Time-averaged density profile
            phi: float
                Time-averaged order parameter
    """
    for Lx in dictLSN:
        for seed in dictLSN[Lx]:
            for nb in dictLSN[Lx][seed]:
                Lr = Lx - nb * lamb
                if Lr_over_nb_lambda * nb * lamb == Lr:
                    peak = dictLSN[Lx][seed][nb]["ave_peak"]
                    phi = dictLSN[Lx][seed][nb]["mean_phi"]
                    yield Lx, nb, peak, phi


def get_dict_NLS(para={}, dictLSN=None) -> dict:
    """ Get dict with key: nb->Lx->seed.

        Parameters:
        --------
            para: list
                List of parameters: eta, $eta, eps, $eps...
            dict_LSN: dict
                 A dict with keys: Lx->seed->nb

        Returns:
        --------
            dict_NLS: dict
                A dict with keys: nb->Lx->seed
    """
    if dictLSN is None:
        dict_LSN = read_matched_file(para)
    dict_NLS = {Lx: {} for Lx in dict_LSN}
    for Lx in dict_LSN:
        dict_NLS[Lx] = common.swap_key(dict_LSN[Lx])
    dict_NLS = common.swap_key(dict_NLS)
    return dict_NLS


def plot_time_serials(file):
    buff = np.load(file)
    para = common.get_para(file)
    plot_serials(
        para,
        buff["t_beg_end"][0],
        buff["t_beg_end"][1],
        buff["num_raw"],
        buff["num_smoothed"],
        buff["seg_num"],
        buff["seg_idx0"],
        buff["seg_idx1"],
        buff["seg_phi"],
        buff["beg_movAve"],
        buff["end_movAve"],
        buff["phi_movAve"],
        show=True)


if __name__ == "__main__":
    os.chdir("E:\\data\\random_torque\\bands\\Lx\\snapshot\\eps20")
    file = "mb_350.20.1000.200.2151000.npz"
    plot_time_serials(file)
