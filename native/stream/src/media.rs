//! Windowless media adapters for Moonlight's encoded H.264 and stereo Opus.
//! GStreamer owns codec selection, decoding, conversion, scheduling and audio.
use anyhow::{Context, Result, bail, ensure};
use gstreamer::{self as gst, prelude::*};
use gstreamer_app::{AppSink, AppSrc};
use gstreamer_video as video;

const VIDEO_QUEUE_BYTES: u64 = 4 * 1024 * 1024;
const AUDIO_QUEUE_BYTES: u64 = 128 * 1024;
const MAX_QUEUED_BUFFERS: u64 = 8;

/// A decoded frame to hand to the existing GTK/RDW renderer on its main thread.
pub struct VideoFrame {
    pub width: u32,
    pub height: u32,
    pub stride: usize,
    pub rgba: Vec<u8>,
}

fn pipeline(description: &str) -> Result<gst::Pipeline> {
    gst::init().context("GStreamer konnte nicht initialisiert werden")?;
    gst::parse::launch(description)?
        .downcast::<gst::Pipeline>()
        .map_err(|_| anyhow::anyhow!("GStreamer-Pipeline fehlt"))
}

fn source(pipeline: &gst::Pipeline, bytes: u64) -> Result<AppSrc> {
    let source = pipeline
        .by_name("input")
        .context("Medieneingang fehlt")?
        .downcast::<AppSrc>()
        .map_err(|_| anyhow::anyhow!("Ungültiger Medieneingang"))?;
    source.set_max_bytes(bytes);
    source.set_max_buffers(MAX_QUEUED_BUFFERS);
    source.set_block(false);
    Ok(source)
}

fn check_error(pipeline: &gst::Pipeline) -> Result<()> {
    let bus = pipeline.bus().context("GStreamer-Bus fehlt")?;
    if let Some(message) = bus.pop_filtered(&[gst::MessageType::Error])
        && let gst::MessageView::Error(error) = message.view()
    {
        bail!("Medienverarbeitung fehlgeschlagen: {}", error.error());
    }
    Ok(())
}

fn push(source: &AppSrc, packet: &[u8], budget: u64) -> Result<()> {
    ensure!(
        !packet.is_empty() && packet.len() as u64 <= budget,
        "Ungültige oder zu große Medieneinheit"
    );
    ensure!(
        source
            .current_level_bytes()
            .saturating_add(packet.len() as u64)
            <= budget
            && source.current_level_buffers() < MAX_QUEUED_BUFFERS,
        "Medienpuffer ausgelastet"
    );
    // &mut decoder methods serialize pushes. Never block the protocol callback
    // or keep an unbounded encoded queue while the UI is on another page.
    source.push_buffer(gst::Buffer::from_mut_slice(packet.to_vec()))?;
    Ok(())
}

pub struct VideoDecoder {
    pipeline: gst::Pipeline,
    source: AppSrc,
    sink: AppSink,
}

impl VideoDecoder {
    pub fn new() -> Result<Self> {
        // decodebin selects an installed suitable decoder, including hardware
        // backends where supported. No autovideosink or external window exists.
        let pipeline = pipeline(
            "appsrc name=input is-live=true format=time do-timestamp=true \
             caps=video/x-h264,stream-format=byte-stream,alignment=au ! h264parse ! decodebin ! \
             videoconvert ! video/x-raw,format=RGBA,width=(int)[1,1920],height=(int)[1,1080] ! \
             appsink name=output max-buffers=1 drop=true sync=false wait-on-eos=false",
        )?;
        let source = source(&pipeline, VIDEO_QUEUE_BYTES)?;
        let sink = pipeline
            .by_name("output")
            .context("Bildausgang fehlt")?
            .downcast::<AppSink>()
            .map_err(|_| anyhow::anyhow!("Ungültiger Bildausgang"))?;
        pipeline.set_state(gst::State::Playing)?;
        Ok(Self {
            pipeline,
            source,
            sink,
        })
    }

    /// One complete Annex-B access unit from the existing Moonlight callback.
    pub fn push_h264(&mut self, unit: &[u8]) -> Result<()> {
        check_error(&self.pipeline)?;
        push(&self.source, unit, VIDEO_QUEUE_BYTES)
    }

