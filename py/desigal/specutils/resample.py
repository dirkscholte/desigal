""" Resample a spectrum to a new wavelength grid.
Currently supported methods are:
1. Linear interpolated resampler
2. S/N conserving resampler
3. Flux conserving resampler
4. Spectroperfection resampler

1 is fastest, 2 and 3 are relatively fast courtesy of parallelization and 4 is slow.
1,2,3 will provide correlated wavelength bins while 4 is not flux conserving.
"""
import multiprocessing
from joblib import Parallel, delayed
import numpy as np
import desispec
from desispec.quicklook.palib import resample_spec
from desispec.interpolation import resample_flux


def linear_resample(wave_new, wave, flux, ivar=None, fill_val=np.nan, n_workers=1):
    """
    Resample a spectrum to a new wavelength grid using linear interpolation.
    """

    if n_workers == 1:
        flux_new = np.array(
            [
                np.interp(wave_new, wave[i], flux[i], left=fill_val, right=fill_val)
                for i in range(len(flux))
            ]
        )
        if ivar is not None:
            ivar_new = np.array(
                [
                    np.interp(wave_new, wave[i], ivar[i], left=fill_val, right=fill_val)
                    for i in range(len(flux))
                ]
            )
            return flux_new, ivar_new
        return flux_new
    else:
        flux_new = np.array(
            Parallel(n_jobs=n_workers)(
                delayed(np.interp)(
                    wave_new, wave[i], flux[i], left=fill_val, right=fill_val
                )
                for i in range(len(flux))
            )
        )
        if ivar is not None:
            ivar_new = np.array(
                Parallel(n_jobs=n_workers)(
                    delayed(np.interp)(
                        wave_new, wave[i], ivar[i], left=fill_val, right=fill_val
                    )
                    for i in range(len(flux))
                )
            )
            return np.array(flux_new), np.array(ivar_new)
        return flux_new


def sn_conserving_resample(
    wave_new, wave, flux, ivar=None, fill_val=np.nan, verbose=False, n_workers=1
):
    """
    Resample a spectrum to a new wavelength grid using S/N conserving resampling.
    """
    if n_workers == 1:
        flux_new, ivar_new = zip(
            *[
                resample_spec(
                    wave=wave[i], flux=flux[i], outwave=wave_new, ivar=ivar[i]
                )
                for i in range(len(flux))
            ]
        )
    else:
        flux_new, ivar_new = zip(
            *Parallel(n_jobs=n_workers)(
                delayed(resample_spec)(
                    wave=wave[i], flux=flux[i], outwave=wave_new, ivar=ivar[i]
                )
                for i in range(len(flux))
            )
        )

    flux_new = np.array(flux_new)
    ivar_new = np.array(ivar_new)
    ## janky fix, find overlap and then fill
    # find overlap between new and old wavelength grid

    mask = flux_new == 0

    flux_new[mask] = fill_val
    ivar_new[mask] = fill_val
    return flux_new, ivar_new


def flux_conserving_resample(
    wave_new, wave, flux, ivar=None, fill_val=np.nan, verbose=False, n_workers=1
):
    """
    Resample a spectrum to a new wavelength grid using Flux conserving resampling.
    """
    if n_workers == 1:
        flux_new, ivar_new = zip(
            *[
                resample_flux(xout=wave_new, x=wave[i], flux=flux[i], ivar=ivar[i])
                for i in range(len(flux))
            ]
        )
    else:
        flux_new, ivar_new = zip(
            *Parallel(n_jobs=n_workers)(
                delayed(resample_flux)(
                    xout=wave_new, x=wave[i], flux=flux[i], ivar=ivar[i]
                )
                for i in range(len(flux))
            )
        )

    flux_new = np.array(flux_new)
    ivar_new = np.array(ivar_new)
    ## janky fix, find overlap and then fill
    mask = flux_new == 0

    flux_new[mask] = fill_val
    ivar_new[mask] = fill_val
    return flux_new, ivar_new


def spectroperfection_resample(
    wave_new, wave, flux, ivar=None, fill_val=np.nan, verbose=False
):
    """
    Resample a spectrum to a new wavelength grid using the spectroperf algorithm.
    """
    raise NotImplementedError("Not implemented yet")


def resample(
    wave_new,
    wave,
    flux,
    ivar=None,
    R=None,
    fill_val=np.nan,
    method="linear",
    n_workers=-1,
):
    """Resample a spectrum to a new wavelength grid.

    Parameters
    ----------
    wave_new : array-like
        New grid to resample to.
    wave :  array-like
        Original wavelength grid.
    flux :  array-like
        Original flux grid.
    ivar : array-like, optional
        Original ivar grid, by default None
    R : _type_, optional
        _description_, by default None
    fill_val : np.float, optional
        fill value for wavelength bins outside initial range, by default np.nan
    method : str, optional
        Method used to resample the spectra, choose out of
        "linear", "sn-cons", "flux-cons",  by default "linear"
    n_workers : int, optional
        Number of CPU threads to use, by default -1

    Returns
    -------
    _type_
        _description_

    Raises
    ------
    ValueError
        _description_
    """
    # set the number of parallel workers
    if n_workers <= 0:
        n_workers = multiprocessing.cpu_count()
    else:
        n_workers = min(int(n_workers), multiprocessing.cpu_count())

    if method not in ["linear", "sn-cons", "flux-cons", "spectroperfection"]:
        raise ValueError(f"Unknown resampling method: {method}")
    if method == "linear":
        return linear_resample(
            wave_new, wave, flux, ivar, fill_val=np.nan, n_workers=n_workers
        )
    elif method == "sn-cons":
        return sn_conserving_resample(
            wave_new, wave, flux, ivar, fill_val=np.nan, n_workers=n_workers
        )
    elif method == "flux-cons":
        return flux_conserving_resample(
            wave_new, wave, flux, ivar, fill_val=np.nan, n_workers=n_workers
        )
    elif method == "spectroperfection":
        return spectroperfection_resample(wave_new, wave, flux, ivar, fill_val=np.nan)
