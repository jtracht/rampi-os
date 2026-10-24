//! Thin Rust adapters for existing Moonlight/OpenSSL/curl/GStreamer facilities.
//! Streaming remains under development until the actual GTK integration passes.
#[cfg(target_os = "linux")]
#[allow(
    non_snake_case,
    non_camel_case_types,
    non_upper_case_globals,
    dead_code
)]
#[allow(unsafe_op_in_unsafe_fn, clippy::all)]
mod ffi;
#[cfg(target_os = "linux")]
pub mod transport;
