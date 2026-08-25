# CR20KB Snap-Fit Holder Generator

Free/open-source parametric snap-fit wall holder for cylindrical objects.

**Live generator:** https://cr20kb.com/snap-fit-holder/

Enter the measured outside diameter of a cylindrical object, choose the holder width and fit preset, and download a printable STL locally in the browser.

## Physical baseline

The first baseline was physically printed and tested by CR20KB:

- material: **PETG HF**;
- measured object OD: **22.03 mm**;
- clip inside diameter: **22.00 mm**;
- holder axial width: **22 mm**;
- result: insertion effort and retention were reported as **exactly right** after real repeated use.

This tested geometry is the default **Normal** preset.

Other diameters, materials and Loose/Firm/Tight presets are still experimental. Print one sample before relying on a new combination.

## Public TEST range

- object diameter: **12–100 mm**;
- adjustable axial holder width;
- adjustable screw through-hole diameter;
- Normal / Loose / Firm / Tight fit presets;
- exact diametral fit offset available in advanced settings;
- browser-local STL export; dimensions are not sent to CR20KB analytics.

For large or long cylindrical objects, especially toward 60–100 mm diameter, using **2–3 separate holders** along the object is generally preferable to making one excessively wide bracket.

## Geometry

The canonical family is reconstructed from a CR20KB owner-made STEP reference. The raw STEP is not published; the measured B-Rep dimensions and reproducible path are included in source form.

At the reference clip ID of 22.00 mm:

- reference B-Rep: 51.774649 × 59 × 22 mm;
- radial clip wall: 2.5 mm;
- mounting plate: 7 mm × 59 mm in top view;
- ring center: 41 mm from wall face;
- stem: 13 mm;
- screw holes: Ø5 mm at 36 mm pitch;
- four R2 junction fillets;
- compound entry lips preserved from the tested reference.

`reference_parametric.py` is the exact CadQuery B-Rep reference builder. `core.js` is the browser-local mesh implementation used by the live generator.

## Inspiration and attribution

This project was inspired by Josh Larsen’s public video:

**3D Printing Snap Fits for Beginners: How to Get Started FAST**  
https://www.youtube.com/watch?v=wv6idwuD7k8

CR20KB is not affiliated with Josh Larsen. The CR20KB code, parameterization, testing and web implementation are independent. We do not claim to have invented the snap-fit principle.

## License and rights

CR20KB code in this folder is released under the **MIT License**. See `LICENSE`.

The MIT License covers the CR20KB software/code only. It does not grant third-party patent, industrial-design, trademark, copyright or other rights that may apply in a particular jurisdiction or application.

## Safety

This is a practical 3D-printing TEST, not a certified structural component. Material, print orientation, temperature, creep, impact, UV exposure and printer calibration can all change performance. For valuable, heavy or safety-critical objects, validate the actual printed installation under the real load.

## CR20KB

More practical generators and engineering tools: https://cr20kb.com/
