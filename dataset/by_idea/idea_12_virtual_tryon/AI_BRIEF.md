# AI Brief — Idea #12: Virtual Tryon

*Paste this whole file into your AI assistant. It contains the idea, the recommended approach, the exact datasets (with decoded columns), how to load them, the pitfalls, and first steps.*

> DESCOPED - Virtual Try-On image data (VITON-HD/DressCode) not feasible in the 1-month timeline. Code repos kept under 03_catalog_images.

## Design note for whoever picks this back up

Mentor feedback (2026-08-06): whenever the actual image-generation call is
built, the prompt sent to the image-gen model must include **product
context** — category, material/attributes, a short description pulled from
`product.attributes`/`product.category` — alongside the user's photo and the
garment photo. Two raw images with no textual context is what causes
nonsensical/irrelevant generations (wrong garment fit, wrong material
rendering, ignoring product specifics). Not implemented — there is no
image-gen service or config in this repo yet — but bake this in from the
first version rather than bolting it on after the fact.
