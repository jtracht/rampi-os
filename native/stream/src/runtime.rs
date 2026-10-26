//! Lifecycle and media callbacks around the pinned official Moonlight C API.
//! All GameStream protocols and cryptography remain in existing libraries.
use crate::{
    ffi,
    media::{AudioPlayback, VideoDecoder, VideoFrame},
};
use anyhow::{Context, Result, bail, ensure};
pub use moonlight_common::stream::control::{
    KeyAction, KeyModifiers, MouseButton, MouseButtonAction,
};
use moonlight_common::stream::{
    MoonlightStreamConfig, MoonlightStreamSettings,
    audio::AudioConfig,
    video::{DecodeResult, VideoFormats},
};
use std::{
    ffi::{CStr, CString, c_char, c_void},
    mem::MaybeUninit,
    panic::{AssertUnwindSafe, catch_unwind},
    ptr, slice,
    sync::{
        Arc, Mutex, MutexGuard, RwLock,
        atomic::{AtomicBool, Ordering},
    },
    thread,
    time::Duration,
};
use zeroize::{Zeroize, Zeroizing};

const LIBRARY: &str = "libmoonlight-common.so.2.7.1";
const MAX_VIDEO_BYTES: usize = 4 * 1024 * 1024;
static ACTIVE: AtomicBool = AtomicBool::new(false);
static CURRENT: Mutex<Option<Arc<State>>> = Mutex::new(None);

#[derive(Clone, Debug, PartialEq)]
pub enum Phase {
    Connecting { stage: i32 },
    Connected,
    Ended { code: i32 },
    Failed { stage: i32, code: i32 },
    InternalError,
    Stopped,
}

fn lock<T>(mutex: &Mutex<T>) -> MutexGuard<'_, T> {
    mutex.lock().unwrap_or_else(|error| error.into_inner())
}

struct State {
    api: Arc<ffi::Moonlight>,
    phase: Mutex<Phase>,
    video: Mutex<Option<VideoDecoder>>,
    audio: Mutex<Option<AudioPlayback>>,
    cancel: AtomicBool,
    ended: AtomicBool,
    ffi_active: AtomicBool,
    input_ready: AtomicBool,
    lifecycle: RwLock<()>,
}

fn publish_phase(state: &State, next: Phase) {
    let mut current = lock(&state.phase);
    if !matches!(*current, Phase::InternalError) {
        *current = next;
    }
}

/// Only one official C connection may start/stop per process. No OS service or
/// cross-user state is created; each Linux session has its own process.
struct Lease;
impl Drop for Lease {
    fn drop(&mut self) {
        lock(&CURRENT).take();
        ACTIVE.store(false, Ordering::Release);
    }
}

#[derive(Clone)]
pub struct MoonlightRuntime {
    api: Arc<ffi::Moonlight>,
}

impl MoonlightRuntime {
    pub(crate) fn launch_query_parameters(&self) -> Result<String> {
        // SAFETY: Upstream returns a static, NUL-terminated protocol version
        // string. It is never freed or modified by this caller.
        let query = unsafe { self.api.LiGetLaunchUrlQueryParameters() };
        ensure!(!query.is_null(), "Moonlight-Protokollversion fehlt");
        Ok(unsafe { CStr::from_ptr(query) }.to_str()?.to_owned())
    }
    pub fn load() -> Result<Self> {
        // SAFETY: Only the exact upstream ABI/version represented by the
        // generated headers is loaded; every required symbol must resolve.
        // ldconfig indexes the upstream SONAME (.so.4), not necessarily the
        // exact versioned filename. Reuse normal system installation paths
        // without accepting an unknown SONAME/ABI or requiring shell setup.
        let mut errors = Vec::new();
        for path in [
            LIBRARY.to_owned(),
            format!("/usr/local/lib/{LIBRARY}"),
            format!("/usr/lib/{LIBRARY}"),
            format!("/usr/lib/aarch64-linux-gnu/{LIBRARY}"),
            format!("/usr/lib/arm-linux-gnueabihf/{LIBRARY}"),
            format!("/usr/lib/x86_64-linux-gnu/{LIBRARY}"),
        ] {
            match unsafe { ffi::Moonlight::new(&path) } {
                Ok(api) => return Ok(Self { api: Arc::new(api) }),
                Err(error) => errors.push(error.to_string()),
            }
        }
        bail!(
            "Moonlight-2.7.1-Laufzeit fehlt oder ist inkompatibel: {}",
            errors.join("; ")
        )
    }

