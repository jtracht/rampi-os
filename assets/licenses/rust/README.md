# Original Rust dependency notices

`webkit6-rs-LICENSE` is the unmodified MIT license from the upstream repository
at the commit recorded in `webkit6 0.6.1`'s `.cargo_vcs_info.json`:

https://gitlab.gnome.org/World/Rust/webkit6-rs/-/raw/16c6035a19f747322b1814b02ca482e12e23f5fd/LICENSE

The three locked 0.6.0 crates record the earlier revision below. Its original
license was separately retrieved and verified byte-for-byte identical:

https://gitlab.gnome.org/World/Rust/webkit6-rs/-/raw/33ddd822d2665546ee9d69ae006b5ad7541ef8a1/LICENSE

The published `webkit6`, `webkit6-sys`, `javascriptcore6` and `javascriptcore6-sys`
crate archives omit the repository-level license file. The build collector adds
this original notice alongside the license texts from the remaining resolved
Cargo source dependencies and the Rust standard library. System libraries retain
their distro-provided notices collected separately in the image.
