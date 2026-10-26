//! Rampi messages rendered by Project Fluent; no custom translation engine.
use fluent_bundle::{FluentArgs, FluentBundle, FluentResource};
use std::sync::atomic::{AtomicUsize, Ordering};

static LANGUAGE: AtomicUsize = AtomicUsize::new(0);
pub const LANGUAGES: [(&str, &str, &str); 2] = [
    ("de", "Deutsch", "de_DE.UTF-8"),
    ("en", "English", "en_US.UTF-8"),
];

fn bundle(language: &str, source: &str) -> Option<FluentBundle<FluentResource>> {
    let resource = FluentResource::try_new(source.to_owned()).ok()?;
    let identifier: unic_langid::LanguageIdentifier = language.parse().ok()?;
    let mut bundle = FluentBundle::new(vec![identifier]);
    bundle.add_resource(resource).ok()?;
    Some(bundle)
}

thread_local! {
    static MESSAGES: [Option<FluentBundle<FluentResource>>; 2] = [
        bundle("de", include_str!("../locales/de.ftl")),
        bundle("en", include_str!("../locales/en.ftl")),
    ];
}

pub fn select(language: &str) -> bool {
    if let Some(index) = LANGUAGES.iter().position(|item| item.0 == language) {
        LANGUAGE.store(index, Ordering::Relaxed);
        true
    } else {
        false
    }
}

pub fn text(id: &str, arguments: &[(&str, &str)]) -> String {
    MESSAGES.with(|messages| {
        let Some(bundle) = &messages[LANGUAGE.load(Ordering::Relaxed)] else {
            return format!("[{id}]");
        };
        let Some(pattern) = bundle.get_message(id).and_then(|message| message.value()) else {
            return format!("[{id}]");
        };
        let mut args = FluentArgs::new();
        for &(name, value) in arguments {
            args.set(name, value);
        }
        let mut errors = Vec::new();
        let result = bundle.format_pattern(pattern, Some(&args), &mut errors);
        if errors.is_empty() {
            result.into_owned()
        } else {
            format!("[{id}]")
        }
    })
}

pub fn locale(language: &str) -> Option<&'static str> {
    LANGUAGES
        .iter()
        .find(|item| item.0 == language)
        .map(|item| item.2)
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::collections::BTreeSet;

    #[test]
    fn both_catalogs_parse_have_matching_messages_and_resolve_named_arguments() {
        let mut expected = None;
        for (language, source) in [
            ("de", include_str!("../locales/de.ftl")),
            ("en", include_str!("../locales/en.ftl")),
        ] {
            let catalog = bundle(language, source).expect("Valid Fluent catalog required");
            let ids: BTreeSet<_> = source
                .lines()
                .filter(|line| !line.starts_with(char::is_whitespace) && !line.starts_with('#'))
                .filter_map(|line| line.split_once(" = ").map(|(id, _)| id))
                .collect();
            assert!(
                ids.len() > 50,
                "Missing application navigation/setup translations"
            );
            if let Some(previous) = &expected {
                assert_eq!(previous, &ids);
            }
            expected = Some(ids.clone());
            for id in ids {
                let pattern = catalog
                    .get_message(id)
                    .and_then(|message| message.value())
                    .unwrap();
                let mut args = FluentArgs::new();
                for (name, value) in [
                    ("url", "https://example.invalid"),
                    ("count", "2"),
                    ("step", "1"),
                    ("total", "12"),
                    ("title", "Keyboard"),
                    ("error", "Fixture error"),
                    ("hash", "0123456789abcdef"),
                    ("name", "My host"),
                    ("address", "host.example"),
                    ("account", "fixture"),
                    ("output", "HDMI-A-1"),
                    ("mode", "1280x720"),
                    ("seconds", "15"),
                ] {
                    args.set(name, value);
                }
                let mut errors = Vec::new();
                let message = catalog.format_pattern(pattern, Some(&args), &mut errors);
                assert!(errors.is_empty(), "{language}/{id}: {errors:?}");
                assert!(!message.is_empty());
            }
        }
        assert_eq!(locale("en"), Some("en_US.UTF-8"));
        assert_eq!(locale("de"), Some("de_DE.UTF-8"));
        assert_eq!(locale("../untrusted"), None);
    }
}