    /// Config must come from the authenticated, server-key-pinned launch/resume
    /// path. This adapter does not authenticate or replace Moonlight's pairing.
    /// Preparation does no network I/O. Move PendingConnection to a worker.
    pub fn prepare(
        &self,
        config: MoonlightStreamConfig,
        settings: MoonlightStreamSettings,
    ) -> Result<(RemoteControl, PendingConnection)> {
        // Clear owned keys even if another connection already owns the lease.
        let config = PrivateConfig(config);
        self.reserve()?.prepare(config, settings)
    }

    pub(crate) fn reserve(&self) -> Result<Reservation> {
        ensure!(
            ACTIVE
                .compare_exchange(false, true, Ordering::AcqRel, Ordering::Acquire)
                .is_ok(),
            "Eine Streamingverbindung wird bereits verwendet oder beendet"
        );
        Ok(Reservation {
            api: self.api.clone(),
            lease: Lease,
        })
    }
}

/// Reserve the process-local C connection BEFORE authenticated launch/resume.
/// Dropping on an HTTP failure releases it without starting a C connection.
pub(crate) struct Reservation {
    api: Arc<ffi::Moonlight>,
    lease: Lease,
}
impl Reservation {
    pub(crate) fn prepare_config(
        self,
        config: MoonlightStreamConfig,
        settings: MoonlightStreamSettings,
    ) -> Result<(RemoteControl, PendingConnection)> {
        self.prepare(PrivateConfig(config), settings)
    }
    fn prepare(
        self,
        config: PrivateConfig,
        settings: MoonlightStreamSettings,
    ) -> Result<(RemoteControl, PendingConnection)> {
        ensure!(
            (32..=1920).contains(&settings.width)
                && (32..=1080).contains(&settings.height)
                && (1..=60).contains(&settings.fps)
                && settings.fps_x100 <= 24000
                && (100..=50000).contains(&settings.bitrate)
                && (128..=1472).contains(&settings.packet_size),
            "Ungültige Streaming-Einstellungen"
        );
        ensure!(
            settings.width.is_multiple_of(2)
                && settings.height.is_multiple_of(2)
                && config
                    .server_codec_mode_support
                    .contains(moonlight_common::stream::video::ServerCodecModeSupport::H264),
            "Das Ziel muss H.264 mit geraden Bildmaßen unterstützen"
        );
        ensure!(
            settings.supported_video_formats == VideoFormats::H264
                && settings.audio_config == AudioConfig::STEREO
                && !settings.hdr
                && !settings.enable_mic
                && !config.foundation_enable_mic,
            "Diese Verbindung benötigt H.264 und Stereo ohne HDR/Mikrofon"
        );
        ensure!(
            !config.address.is_empty() && config.address.len() <= 253,
            "Ungültiges Streaming-Ziel"
        );
        let lease = self.lease;
        let state = Arc::new(State {
            api: self.api.clone(),
            phase: Mutex::new(Phase::Connecting { stage: 0 }),
            video: Mutex::new(None),
            audio: Mutex::new(None),
            cancel: AtomicBool::new(false),
            ended: AtomicBool::new(false),
            ffi_active: AtomicBool::new(false),
            input_ready: AtomicBool::new(false),
            lifecycle: RwLock::new(()),
        });
        *lock(&CURRENT) = Some(state.clone());
        Ok((
            RemoteControl {
                state: state.clone(),
            },
            PendingConnection {
                state,
                config,
                settings,
                lease: Some(lease),
            },
        ))
    }
}

