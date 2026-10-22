# Original Rust dependency notices

`webkit6-rs-LICENSE` is the unmodified MIT license from the upstream repository
at the commit recorded in the locked crates' `.cargo_vcs_info.json`:

https://gitlab.gnome.org/World/Rust/webkit6-rs/-/raw/16c6035a19f747322b1814b02ca482e12e23f5fd/LICENSE

The published `webkit6`, `webkit6-sys`, `javascriptcore6` and `javascriptcore6-sys`
crate archives omit the repository-level license file. The build collector adds
this original notice alongside the license texts from the remaining resolved
Cargo source dependencies and the Rust standard library. System libraries retain
their distro-provided notices collected separately in the image.
