# Snap-Fit Holder — CR20KB reference geometry

Status: **public TEST / physically validated baseline**.

The geometry family was reconstructed from an owner-made STEP reference. The raw STEP is intentionally not published; this repository contains the measured B-Rep geometry and reproducible parameter model.

## Reference at clip ID 22.00 mm

- one solid;
- bounding box: **51.774649 × 59.000000 × 22.000000 mm**;
- volume: **18275.377347 mm³**;
- mounting plate: **7.0 mm × 59.0 mm** in top view;
- clip inner radius: **11.0 mm**;
- clip outer radius: **13.5 mm**;
- nominal radial wall: **2.5 mm**;
- ring centre: **41.0 mm** from wall face;
- stem width: **13.0 mm**;
- reference axial width: **22.0 mm**;
- mounting holes: **Ø5.0 mm** at **36.0 mm pitch**;
- four root/junction fillets: **R2.0 mm**;
- compound entry-lip radii include **R2.421270916, R1.25 and R4.921270916 mm**.

`reference_parametric.py` recreates the reference B-Rep to floating-point tolerance.

## Parameter family

`Dclip = Dobject + fit`

`s = Dclip / 22`

The reference top-view structural geometry scales by `s`: plate, stem, reach, ring outside geometry, junction fillets, entry lips and screw-hole pitch.

Axial holder width and screw-hole diameter remain user-controlled parameters.

Public TEST object-diameter range: **12–100 mm**.

## Physical baseline

- measured object OD: **22.03 mm**;
- clip ID: **22.00 mm**;
- PETG HF;
- holder width: **22 mm**;
- result: real repeated insertion/removal gave the desired snap effort and retention.

That sample is the **Normal** preset baseline. Other diameters, materials and fit presets remain experimental until more physical samples are collected.

For large/long objects, particularly toward **60–100 mm**, prefer multiple holders along the object rather than a single excessively wide bracket.

## Inspiration

Inspired by Josh Larsen’s video **3D Printing Snap Fits for Beginners: How to Get Started FAST**:

https://www.youtube.com/watch?v=wv6idwuD7k8

CR20KB is independent and unaffiliated. We do not claim invention of the snap-fit principle.