/// Cloneable UI endpoint. Frame polling and input never wait for network setup
/// or teardown. Keyboard values come from an existing GUI keycode mapping.
#[derive(Clone)]
pub struct RemoteControl {
    state: Arc<State>,
}
impl RemoteControl {
    pub fn phase(&self) -> Phase {
        lock(&self.state.phase).clone()
    }
    pub fn stop(&self) {
        self.state.cancel.store(true, Ordering::Release);
        if let Ok(_access) = self.state.lifecycle.try_read()
            && self.state.ffi_active.load(Ordering::Acquire)
        {
            // SAFETY: The lifecycle guard prevents teardown/reuse while this
            // connection interrupts its own pending C start call.
            unsafe { self.state.api.LiInterruptConnection() };
        }
    }
    pub fn take_frame(&self) -> Result<Option<VideoFrame>> {
        let Ok(video) = self.state.video.try_lock() else {
            return Ok(None);
        };
        video.as_ref().map_or(Ok(None), VideoDecoder::take_frame)
    }
    fn input(&self, send: impl FnOnce(&ffi::Moonlight) -> i32) -> Result<()> {
        let _access = self
            .state
            .lifecycle
            .try_read()
            .map_err(|_| anyhow::anyhow!("Verbindung wird beendet"))?;
        ensure!(
            self.state.input_ready.load(Ordering::Acquire)
                && !self.state.cancel.load(Ordering::Acquire),
            "Streaming ist nicht verbunden"
        );
        ensure!(
            send(&self.state.api) == 0,
            "Remote-Eingabe wurde nicht angenommen"
        );
        Ok(())
    }
    pub fn keyboard(&self, key: i16, action: KeyAction, modifiers: KeyModifiers) -> Result<()> {
        self.input(|api| unsafe {
            api.LiSendKeyboardEvent(key, action as c_char, modifiers.bits() as c_char)
        })
    }
    pub fn mouse_position(&self, x: i16, y: i16, width: i16, height: i16) -> Result<()> {
        ensure!(
            width > 0 && height > 0 && x >= 0 && y >= 0 && x <= width && y <= height,
            "Ungültige Mausposition"
        );
        self.input(|api| unsafe { api.LiSendMousePositionEvent(x, y, width, height) })
    }
    pub fn mouse_button(&self, button: MouseButton, action: MouseButtonAction) -> Result<()> {
        self.input(|api| unsafe { api.LiSendMouseButtonEvent(action as c_char, button as i32) })
    }
    pub fn scroll(&self, vertical: i16, horizontal: i16) -> Result<()> {
        self.input(|api| unsafe { api.LiSendHighResScrollEvent(vertical) })?;
        self.input(|api| unsafe { api.LiSendHighResHScrollEvent(horizontal) })
    }
}

pub struct PendingConnection {
    state: Arc<State>,
    config: PrivateConfig,
    settings: MoonlightStreamSettings,
    lease: Option<Lease>,
}

// Clear this adapter's owned key copies on every path, including validation,
// abandonment and cancellation before the C start call.
struct PrivateConfig(MoonlightStreamConfig);
impl std::ops::Deref for PrivateConfig {
    type Target = MoonlightStreamConfig;
    fn deref(&self) -> &Self::Target {
        &self.0
    }
}
impl std::ops::DerefMut for PrivateConfig {
    fn deref_mut(&mut self) -> &mut Self::Target {
        &mut self.0
    }
}
impl Drop for PrivateConfig {
    fn drop(&mut self) {
        self.0.encryption.aes_key.0.zeroize();
        self.0.encryption.aes_iv.0.zeroize();
    }
}
impl Drop for PendingConnection {
    fn drop(&mut self) {
        if self.lease.is_some() {
            self.state.cancel.store(true, Ordering::Release);
            if matches!(*lock(&self.state.phase), Phase::Connecting { .. }) {
                *lock(&self.state.phase) = Phase::Stopped;
            }
        }
    }
}

struct StartOutcome(Arc<State>);
impl Drop for StartOutcome {
    fn drop(&mut self) {
        let mut phase = lock(&self.0.phase);
        if matches!(*phase, Phase::Connecting { .. }) {
            *phase = if self.0.cancel.load(Ordering::Acquire) {
                Phase::Stopped
            } else {
                Phase::Failed { stage: 0, code: -1 }
            };
        }
    }
}
pub struct NativeSession {
    state: Arc<State>,
    _lease: Lease,
    started: bool,
}

impl Zeroize for ffi::_STREAM_CONFIGURATION {
    fn zeroize(&mut self) {
        self.remoteInputAesKey.zeroize();
        self.remoteInputAesIv.zeroize();
    }
}

