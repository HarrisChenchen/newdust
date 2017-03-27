import numpy as np
from ... import constants as c

__all__ = ['Mie']

def _lam_cm(lam, unit='kev'):
    assert unit in ALLOWED_UNITS
    if unit == 'kev':
        result  = c.hc / lam  # kev cm / kev
    if unit == 'angs':
        result  = c.angs2cm * lam  # cm/angs * angs
    return result  # cm

# Major update: March 27, 2016
# This code is slow, so to avoid running getQs over and over again, create
# "calculate" function that runs getQs and stores it, then returns the appropriate values later??  Not sure ...

# Copied from ~/code/mie/bhmie_mod.pro
# ''Subroutine BHMIE is the Bohren-Huffman Mie scattering subroutine
#    to calculate scattering and absorption by a homogenous isotropic
#    sphere.''
#
class Mie(object):
    """
    | Mie scattering algorithms of Bohren & Hoffman
    | See their book: *Absorption and Scattering of Light by Small Particles*
    |
    | **ATTRIBUTES**
    | stype : string : 'Mie'
    |
    | **FUNCTIONS**
    | getQs( a=1.0 [um], E=1.0 [keV], cm=cmi.CmDrude(), getQ='sca' ['ext','back','gsca','diff'], theta=None [arcsec] )
    |     *returns* Efficiency factors depending on getQ [unitless or ster^-1]
    | Qsca( E [keV], a=1.0 [um], cm=cmi.CmDrude() )
    |     *returns* Scattering efficiency [unitless]
    | Qext( E [keV], a=1.0 [um], cm=cmi.CmDrude() )
    |     *returns* Extinction efficiency [unitless]
    | Diff( theta [arcsec], E=1.0 [keV], a=1.0 [um], cm=cmi.CmDrude() )
    |     *returns* Differential cross-section [cm^2 ster^-1]
    """

    def __init__(self):
        self.stype = 'Mie'
        self.cite  = 'Mie scattering solution'
        self.qsca  = None
        self.qext  = None
        self.qback = None
        self.gsca  = None
        self.diff  = None

    def calculate(self, lam, a, cm, unit='kev', theta=None):  # Takes single a and E argument

        if np.size(a) > 1:
            print('Error: Can only specify one value for a')
            return

        indl90 = np.array([])  # Empty arrays indicate that there are no theta values set
        indg90 = np.array([])  # Do not have to check if theta != None throughout calculation
        s1     = np.array([])
        s2     = np.array([])
        pi     = np.array([])
        pi0    = np.array([])
        pi1    = np.array([])
        tau    = np.array([])
        amu    = np.array([])

        if theta is not None:
            if np.size(lam) > 1 and np.size(lam) != np.size(theta):
                print('Error: If more than one lam value specified, theta must have same size as E')
                return

            if np.size(theta) == 1:
                theta = np.array([theta])

            theta_rad = theta * c.arcs2rad
            amu       = np.abs(np.cos(theta_rad))

            indl90    = np.where(theta_rad < np.pi/2.0)
            indg90    = np.where(theta_rad >= np.pi/2.0)

            nang  = np.size(theta)
            s1    = np.zeros(nang, dtype='complex')
            s2    = np.zeros(nang, dtype='complex')
            pi    = np.zeros(nang, dtype='complex')
            pi0   = np.zeros(nang, dtype='complex')
            pi1   = np.zeros(nang, dtype='complex') + 1.0
            tau   = np.zeros(nang, dtype='complex')

        refrel = cm.rp(lam, unit) + 1j * cm.ip(lam, unit)
        lam_cm = _lam_cm(lam, unit)

        x      = (2.0 * np.pi * a*c.micron2cm) / lam_cm
        y      = x * refrel
        ymod   = np.abs(y)
        nx     = np.size(x)

        # *** Series expansion terminated after NSTOP terms
        # Logarithmic derivatives calculated from NMX on down

        xstop  = x + 4.0 * np.power(x, 0.3333) + 2.0
        test   = np.append(xstop, ymod)
        nmx    = np.max(test) + 15
        nmx    = np.int32(nmx)

        nstop  = xstop
#        nmxx   = 150000

