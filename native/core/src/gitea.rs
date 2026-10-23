//! Official repository project API: metadata, ordered columns, paged issues.
use crate::board::{Board, Card};
use anyhow::{Context, Result, ensure};
use serde_json::Value;

pub struct Project {
    endpoint: String,
    project_id: i64,
    columns: Vec<(i64, i64, String)>,
    stage: u8,
    column: usize,
    page: usize,
}
fn segment(s: &str) -> bool {
    !s.is_empty()
        && s.len() <= 128
        && s != "."
        && s != ".."
        && s.bytes()
            .all(|c| c.is_ascii_alphanumeric() || b"_.-".contains(&c))
}
impl Project {
    pub fn new(source: &str) -> Result<Self> {
        let expanded;
        let (site, path) = if let Some(parts) = source.split_once('#') {
            parts
        } else {
            let (repository, id) = source
                .trim_end_matches('/')
                .rsplit_once("/projects/")
                .context("Die HTTPS-Adresse des Gitea-Repository-Projekts einfügen")?;
            let (owner_path, repo) = repository
                .rsplit_once('/')
                .context("Gitea-Repository fehlt")?;
            let (site, owner) = owner_path
                .rsplit_once('/')
                .context("Gitea-Eigentümer fehlt")?;
            expanded = format!("repos/{owner}/{repo}/{id}");
            (site, expanded.as_str())
        };
        crate::config::validate_https(site)?;
        let site = site.trim_end_matches('/');
        let mut parts = site[8..].split('/');
        let authority = parts.next().unwrap_or("");
        let (host, port) = authority.split_once(':').unwrap_or((authority, "443"));
        ensure!(
            host.len() <= 253
                && !host.is_empty()
                && host.split('.').all(|label| !label.is_empty()
                    && label.len() <= 63
                    && !label.starts_with('-')
                    && !label.ends_with('-')
                    && label
                        .bytes()
                        .all(|c| c.is_ascii_alphanumeric() || c == b'-'))
                && port.parse::<u16>().is_ok_and(|p| p > 0)
                && parts.all(segment),
            "Ungültiger Gitea-Server oder Installationspfad"
        );
        let path: Vec<_> = path.split('/').collect();
        ensure!(
            path.len() == 4 && path[0] == "repos" && segment(path[1]) && segment(path[2]),
            "Gitea benötigt repos/EIGENTÜMER/REPOSITORY/PROJEKT-ID"
        );
        let project_id: i64 = path[3].parse().context("Ungültige Gitea-Projekt-ID")?;
        ensure!(project_id > 0, "Ungültige Gitea-Projekt-ID");
        Ok(Self {
            endpoint: format!(
                "{site}/api/v1/repos/{}/{}/projects/{project_id}",
                path[1], path[2]
            ),
            project_id,
            columns: Vec::new(),
            stage: 0,
            column: 0,
            page: 1,
        })
    }
    pub fn url(&self) -> String {
        match self.stage {
            0 => self.endpoint.clone(),
            1 => format!("{}/columns?limit=100&page={}", self.endpoint, self.page),
            _ => format!(
                "{}/columns/{}/issues?limit=100&page={}",
                self.endpoint, self.columns[self.column].0, self.page
            ),
        }
    }
    pub fn accept(&mut self, data: &Value, board: &mut Board) -> Result<bool> {
        if self.stage == 0 {
            ensure!(
                data["id"].as_i64() == Some(self.project_id),
                "Falsches Gitea-Projekt"
            );
            board.title = data["title"]
                .as_str()
                .context("Gitea-Projekttitel fehlt")?
                .into();
            self.stage = 1;
            return Ok(false);
        }
        let rows = data
            .as_array()
            .context("Gitea-Projekt-API nicht verfügbar oder unvollständig")?;
        ensure!(rows.len() <= 100, "Gitea-Seite überschreitet das Limit");
        if self.stage == 1 {
            for row in rows {
                let id = row["id"].as_i64().context("Gitea-Spalten-ID fehlt")?;
                let title = row["title"].as_str().context("Gitea-Spaltentitel fehlt")?;
                ensure!(
                    id >= 0
                        && self.columns.len() < 32
                        && !self.columns.iter().any(|c| c.0 == id || c.2 == title),
                    "Doppelte oder zu viele Gitea-Spalten"
                );
                self.columns
                    .push((id, row["sorting"].as_i64().unwrap_or(0), title.into()));
            }
            if rows.is_empty() {
                self.columns.sort_by_key(|c| (c.1, c.0));
                board.columns = self.columns.iter().map(|c| c.2.clone()).collect();
                self.stage = 2;
                self.page = 1;
                return Ok(self.columns.is_empty());
            }
        } else {
            for row in rows {
                let id = row["id"].as_i64().context("Gitea-Issue-ID fehlt")?;
                ensure!(id > 0, "Ungültige Gitea-Issue-ID");
                board.cards.push(Card {
                    id: id.to_string(),
                    title: row["title"]
                        .as_str()
                        .context("Gitea-Issue-Titel fehlt")?
                        .into(),
                    description: row["body"].as_str().unwrap_or("").into(),
                    url: row["html_url"].as_str().unwrap_or("").into(),
                    project: board.title.clone(),
                    status: self.columns[self.column].2.clone(),
                    ..Default::default()
                });
            }
            if rows.is_empty() {
                self.column += 1;
                self.page = 1;
                return Ok(self.column == self.columns.len());
            }
        }
        // Continue until an empty page, including servers with a smaller page cap.
        self.page += 1;
        Ok(false)
    }
}