fn optional_string(value: Option<&str>) -> Result<Option<CString>> {
    value
        .map(|text| {
            ensure!(text.len() <= 4096, "Ungültige Streaming-Antwort");
            CString::new(text).context("Ungültige Streaming-Antwort")
        })
        .transpose()
}

impl PendingConnection {
    /// Blocking official C operation: call only on a worker, never the GTK main thread.
    pub fn start(mut self) -> Result<NativeSession> {
        let _outcome = StartOutcome(self.state.clone());
        ensure!(
            !self.state.cancel.load(Ordering::Acquire),
            "Verbindung abgebrochen"
        );
        let address = CString::new(self.config.address.as_str())?;
        let version = CString::new(self.config.version.to_string())?;
        let gfe = optional_string(self.config.gfe_version.as_deref())?;
        let url = optional_string(self.config.rtsp_session_url.as_deref())?;
        // SAFETY: These official initializers fill the complete matching C ABI
        // structures. The generated size/offset assertions cover both targets.
        let (mut server, mut wire, mut video, mut audio, mut callbacks) = unsafe {
            let mut server = MaybeUninit::uninit();
            self.state
                .api
                .LiInitializeServerInformation(server.as_mut_ptr());
            let mut wire = MaybeUninit::uninit();
            self.state
                .api
                .LiInitializeStreamConfiguration(wire.as_mut_ptr());
            let mut video = MaybeUninit::uninit();
            self.state
                .api
                .LiInitializeVideoCallbacks(video.as_mut_ptr());
            let mut audio = MaybeUninit::uninit();
            self.state
                .api
                .LiInitializeAudioCallbacks(audio.as_mut_ptr());
            let mut callbacks = MaybeUninit::uninit();
            self.state
                .api
                .LiInitializeConnectionCallbacks(callbacks.as_mut_ptr());
            (
                server.assume_init(),
                Zeroizing::new(wire.assume_init()),
                video.assume_init(),
                audio.assume_init(),
                callbacks.assume_init(),
            )
        };
        server.address = address.as_ptr();
        server.serverInfoAppVersion = version.as_ptr();
        server.serverInfoGfeVersion = gfe.as_ref().map_or(ptr::null(), |s| s.as_ptr());
        server.rtspSessionUrl = url.as_ref().map_or(ptr::null(), |s| s.as_ptr());
        server.serverCodecModeSupport = self.config.server_codec_mode_support.bits() as i32;
        wire.width = self.settings.width as i32;
        wire.height = self.settings.height as i32;
        wire.fps = self.settings.fps as i32;
        wire.clientRefreshRateX100 = self.settings.fps_x100 as i32;
        wire.bitrate = self.settings.bitrate as i32;
        wire.packetSize = self.settings.packet_size as i32;
        wire.streamingRemotely = self.settings.streaming_remotely as u32 as i32;
        wire.audioConfiguration = self.settings.audio_config.raw() as i32;
        wire.supportedVideoFormats = self.settings.supported_video_formats.bits() as i32;
        wire.colorSpace = self.settings.color_space as u32 as i32;
        wire.colorRange = self.settings.color_range as u32 as i32;
        wire.encryptionFlags = self.settings.encryption_flags.bits() as i32;
        wire.remoteInputAesKey = self.config.encryption.aes_key.0.map(|b| b as c_char);
        let iv = Zeroizing::new(self.config.encryption.aes_iv.to_be_bytes());
        for (target, byte) in wire.remoteInputAesIv.iter_mut().zip(iv.iter()) {
            *target = *byte as c_char;
        }
        self.config.encryption.aes_key.0.zeroize();
        self.config.encryption.aes_iv.0.zeroize();
        video.setup = Some(video_setup);
        video.submitDecodeUnit = Some(video_submit);
        video.cleanup = Some(video_cleanup);
        audio.init = Some(audio_setup);
        audio.decodeAndPlaySample = Some(audio_submit);
        audio.cleanup = Some(audio_cleanup);
        callbacks.stageStarting = Some(stage_starting);
        callbacks.stageFailed = Some(stage_failed);
        callbacks.connectionTerminated = Some(terminated);
        // No variadic Rust logger; the API's optional default remains in use.
        callbacks.logMessage = None;
        let mut driver = NativeSession {
            state: self.state.clone(),
            _lease: self.lease.take().context("Verbindungsbesitz fehlt")?,
            started: false,
        };
        // SAFETY: Single process lease serializes start/stop. Owned strings,
        // structures and callbacks remain live for the whole blocking call.
        let result = unsafe {
            driver.state.api.LiStartConnection(
                &mut server,
                &mut *wire,
                &mut callbacks,
                &mut video,
                &mut audio,
                ptr::null_mut(),
                0,
                ptr::null_mut(),
                0,
            )
        };
        if result != 0 {
            if !matches!(
                *lock(&driver.state.phase),
                Phase::Failed { .. } | Phase::InternalError
            ) {
                publish_phase(
                    &driver.state,
                    Phase::Failed {
                        stage: 0,
                        code: result,
                    },
                );
            }
            bail!("Streamingverbindung fehlgeschlagen ({result})");
        }
        driver.started = true;
        if !driver.state.ended.load(Ordering::Acquire)
            && !driver.state.cancel.load(Ordering::Acquire)
        {
            driver.state.input_ready.store(true, Ordering::Release);
            publish_phase(&driver.state, Phase::Connected);
        }
        Ok(driver)
    }
}

