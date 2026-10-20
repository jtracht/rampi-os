//! Unequal edge harmonics; rendering and frame scheduling remain GTK/Cairo's job.
use std::f64::consts::TAU;
pub fn edges(seconds: f64, selected: bool, impulse_age: Option<f64>, reduced: bool) -> [f64; 4] {
    if reduced {
        return [0.0; 4];
    }
    let phase = seconds * TAU / 2.7;
    let idle = if selected { 4.0 } else { 0.0 };
    let pulse = impulse_age
        .filter(|age| (0.0..0.24).contains(age))
        .map_or(0.0, |age| 28.0 * (-age * 13.0).exp() * (age * 38.0).sin());
    [
        pulse * 0.85 + idle * phase.sin(),
        -pulse * 0.55 + idle * (phase * 2.0 + 1.3).sin(),
        pulse * 0.68 + idle * (phase + 3.8).sin(),
        -pulse * 0.93 + idle * (phase * 3.0 + 0.6).cos(),
    ]
}
#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn waves_are_asymmetric_bounded_and_stoppable() {
        for i in 0..1000 {
            let t = i as f64 / 100.0;
            assert!(
                edges(t, true, Some(t), false)
                    .iter()
                    .all(|v| v.is_finite() && v.abs() < 32.0)
            );
            assert_eq!(edges(t, true, Some(0.05), true), [0.0; 4]);
        }
        let e = edges(0.11, true, Some(0.06), false);
        assert!(e[0] != e[1] && e[1] != e[2] && e[2] != e[3]);
        assert_eq!(edges(1.0, false, Some(1.0), false), [0.0; 4]);
    }
}
