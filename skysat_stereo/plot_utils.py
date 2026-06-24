#! /usr/bin/env python
"""Lightweight matplotlib plotting helpers for skysat_stereo figures.

This module provides ``iv`` / ``iv_fn`` / ``iv_ds`` image viewers that were
previously imported from David Shean's ``imview`` package
(``imview.lib.pltlib``).  The functionality is reproduced here so that
skysat_stereo does not depend on imview, which relied on matplotlib APIs
(``pyplot.register_cmap``, ``pyplot.get_cmap``) that were removed in
matplotlib 3.9.

Only the pieces actually used by skysat_stereo are kept.  Heavy lifting
(raster reading, hillshade generation, percentile stretch, resolution
computation) reuses ``pygeotools`` which is already a dependency.
"""
import os

import matplotlib
import matplotlib.pyplot as plt
import numpy as np

from pygeotools.lib import malib, geolib, iolib

# Global imshow keyword arguments
# Note: matplotlib v2.0+ interpolates across masked values, disable for now
imshow_kwargs = {'interpolation': 'none'}

# Global cbar keyword arguments
cbar_kwargs = {'orientation': 'vertical'}


def _load_gmt_cpt(fileName, reverse=False):
    """Parse a GMT .cpt color palette into a matplotlib segmentdata dict.

    Adapted from the SciPy cookbook gmtColormap (via imview), trimmed to the
    RGB color model used by the bundled palettes.
    """
    with open(fileName) as f:
        lines = f.readlines()

    x, r, g, b = [], [], [], []
    xtemp = rtemp = gtemp = btemp = None
    for l in lines:
        ls = l.split()
        if l[0] == "#":
            continue
        if ls[0] in ("B", "F", "N"):
            continue
        x.append(float(ls[0]))
        r.append(float(ls[1]))
        g.append(float(ls[2]))
        b.append(float(ls[3]))
        xtemp = float(ls[4])
        rtemp = float(ls[5])
        gtemp = float(ls[6])
        btemp = float(ls[7])
    x.append(xtemp)
    r.append(rtemp)
    g.append(gtemp)
    b.append(btemp)

    x = np.array(x, float)
    r = np.array(r, float)
    g = np.array(g, float)
    b = np.array(b, float)
    if reverse:
        r = r[::-1]
        g = g[::-1]
        b = b[::-1]
    # RGB color model
    r = r / 255.
    g = g / 255.
    b = b / 255.
    xNorm = (x - x[0]) / (x[-1] - x[0])

    red, green, blue = [], [], []
    for i in range(len(x)):
        red.append([xNorm[i], r[i], r[i]])
        green.append([xNorm[i], g[i], g[i]])
        blue.append([xNorm[i], b[i], b[i]])
    return {"red": red, "green": green, "blue": blue}


def _register_rainbow():
    """Register the GMT 'cpt_rainbow' colormap (and its reverse) once."""
    cpt_fn = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'rainbow.cpt')
    if not os.path.exists(cpt_fn):
        return
    for name, reverse in (('cpt_rainbow', False), ('cpt_rainbow_r', True)):
        if name in matplotlib.colormaps:
            continue
        seg = _load_gmt_cpt(cpt_fn, reverse=reverse)
        cmap = matplotlib.colors.LinearSegmentedColormap(name, seg)
        matplotlib.colormaps.register(cmap)


_register_rainbow()


def iv_fn(fn, full=False, return_ma=False, **kwargs):
    ds = iolib.fn_getds(fn)
    return iv_ds(ds, full=full, return_ma=return_ma, **kwargs)


def iv_ds(ds, full=False, return_ma=False, **kwargs):
    if full:
        a = iolib.ds_getma(ds)
    else:
        a, ds = iolib.ds_getma_sub(ds, return_ds=True)
    ax = iv(a, ds=ds, **kwargs)
    if return_ma:
        out = (ax, a)
    else:
        out = ax
    return out