impl NativeSession {
    /// Keeps ownership on the worker until explicit stop or actual host termination.
    pub fn wait(self) {
        while !self.state.cancel.load(Ordering::Acquire)
            && !self.state.ended.load(Ordering::Acquire)
        {
            thread::sleep(Duration::from_millis(20));
        }
    }
}
impl Drop for NativeSession {
    fn drop(&mut self) {
        let _exclusive = self
            .state
            .lifecycle
            .write()
            .unwrap_or_else(|error| error.into_inner());
        self.state.input_ready.store(false, Ordering::Release);
        self.state.ffi_active.store(false, Ordering::Release);
        if self.started {
            // SAFETY: Only this worker owns stop, after all outstanding input calls.
            unsafe { self.state.api.LiStopConnection() };
        }
        lock(&self.state.video).take();
        lock(&self.state.audio).take();
        let mut phase = lock(&self.state.phase);
        if (self.state.cancel.load(Ordering::Acquire) && !matches!(*phase, Phase::InternalError))
            || matches!(*phase, Phase::Connecting { .. } | Phase::Connected)
        {
            *phase = Phase::Stopped;
        }
    }
}

fn callback<T>(fallback: T, f: impl FnOnce(&State) -> T) -> T {
    let Some(state) = lock(&CURRENT).clone() else {
        return fallback;
    };
    match catch_unwind(AssertUnwindSafe(|| f(&state))) {
        Ok(value) => value,
        Err(_) => {
            state.cancel.store(true, Ordering::Release);
            *lock(&state.phase) = Phase::InternalError;
            fallback
        }
    }
}
unsafe extern "C" fn stage_starting(stage: i32) {
    callback((), |state| {
        state.ffi_active.store(true, Ordering::Release);
        publish_phase(state, Phase::Connecting { stage });
        if state.cancel.load(Ordering::Acquire) {
            // SAFETY: This callback belongs to the current start, after its
            // interrupted flag has been initialized by the official library.
            unsafe { state.api.LiInterruptConnection() };
        }
    });
}
unsafe extern "C" fn stage_failed(stage: i32, code: i32) {
    callback((), |state| {
        publish_phase(state, Phase::Failed { stage, code });
    });
}
unsafe extern "C" fn terminated(code: i32) {
    callback((), |state| {
        state.input_ready.store(false, Ordering::Release);
        state.ended.store(true, Ordering::Release);
        publish_phase(state, Phase::Ended { code });
    });
}
unsafe extern "C" fn video_setup(
    format: i32,
    width: i32,
    height: i32,
    _: i32,
    _: *mut c_void,
    _: i32,
) -> i32 {
    callback(-1, |state| {
        if format != VideoFormats::H264.bits() as i32
            || !(32..=1920).contains(&width)
            || !(32..=1080).contains(&height)
        {
            return -1;
        }
        match VideoDecoder::new() {
            Ok(decoder) => {
                *lock(&state.video) = Some(decoder);
                0
            }
            Err(_) => -1,
        }
    })
}
unsafe extern "C" fn video_submit(unit: ffi::PDECODE_UNIT) -> i32 {
    callback(DecodeResult::NeedIdr as i32, |state| {
        // SAFETY: Moonlight owns the callback's linked buffers until return.
        // Check lengths/count before copying; never retain borrowed pointers.
        let Some(unit) = (unsafe { unit.as_ref() }) else {
            return DecodeResult::NeedIdr as i32;
        };
        let Ok(length) = usize::try_from(unit.fullLength) else {
            return DecodeResult::NeedIdr as i32;
        };
        if length == 0 || length > MAX_VIDEO_BYTES {
            return DecodeResult::NeedIdr as i32;
        }
        let mut bytes = Vec::with_capacity(length);
        let mut next = unit.bufferList;
        for _ in 0..1024 {
            if next.is_null() {
                break;
            }
            let entry = unsafe { &*next };
            let Ok(size) = usize::try_from(entry.length) else {
                return DecodeResult::NeedIdr as i32;
            };
            if entry.data.is_null() || size == 0 || bytes.len().saturating_add(size) > length {
                return DecodeResult::NeedIdr as i32;
            }
            bytes
                .extend_from_slice(unsafe { slice::from_raw_parts(entry.data.cast::<u8>(), size) });
            next = entry.next;
        }
        if !next.is_null() || bytes.len() != length {
            return DecodeResult::NeedIdr as i32;
        }
        match lock(&state.video)
            .as_mut()
            .map(|video| video.push_h264(&bytes))
        {
            Some(Ok(())) => DecodeResult::Ok as i32,
            _ => DecodeResult::NeedIdr as i32,
        }
    })
}
unsafe extern "C" fn video_cleanup() {
    callback((), |state| {
        lock(&state.video).take();
    });
}
unsafe extern "C" fn audio_setup(
    config: i32,
    opus: ffi::POPUS_MULTISTREAM_CONFIGURATION,
    _: *mut c_void,
    _: i32,
) -> i32 {
    callback(-1, |state| {
        let Some(opus) = (unsafe { opus.as_ref() }) else {
            return -1;
        };
        if config != AudioConfig::STEREO.raw() as i32
            || opus.sampleRate != 48000
            || opus.channelCount != 2
            || opus.streams != 1
            || opus.coupledStreams != 1
            || opus.mapping[..2] != [0, 1]
        {
            return -1;
        }
        match AudioPlayback::new() {
            Ok(audio) => {
                *lock(&state.audio) = Some(audio);
                0
            }
            Err(_) => -1,
        }
    })
}
unsafe extern "C" fn audio_submit(data: *mut c_char, size: i32) {
    callback((), |state| {
        if data.is_null() || !(1..=65536).contains(&size) {
            return;
        }
        if let Some(audio) = lock(&state.audio).as_mut() {
            // SAFETY: The official callback supplies a live packet of this length.
            let _ =
                audio.push_opus(unsafe { slice::from_raw_parts(data.cast::<u8>(), size as usize) });
        }
    });
}
unsafe extern "C" fn audio_cleanup() {
    callback((), |state| {
        lock(&state.audio).take();
    });
}