#        if (nmx > nmxx):
#            print('error: nmx > nmxx=', nmxx, ' for |m|x=', ymod)
        # *** Logarithmic derivative D(J) calculated by downward recurrence
        # beginning with initial value (0.,0.) at J=NMX

        d = np.zeros(shape=(nx,nmx+1), dtype='complex')
        dold = np.zeros(nmx+1, dtype='complex')
        # Original code set size to nmxx.
        # I see that the array only needs to be slightly larger than nmx

        for n in np.arange(nmx-1)+1:  # for n=1, nmx-1 do begin
            en = nmx - n + 1
            d[:,nmx-n]  = (en/y) - (1.0 / (d[:,nmx-n+1]+en/y))

        # *** Riccati-Bessel functions with real argument X
        # calculated by upward recurrence

        psi0 = np.cos(x)
        psi1 = np.sin(x)
        chi0 = -np.sin(x)
        chi1 = np.cos(x)
        xi1  = psi1 - 1j * chi1

        qsca = 0.0    # scattering efficiency
        gsca = 0.0    # <cos(theta)>

        s1_ext = 0
        s2_ext = 0
        s1_back = 0
        s2_back = 0

        pi_ext  = 0
        pi0_ext = 0
        pi1_ext = 1
        tau_ext = 0

        p    = -1.0

        for n in np.arange(np.max(nstop))+1:  # for n=1, nstop do begin
            en = n
            fn = (2.0*en+1.0) / (en * (en+1.0))

            # for given N, PSI  = psi_n        CHI  = chi_n
            #              PSI1 = psi_{n-1}    CHI1 = chi_{n-1}
            #              PSI0 = psi_{n-2}    CHI0 = chi_{n-2}
            # Calculate psi_n and chi_n
            # *** Compute AN and BN:

            #*** Store previous values of AN and BN for use
            #    in computation of g=<cos(theta)>
            if n > 1:
                an1 = an
                bn1 = bn

            if nx > 1:
                ig  = np.where(nstop >= n)

                psi    = np.zeros(nx)
                chi    = np.zeros(nx)

                psi[ig] = (2.0*en-1.0) * psi1[ig]/x[ig] - psi0[ig]
                chi[ig] = (2.0*en-1.0) * chi1[ig]/x[ig] - chi0[ig]
                xi      = psi - 1j * chi

                an = np.zeros(nx, dtype='complex')
                bn = np.zeros(nx, dtype='complex')

                an[ig] = (d[ig,n]/refrel[ig] + en/x[ig]) * psi[ig] - psi1[ig]
                an[ig] = an[ig] / ((d[ig,n]/refrel[ig] + en/x[ig]) * xi[ig] - xi1[ig])
                bn[ig] = (refrel[ig]*d[ig,n] + en / x[ig]) * psi[ig] - psi1[ig]
                bn[ig] = bn[ig] / ((refrel[ig]*d[ig,n] + en/x[ig]) * xi[ig] - xi1[ig])
            else:
                psi = (2.0*en-1.0) * psi1/x - psi0
                chi = (2.0*en-1.0) * chi1/x - chi0
                xi  = psi - 1j * chi

                an = (d[0,n]/refrel + en/x) * psi - psi1
                an = an / ((d[0,n]/refrel + en/x) * xi - xi1)
                bn = (refrel*d[0,n] + en / x) * psi - psi1
                bn = bn / ((refrel*d[0,n] + en/x) * xi - xi1)

            # *** Augment sums for Qsca and g=<cos(theta)>

            # NOTE from LIA: In IDL version, bhmie casts double(an)
            # and double(bn).  This disgards the imaginary part.  To
            # avoid type casting errors, I use an.real and bn.real

            # Because animag and bnimag were intended to isolate the
            # real from imaginary parts, I replaced all instances of
            # double( foo * complex(0.d0,-1.d0) ) with foo.imag

            qsca   = qsca + (2.0 * en + 1.0) * (np.power(np.abs(an),2) + np.power(np.abs(bn),2))
            gsca   = gsca + ((2.0 * en + 1.0) / (en * (en + 1.0))) * (an.real * bn.real + an.imag * bn.imag)

            if n > 1:
                gsca    = gsca + ((en-1.0) * (en+1.0)/en) * \
                    (an1.real*an.real + an1.imag*an.imag + bn1.real*bn.real + bn1.imag*bn.imag)

            # *** Now calculate scattering intensity pattern
            #     First do angles from 0 to 90

            # LIA : Altered the two loops below so that only the indices where ang
            # < 90 are used.  Replaced (j) with [indl90]

            # Note also: If theta is specified, and np.size(E) > 1,
            # the number of E values must match the number of theta
            # values.  Cosmological halo functions will utilize this
            # Diff this way.

            pi  = pi1
            tau = en * amu * pi - (en + 1.0) * pi0

            if np.size(indl90) != 0:
                antmp = an
                bntmp = bn
                if nx > 1:
                    antmp = an[indl90]
                    bntmp = bn[indl90]  # For case where multiple E and theta are specified

                s1[indl90]  = s1[indl90] + fn * (antmp * pi[indl90] + bntmp*tau[indl90])
                s2[indl90]  = s2[indl90] + fn * (antmp * tau[indl90] + bntmp*pi[indl90])
            #ENDIF

            pi_ext = pi1_ext
            tau_ext = en * 1.0 * pi_ext - (en + 1.0) * pi0_ext

            s1_ext = s1_ext + fn * (an*pi_ext+bn*tau_ext)
            s2_ext = s2_ext + fn * (bn*pi_ext+an*tau_ext)

            # *** Now do angles greater than 90 using PI and TAU from
            #     angles less than 90.
            #     P=1 for N=1,3,...; P=-1 for N=2,4,...

            p = -p

            # LIA : Previous code used tau(j) from the previous loop.  How do I
            # get around this?

            if np.size(indg90) != 0:
                antmp = an
                bntmp = bn
                if nx > 1:
                    antmp = an[indg90]
                    bntmp = bn[indg90]  # For case where multiple E and theta are specified

                s1[indg90]  = s1[indg90] + fn * p * (antmp * pi[indg90] - bntmp*tau[indg90])
                s2[indg90]  = s2[indg90] + fn * p * (bntmp * pi[indg90] - antmp*tau[indg90])
            #ENDIF

            s1_back = s1_back + fn * p * (an * pi_ext - bn * tau_ext)
            s2_back = s2_back + fn * p * (bn * pi_ext - an * tau_ext)

            psi0 = psi1
            psi1 = psi
            chi0 = chi1
            chi1 = chi
            xi1  = psi1 - 1j * chi1

            # *** Compute pi_n for next value of n
            #     For each angle J, compute pi_n+1
            #     from PI = pi_n , PI0 = pi_n-1

            pi1  = ((2.0 * en + 1.0) * amu * pi - (en + 1.0) * pi0) / en
            pi0  = pi

            pi1_ext = ((2.0 * en + 1.0) * 1.0 * pi_ext - (en + 1.0) * pi0_ext) / en
            pi0_ext = pi_ext

            # ENDFOR

        # *** Have summed sufficient terms.
        #     Now compute QSCA,QEXT,QBACK,and GSCA
        gsca = 2.0 * gsca / qsca
        qsca = (2.0 / np.power(x,2)) * qsca

        # LIA : Changed qext to use s1(theta=0) instead of s1(1).  Why did the
        # original code use s1(1)?

        qext = (4.0 / np.power(x,2)) * s1_ext.real
        qback = np.power(np.abs(s1_back)/x, 2) / np.pi

        self.qsca = qsca
        self.qext = qext
        self.qback = qback
        self.gsca = gsca

        if theta is not None:
            bad_theta = np.where(theta_rad > np.pi)  # Set to 0 values where theta > !pi
            s1[bad_theta] = 0
            s2[bad_theta] = 0
            self.diff = 0.5 * (np.power(np.abs(s1), 2) + np.power(np.abs(s2), 2)) / (np.pi * x*x)

    def Qsca(self, *args, **kwargs):
        if self.qsca is None:
            self.calculate(*args, **kwargs)
        return self.qsca

    def Qext(self, *args, **kwargs):
        if self.qext is None:
            self.calculate(*args, **kwargs)
        return self.qsca

    def Qabs(self, *args, **kwargs):
        if self.qsca is None:
            self.calculate(*args, **kwargs)
        return self.qext - self.qsca

    def Diff(self, *args, **kwargs):
        if self.qsca is None:
            self.calculate(*args, **kwargs)