    /// Nonblocking; retaining at most one decoded frame prevents a hidden-page backlog.
    pub fn take_frame(&self) -> Result<Option<VideoFrame>> {
        check_error(&self.pipeline)?;
        let Some(sample) = self.sink.try_pull_sample(gst::ClockTime::ZERO) else {
            return Ok(None);
        };
        let caps = sample.caps().context("Bildformat fehlt")?;
        let info = video::VideoInfo::from_caps(caps)?;
        ensure!(
            info.format() == video::VideoFormat::Rgba
                && (1..=1920).contains(&info.width())
                && (1..=1080).contains(&info.height()),
            "Nicht unterstütztes Bildformat"
        );
        let stride = usize::try_from(info.stride()[0])?;
        ensure!(stride >= info.width() as usize * 4, "Ungültige Bildzeilen");
        let size = stride
            .checked_mul(info.height() as usize)
            .context("Bild zu groß")?;
        ensure!(size <= 16 * 1024 * 1024, "Bildspeicherbudget überschritten");
        let buffer = sample.buffer().context("Bilddaten fehlen")?;
        let mapping = buffer.map_readable()?;
        let offset = info.offset()[0];
        let end = offset.checked_add(size).context("Ungültige Bilddaten")?;
        let rgba = mapping
            .as_slice()
            .get(offset..end)
            .context("Unvollständiges Bild")?
            .to_vec();
        Ok(Some(VideoFrame {
            width: info.width(),
            height: info.height(),
            stride,
            rgba,
        }))
    }
}

impl Drop for VideoDecoder {
    fn drop(&mut self) {
        let _ = self.pipeline.set_state(gst::State::Null);
    }
}

pub struct AudioPlayback {
    pipeline: gst::Pipeline,
    source: AppSrc,
}

impl AudioPlayback {
    pub fn new() -> Result<Self> {
        Self::with_output("autoaudiosink sync=false")
    }

    fn with_output(output: &str) -> Result<Self> {
        let pipeline = pipeline(&format!(
            "appsrc name=input is-live=true format=time do-timestamp=true \
             caps=audio/x-opus,rate=48000,channels=2,channel-mapping-family=0 ! \
             opusdec ! audioconvert ! audioresample ! {output}"
        ))?;
        let source = source(&pipeline, AUDIO_QUEUE_BYTES)?;
        pipeline.set_state(gst::State::Playing)?;
        Ok(Self { pipeline, source })
    }

    pub fn push_opus(&mut self, packet: &[u8]) -> Result<()> {
        check_error(&self.pipeline)?;
        ensure!(packet.len() <= 64 * 1024, "Ungültiges Opus-Paket");
        push(&self.source, packet, AUDIO_QUEUE_BYTES)
    }
}