#[cfg(test)]
mod tests {
    use super::*;
    use moonlight_common::{
        crypto::openssl::OpenSSLCryptoBackend,
        stream::{
            AesIv, AesKey, EncryptionFlags, StreamingConfig, SunshineEncryption,
            control::ActiveGamepads,
            video::{ColorRange, ColorSpace, ServerCodecModeSupport},
        },
    };
    use std::{net::TcpListener, path::Path, time::Instant};

    fn parameters(port: u16) -> (MoonlightStreamConfig, MoonlightStreamSettings) {
        let crypto = OpenSSLCryptoBackend;
        (
            MoonlightStreamConfig {
                address: "127.0.0.1".into(),
                version: "7.1.431.0".parse().unwrap(),
                gfe_version: Some("3.26.0.154".into()),
                server_codec_mode_support: ServerCodecModeSupport::H264,
                rtsp_session_url: Some(format!("rtsp://127.0.0.1:{port}")),
                encryption: SunshineEncryption {
                    aes_key: AesKey::new_random(&crypto).unwrap(),
                    aes_iv: AesIv::new_random(&crypto).unwrap(),
                },
                apollo_permissions: None,
                foundation_enable_mic: false,
            },
            MoonlightStreamSettings {
                width: 1280,
                height: 720,
                fps: 30,
                fps_x100: 3000,
                bitrate: 8000,
                packet_size: 1024,
                encryption_flags: EncryptionFlags::all(),
                streaming_remotely: StreamingConfig::Auto,
                sops: true,
                hdr: false,
                supported_video_formats: VideoFormats::H264,
                color_space: ColorSpace::Rec709,
                color_range: ColorRange::Limited,
                local_audio_play_mode: false,
                audio_config: AudioConfig::STEREO,
                gamepads_attached: ActiveGamepads::empty(),
                gamepads_persist_after_disconnect: false,
                enable_mic: false,
            },
        )
    }

