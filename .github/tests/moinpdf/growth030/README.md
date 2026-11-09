# MoinPDF 0.30 native integration fixtures

The invoice PDF and XML files are fictional fixtures from MoinPDF 0.30.0.
They contain no customer documents or private account data.

`fixture-2.jpg` is an unchanged image from FH Südwestfalen's
[German handwriting dataset](https://huggingface.co/datasets/fhswf/german_handwriting),
revision `f08067881aafb8ad50f0ca14c1e57314438b79a2`, train row 2.
The publisher declares the Academic Free License 3.0. The full license and
original dataset README are retained alongside the image. `fixtures.json`
records the source row, SHA-256 checksum and expected transcription.

This dataset was a training source for the handwriting model. The test checks
native inference and blank-line rejection through Umbrel's authenticated HTTP
gateway; it is not an independent recognition-accuracy benchmark.
