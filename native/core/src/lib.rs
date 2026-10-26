//! Platform-independent Rampi state, configuration and safe command construction.
pub mod accounts;
pub mod board;
pub mod config;
#[cfg(test)]
mod connector_tests;
pub mod connectors;
pub mod i18n;
pub mod motion;
pub mod tailscale;

mod gitea;
