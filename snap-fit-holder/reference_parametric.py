#!/usr/bin/env python3
"""CR20KB Snap-Fit Holder exact B-Rep reference builder.

The original owner STEP is not committed. This source contains only the measured
canonical geometry and the independent CR20KB parameterization.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import cadquery as cq

REF_D = 22.0
REF_HOLE_Y = 18.0
REF_HOLE_D = 5.0
REF_PLATE_X = 7.0
REF_VOLUME = 18275.377347384932
REF_BBOX = (51.7746491938809, 59.0, 22.0)

PATH = (
    ("M", 0.0, -29.5),
    ("L", 7.0, -29.5),
    ("L", 7.0, -8.5),
    ("A", 7.585786437626905, -7.085786437626905, 9.0, -6.5),
    ("L", 28.0385186031843, -6.5),
    ("A", 28.988900529807285, -6.740234619743761, 29.7109678156766, -7.40322580645161),
    ("A", 37.02554998461908, -12.90169551164647, 46.1662263369287, -12.4723736889024),
    ("A", 48.052336949495334, -12.486308134874132, 49.3561701198421, -13.849255850498),
    ("A", 50.96867245175525, -14.573711666662431, 51.6931282679198, -12.9612093347493),
    ("A", 49.04306700530129, -10.190996836482837, 45.209517756016, -10.1626748576242),
    ("A", 30.0, 0.0, 45.209517756016, 10.1626748576242),
    ("A", 49.043067005301296, 10.190996836482842, 51.6931282679198, 12.9612093347492),
    ("A", 50.96867245175525, 14.57371166666243, 49.3561701198421, 13.849255850498),
    ("A", 48.052336949495285, 12.486308134874111, 46.1662263369287, 12.4723736889024),
    ("A", 37.02554998461909, 12.901695511646468, 29.7109678156766, 7.4032258064516),
    ("A", 28.988900529807268, 6.7402346197437515, 28.0385186031843, 6.5),
    ("L", 9.0, 6.5),
    ("A", 7.585786437626905, 7.085786437626905, 7.0, 8.5),
    ("L", 7.0, 29.5),
    ("L", 0.0, 29.5),
)


def build(
    object_d: float = 22.03,
    fit: float = -0.03,
    width: float | None = None,
    depth_ratio: float = 1.0,
    hole_d: float = 5.0,
) -> cq.Workplane:
    """Build the canonical family.

    object_d: measured cylinder outside diameter, 12..100 mm for public TEST.
    fit: diametral difference clip ID - object OD.
    width: direct axial holder width in mm. If omitted, clip_d * depth_ratio.
    depth_ratio: compatibility/development parameter when width is omitted.
    hole_d: screw through-hole diameter, independent of object diameter.
    """
    if not 12.0 <= object_d <= 100.0:
        raise ValueError("object_d outside public TEST range 12..100 mm")
    if not -2.0 <= fit <= 2.0:
        raise ValueError("fit outside TEST bounds -2..2 mm")
    clip_d = object_d + fit
    if clip_d <= 0:
        raise ValueError("clip inside diameter must be positive")
    if width is None:
        if not 0.08 <= depth_ratio <= 3.0:
            raise ValueError("depth_ratio outside TEST bounds")
        width = clip_d * depth_ratio
    if not 8.0 <= width <= 60.0:
        raise ValueError("width outside TEST bounds 8..60 mm")
    if not 3.0 <= hole_d <= 10.0:
        raise ValueError("hole_d outside TEST bounds 3..10 mm")

    s = clip_d / REF_D
    first = PATH[0]
    wp = cq.Workplane("XY").moveTo(first[1] * s, first[2] * s)
    for cmd in PATH[1:]:
        if cmd[0] == "L":
            wp = wp.lineTo(cmd[1] * s, cmd[2] * s)
        elif cmd[0] == "A":
            wp = wp.threePointArc((cmd[1] * s, cmd[2] * s), (cmd[3] * s, cmd[4] * s))
        else:
            raise ValueError(f"unsupported path command {cmd[0]}")

    result = wp.close().extrude(width / 2.0, both=True)
    plate_x = REF_PLATE_X * s
    hole_y = REF_HOLE_Y * s
    hole_length = plate_x + 4.0
    for y in (-hole_y, hole_y):
        cutter = cq.Solid.makeCylinder(
            hole_d / 2.0,
            hole_length,
            cq.Vector(-2.0, y, 0.0),
            cq.Vector(1.0, 0.0, 0.0),
        )
        result = result.cut(cutter)
    return result


def metrics(model: cq.Workplane) -> dict[str, float | tuple[float, float, float]]:
    solid = model.val()
    box = solid.BoundingBox()
    return {"volume_mm3": solid.Volume(), "bbox_mm": (box.xlen, box.ylen, box.zlen)}


def verify_reference() -> None:
    model = build(object_d=22.03, fit=-0.03, width=22.0, hole_d=5.0)
    data = metrics(model)
    if abs(data["volume_mm3"] - REF_VOLUME) > 1e-6:
        raise AssertionError((data["volume_mm3"], REF_VOLUME))
    for got, expected in zip(data["bbox_mm"], REF_BBOX):
        if abs(got - expected) > 1e-7:
            raise AssertionError((data["bbox_mm"], REF_BBOX))


def export(model: cq.Workplane, stem: Path) -> tuple[Path, Path]:
    step = stem.with_suffix(".step")
    stl = stem.with_suffix(".stl")
    cq.exporters.export(model, str(step))
    cq.exporters.export(model, str(stl), tolerance=0.02, angularTolerance=0.08)
    return step, stl


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--D", type=float, default=22.03, help="measured object OD, mm")
    parser.add_argument("--fit", type=float, default=-0.03, help="clip ID - object OD, diametral mm")
    parser.add_argument("--width", type=float, default=None, help="axial holder width, mm")
    parser.add_argument("--depth-ratio", type=float, default=1.0, help="used only when --width is omitted")
    parser.add_argument("--hole-d", type=float, default=5.0)
    parser.add_argument("--out", type=Path, default=Path("cr20kb-snap-fit-holder"))
    parser.add_argument("--verify-reference", action="store_true")
    args = parser.parse_args()

    if args.verify_reference:
        verify_reference()
    model = build(args.D, args.fit, args.width, args.depth_ratio, args.hole_d)
    step, stl = export(model, args.out)
    print(metrics(model))
    print(step)
    print(stl)


if __name__ == "__main__":
    main()
