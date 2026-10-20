//! Thin binding to libcanberra's existing low-latency UI sound player.
//! No mixer, decoder, audio protocol or device handling is implemented here.
use std::{
    ffi::{CString, c_char, c_int, c_void},
    path::Path,
    ptr::NonNull,
};
#[link(name = "canberra")]
unsafe extern "C" {
    fn ca_context_create(context: *mut *mut c_void) -> c_int;
    fn ca_context_destroy(context: *mut c_void) -> c_int;
    fn ca_context_set_driver(context: *mut c_void, driver: *const c_char) -> c_int;
    fn ca_context_play(context: *mut c_void, id: u32, ...) -> c_int;
}
pub struct Sound {
    context: NonNull<c_void>,
    select: CString,
    click: CString,
}
impl Sound {
    pub fn new(select: &Path, click: &Path) -> Option<Self> {
        use std::os::unix::ffi::OsStrExt;
        let (select, click) = (
            CString::new(select.as_os_str().as_bytes()).ok()?,
            CString::new(click.as_os_str().as_bytes()).ok()?,
        );
        let mut raw = std::ptr::null_mut();
        // SAFETY: libcanberra writes a context pointer to valid stack storage.
        // The opaque context is only used on GTK's main thread and freed once.
        if unsafe { ca_context_create(&mut raw) } < 0 {
            return None;
        }
        let context = NonNull::new(raw)?;
        let result = Self {
            context,
            select,
            click,
        };
        // PulseAudio's API also addresses the installed PipeWire Pulse service.
        // Failure leaves sound optional; no fallback process/window is started.
        if unsafe { ca_context_set_driver(result.context.as_ptr(), c"pulse".as_ptr()) } < 0 {
            return None;
        }
        Some(result)
    }
    pub fn play(&self, click: bool) -> i32 {
        let path = if click { &self.click } else { &self.select };
        // SAFETY: all variadic property arguments are valid NUL-terminated
        // strings, and the list ends in a null key as required by canberra.h.
        // The library copies properties before returning; self owns the context.
        unsafe {
            ca_context_play(
                self.context.as_ptr(),
                u32::from(click),
                c"media.filename".as_ptr(),
                path.as_ptr(),
                std::ptr::null::<c_char>(),
            )
        }
    }
}
impl Drop for Sound {
    fn drop(&mut self) {
        // SAFETY: this is the sole owning handle returned by ca_context_create.
        unsafe {
            ca_context_destroy(self.context.as_ptr());
        }
    }
}