def iv(a, ax=None, clim=None, clim_perc=(2, 98), cmap='cpt_rainbow', label=None, title=None,
       ds=None, res=None, hillshade=False, scalebar=True, cbar=True, skinny=True):
    """Quick image viewer with standardized display settings."""
    if ax is None:
        f, ax = plt.subplots()
    ax.set_aspect('equal')
    if clim is None:
        clim = get_clim(a, clim_perc)
    cm = cmap_setndv(cmap, cmap)
    alpha = 1.0
    if hillshade:
        if ds is not None:
            hs = geolib.gdaldem_mem_ds(ds, processing='hillshade', computeEdges=True, returnma=True)
            b_cm = cmap_setndv('gray', cmap)
            # Set the overlay bad values to completely transparent, otherwise darkens the bg
            cm.set_bad(alpha=0)
            bg_clim = get_clim(hs, (2, 98))
            ax.imshow(hs, cmap=b_cm, clim=bg_clim)
            alpha = 0.5
    if scalebar:
        if ds is not None:
            # Get resolution at center of dataset
            ccoord = geolib.get_center(ds, t_srs=geolib.wgs_srs)
            # Compute resolution in local cartesian coordinates at center
            c_srs = geolib.localortho(*ccoord)
            res = geolib.get_res(ds, c_srs)[0]
        if res is not None:
            sb_loc = best_scalebar_location(a)
            add_scalebar(ax, res, location=sb_loc)
    imgplot = ax.imshow(a, cmap=cm, clim=clim, alpha=alpha, **imshow_kwargs)
    if cbar:
        cbar_kwargs['extend'] = get_cbar_extend(a, clim=clim)
        cbar_kwargs['format'] = get_cbar_format(a)
        add_cbar(ax, imgplot, label=label, skinny=skinny)
    hide_ticks(ax)
    if title is not None:
        ax.set_title(title)
    plt.tight_layout()
    return ax


def get_clim(a, clim_perc=(2, 98)):
    """Compute percentile stretch for input array."""
    clim = malib.calcperc(a, clim_perc)
    if clim[0] == clim[1]:
        if clim[0] > a.fill_value:
            clim = (a.fill_value, clim[0])
        else:
            clim = (clim[0], a.fill_value)
    return clim


def get_cbar_extend(a, clim=None):
    """Determine whether we need to add triangles to ends of colorbar."""
    if clim is None:
        clim = get_clim(a)
    extend = 'both'
    if a.min() >= clim[0] and a.max() <= clim[1]:
        extend = 'neither'
    elif a.min() >= clim[0] and a.max() > clim[1]:
        extend = 'max'
    elif a.min() < clim[0] and a.max() <= clim[1]:
        extend = 'min'
    return extend


def get_cbar_format(a):
    return None


def cmap_setndv(cmap1, cmap2=None):
    """Return a copy of a colormap with default nodata (bad) color set."""
    # Work on a copy so the globally registered colormap is never mutated
    cmap = matplotlib.colormaps[cmap1].copy()
    if cmap2 is None:
        cmap2 = cmap1
    if 'inferno' in cmap2:
        # Set nodata to opaque gray
        cmap.set_bad('0.5', alpha=1)
    else:
        # Set nodata to opaque black
        cmap.set_bad('k', alpha=1)
    return cmap


def hide_ticks(ax):
    ax.get_xaxis().set_visible(False)
    ax.get_yaxis().set_visible(False)


def best_scalebar_location(a, length_pad=0.2, height_pad=0.1):
    """Attempt to determine best corner for scalebar based on unmasked pixels."""
    a = malib.checkma(a)
    length = int(a.shape[1] * length_pad)
    height = int(a.shape[0] * height_pad)
    d = {}
    d['upper right'] = a[0:height, -length:].count()
    d['upper left'] = a[0:height, 0:length].count()
    d['lower right'] = a[-height:, -length:].count()
    d['lower left'] = a[-height:, 0:length].count()
    loc = min(d, key=d.get)
    return loc


def add_scalebar(ax, res, location='lower right', arr=None):
    from matplotlib_scalebar.scalebar import ScaleBar
    if arr is not None:
        location = best_scalebar_location(arr)
    sb = ScaleBar(res, location=location, border_pad=0.5)
    ax.add_artist(sb)


def add_cbar(ax, mappable, label=None, arr=None, clim=None, cbar_kwargs=cbar_kwargs,
             fontsize=10, format=None, skinny=True):
    """Add colorbar to axes for previously plotted mappable (output from imshow)."""
    from mpl_toolkits.axes_grid1 import make_axes_locatable
    fig = ax.get_figure()
    divider = make_axes_locatable(ax)
    if not skinny:
        cax = divider.append_axes("right", size="5%", pad="2%")
    else:
        cax = divider.append_axes("right", size="2%", pad="1%")
    if arr is not None and clim is not None:
        cbar_kwargs['extend'] = get_cbar_extend(arr, clim=clim)
    if format is not None:
        cbar_kwargs['format'] = format
    cbar = fig.colorbar(mappable, cax=cax, **cbar_kwargs)
    if label is not None:
        cbar.set_label(label, size=fontsize)
    cbar.ax.tick_params(labelsize=fontsize)
    # Set colorbar to be opaque, even if image is transparent
    cbar.set_alpha(1)
    return cbar