    #[test]
    #[ignore = "requires the actual pinned official Moonlight C library in an isolated container"]
    fn actual_c_start_cancel_and_reuse() {
        assert!(Path::new("/.dockerenv").exists());
        assert_eq!(std::env::var("RAMPI_TEST_CONTAINER").as_deref(), Ok("1"));
        let runtime = MoonlightRuntime::load().expect("actual versioned official C library");
        let listener = TcpListener::bind("127.0.0.1:0").unwrap();
        let port = listener.local_addr().unwrap().port();
        let (config, settings) = parameters(port);
        let (control, pending) = runtime.prepare(config, settings).unwrap();
        let (config, settings) = parameters(port);
        assert!(
            runtime.prepare(config, settings).is_err(),
            "single global C start lease"
        );
        assert!(
            control
                .keyboard(0x41, KeyAction::Down, KeyModifiers::empty())
                .is_err()
        );
        let worker = thread::spawn(move || pending.start().map(|session| session.wait()));
        let until = Instant::now() + Duration::from_secs(10);
        while matches!(control.phase(), Phase::Connecting { stage } if stage < 4) {
            assert!(
                Instant::now() < until,
                "actual C RTSP stage missing: {:?}",
                control.phase()
            );
            thread::sleep(Duration::from_millis(10));
        }
        assert!(
            matches!(control.phase(), Phase::Connecting { stage: 4 }),
            "{:?}",
            control.phase()
        );
        let submitted = Instant::now();
        control.stop();
        assert!(
            submitted.elapsed() < Duration::from_secs(1),
            "UI cancellation must not wait for the native network timeout"
        );
        let until = Instant::now() + Duration::from_secs(20);
        while !worker.is_finished() {
            assert!(
                Instant::now() < until,
                "native C cancellation did not finish"
            );
            thread::sleep(Duration::from_millis(10));
        }
        assert!(
            worker.join().unwrap().is_err(),
            "silent RTSP peer must not connect"
        );
        assert_eq!(control.phase(), Phase::Stopped);
        assert!(control.take_frame().unwrap().is_none());

        let (config, settings) = parameters(port);
        let (next_control, next_pending) = runtime
            .prepare(config, settings)
            .expect("lease after C cleanup");
        control.stop(); // An old endpoint must not interrupt the next connection.
        assert!(!next_control.state.cancel.load(Ordering::Acquire));
        next_control.stop();
        assert!(
            next_pending.start().is_err(),
            "cancel before entering native start"
        );
        assert_eq!(next_control.phase(), Phase::Stopped);
        let (config, settings) = parameters(port);
        let (abandoned, pending) = runtime
            .prepare(config, settings)
            .expect("lease after pending cancel");
        drop(pending);
        assert!(!ACTIVE.load(Ordering::Acquire));
        assert_eq!(abandoned.phase(), Phase::Stopped);
        let (mut invalid, settings) = parameters(port);
        invalid.address = "invalid\0peer".into();
        let (invalid_control, pending) = runtime.prepare(invalid, settings).unwrap();
        assert!(pending.start().is_err());
        assert!(matches!(invalid_control.phase(), Phase::Failed { .. }));
        assert!(!ACTIVE.load(Ordering::Acquire));
        println!(
            "RAMPI_STREAM_NATIVE_C_LIFECYCLE_OK: actual C RTSP, cancellation, reuse and stale endpoint isolation"
        );
    }
}