impl Drop for AudioPlayback {
    fn drop(&mut self) {
        let _ = self.pipeline.set_state(gst::State::Null);
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::{
        process::Command,
        thread,
        time::{Duration, Instant},
    };

    fn encoded_color(color: &str) -> Vec<u8> {
        let output = Command::new("ffmpeg")
            .args([
                "-v",
                "error",
                "-f",
                "lavfi",
                "-i",
                &format!("color=c={color}:size=160x96:rate=10"),
                "-frames:v",
                "1",
                "-c:v",
                "libx264",
                "-preset",
                "ultrafast",
                "-tune",
                "zerolatency",
                "-f",
                "h264",
                "pipe:1",
            ])
            .output()
            .expect("actual FFmpeg encoder required");
        assert!(
            output.status.success(),
            "{}",
            String::from_utf8_lossy(&output.stderr)
        );
        assert!(!output.stdout.is_empty());
        output.stdout
    }

    fn next_frame(decoder: &VideoDecoder) -> VideoFrame {
        let until = Instant::now() + Duration::from_secs(10);
        loop {
            if let Some(frame) = decoder.take_frame().expect("real video decoding") {
                return frame;
            }
            assert!(Instant::now() < until, "decoded frame missing");
            thread::sleep(Duration::from_millis(10));
        }
    }

    #[test]
    #[ignore = "run explicitly in tests/streaming/Dockerfile.media; real codecs and FFmpeg required"]
    fn actual_h264_and_opus_roundtrip() {
        let mut decoder = VideoDecoder::new().expect("windowless video pipeline");
        assert!(decoder.push_h264(&[]).is_err());
        assert!(
            decoder
                .push_h264(&vec![0; VIDEO_QUEUE_BYTES as usize + 1])
                .is_err()
        );
        for (color, channel) in [("red", 0), ("blue", 2)] {
            decoder
                .push_h264(&encoded_color(color))
                .expect("encoded H264 input");
            let frame = next_frame(&decoder);
            assert_eq!((frame.width, frame.height), (160, 96));
            let pixel = &frame.rgba[frame.stride * 48 + 80 * 4..][..4];
            assert!(pixel[channel] > 180, "decoded {color}: {pixel:?}");
            assert!(pixel[2 - channel] < 50, "decoded {color}: {pixel:?}");
            assert_eq!(pixel[3], 255);
        }
        drop(decoder);
        // A new decoder must work after teardown, rather than reusing old frames.
        let mut decoder = VideoDecoder::new().expect("recreated video decoder");
        decoder
            .push_h264(&encoded_color("green"))
            .expect("reconnect H264");
        let frame = next_frame(&decoder);
        let pixel = &frame.rgba[frame.stride * 48 + 80 * 4..][..4];
        assert!(pixel[1] > 80 && pixel[0] < 50 && pixel[2] < 50, "{pixel:?}");

        let encoded = pipeline(
            "audiotestsrc wave=sine freq=997 samplesperbuffer=240 \
            num-buffers=80 ! audio/x-raw,rate=48000,channels=2 ! opusenc frame-size=5 ! \
            appsink name=encoded sync=false",
        )
        .expect("real Opus encoder");
        let source_sink = encoded
            .by_name("encoded")
            .unwrap()
            .downcast::<AppSink>()
            .unwrap();
        let mut playback = AudioPlayback::with_output(
            "audio/x-raw,format=F32LE,rate=48000,channels=2 ! \
            appsink name=capture max-buffers=128 sync=false wait-on-eos=false",
        )
        .expect("production Opus decoder with PCM capture");
        let capture = playback
            .pipeline
            .by_name("capture")
            .unwrap()
            .downcast::<AppSink>()
            .unwrap();
        assert!(playback.push_opus(&[]).is_err());
        assert!(playback.push_opus(&vec![0; 65537]).is_err());
        encoded.set_state(gst::State::Playing).unwrap();
        let mut pcm = Vec::new();
        let mut packets = 0;
        while let Some(sample) = source_sink.try_pull_sample(gst::ClockTime::from_seconds(2)) {
            let buffer = sample.buffer().unwrap().map_readable().unwrap();
            playback
                .push_opus(buffer.as_slice())
                .expect("actual Opus packet");
            packets += 1;
            thread::sleep(Duration::from_millis(5));
            while let Some(sample) = capture.try_pull_sample(gst::ClockTime::ZERO) {
                let buffer = sample.buffer().unwrap().map_readable().unwrap();
                assert_eq!(buffer.len() % 8, 0);
                pcm.extend(
                    buffer
                        .as_chunks::<8>()
                        .0
                        .iter()
                        .map(|pair| f32::from_le_bytes(pair[..4].try_into().unwrap())),
                );
            }
        }
        encoded.set_state(gst::State::Null).unwrap();
        assert!(packets >= 60, "encoded packets: {packets}");
        assert!(pcm.len() > 12000, "decoded PCM samples: {}", pcm.len());
        let pcm = &pcm[200..];
        let rms =
            (pcm.iter().map(|v| f64::from(*v).powi(2)).sum::<f64>() / pcm.len() as f64).sqrt();
        let crossings = pcm.windows(2).filter(|v| v[0] <= 0.0 && v[1] > 0.0).count();
        let frequency = crossings as f64 * 48000.0 / pcm.len() as f64;
        assert!(rms > 0.05, "decoded audio RMS: {rms}");
        assert!(
            (950.0..1040.0).contains(&frequency),
            "decoded frequency: {frequency}"
        );
        // Exercise the production queue guard against a real blocked consumer.
        // This fixture intentionally never pulls its one buffered sample.
        let blocked = pipeline(
            "appsrc name=input is-live=true format=time \
            caps=application/octet-stream ! appsink max-buffers=1 drop=false \
            sync=false wait-on-eos=false",
        )
        .unwrap();
        let blocked_source = source(&blocked, 1024).unwrap();
        blocked.set_state(gst::State::Playing).unwrap();
        let mut refused = false;
        for _ in 0..100 {
            if push(&blocked_source, &[0; 256], 1024).is_err() {
                refused = true;
                break;
            }
            thread::sleep(Duration::from_millis(1));
        }
        let queued_bytes = blocked_source.current_level_bytes();
        let queued_buffers = blocked_source.current_level_buffers();
        blocked.set_state(gst::State::Null).unwrap();
        assert!(refused, "blocked consumer must cause bounded backpressure");
        assert!(queued_bytes <= 1024 && queued_buffers <= MAX_QUEUED_BUFFERS);
        println!(
            "RAMPI_STREAM_GSTREAMER_MEDIA_OK: actual H264 colors, teardown/recreate and Opus {frequency:.1}Hz RMS{rms:.3}"
        );
    }
}
