import numpy as np
from newdust import constants as c

__all__ = ['CmDrude']

ALLOWED_UNITS = ['kev', 'angs']

class CmDrude(object):
    """
    | **ATTRIBUTES**
    | cmtype : 'Drude'
    | rho    : grain density [g cm^-3]
    | citation : A string containing citation to original work
    |
    | ** FUNCTIONS**
    | rp(E)  : real part of complex index of refraction [E in keV]
    | ip(E)  : imaginary part of complex index of refraction [always 0.0]
    """
    def __init__(self, rho=3.0):  # Returns a CM using the Drude approximation
        self.cmtype = 'Drude'
        self.rho    = rho
        self.citation = "Using the Drude approximation.\nBohren, C. F. & Huffman, D. R., 1983, Absorption and Scattering of Light by Small Particles (New York: Wiley)"

    def rp(self, lam, unit='kev'):
        assert unit in ALLOWED_UNITS
        if unit == 'angs':
            E = c.hc_angs / lam  # keV
        if unit == 'kev':
            E = lam
        mm1 = self.rho / (2.0*c.m_p) * c.r_e/(2.0*np.pi) * np.power(c.hc/E, 2)
        return mm1+1

    def ip(self, lam):
        if np.size(lam) > 1:
            return np.zeros(np.size(lam))
        else:
            return 0.0

    def plot(self, ax, lam, unit='kev', **kwargs):
        assert unit in ALLOWED_UNITS
        rp = self.rp(lam, unit=unit)
        ax.plot(lam, rp-1.0, **kwargs)
        ax.set_ylabel("m-1")
        if unit == 'kev':
            ax.set_xlabel("Energy (keV)")
        if unit == 'angs':
            ax.set_xlabel("Wavelength (Angstroms)")
