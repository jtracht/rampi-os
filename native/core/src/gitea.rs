//! Official repository project API: metadata, ordered columns, paged issues.
use crate::board::{Board, Card};
use anyhow::{Context, Result, ensure};
use serde_json::Value;

pub struct Project {
    endpoint: String,
    project_id: i64,
    project_type: &'static str,
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
            if let Some((site, scope)) = repository.rsplit_once("/api/v1/") {
                expanded = format!("{scope}/{id}");
                (site, expanded.as_str())
            } else if let Some((site, organization)) = repository.rsplit_once("/orgs/") {
                expanded = format!("orgs/{organization}/{id}");
                (site, expanded.as_str())
            } else {
                let (owner_path, repo) = repository
                    .rsplit_once('/')
                    .context("Gitea-Repository fehlt")?;
                let (site, owner) = owner_path
                    .rsplit_once('/')
                    .context("Gitea-Eigentümer fehlt")?;
                expanded = format!("repos/{owner}/{repo}/{id}");
                (site, expanded.as_str())
            }
        };
        crate::config::validate_https(site)?;
        ensure!(
            site[8..].split_once('/').is_none_or(|(_, path)| {
                let path = path.trim_end_matches('/');
                path.is_empty() || path.split('/').all(segment)
            }),
            "Ungültiger Gitea-Installationspfad"
        );
        let site_url = url::Url::parse(site).context("Ungültiger Gitea-Server")?;
        ensure!(
            site_url.scheme() == "https"
                && site_url.host_str().is_some()
                && site_url.username().is_empty()
                && site_url.password().is_none()
                && site_url.query().is_none()
                && site_url.fragment().is_none()
                && site_url
                    .port_or_known_default()
                    .is_some_and(|port| port > 0)
                && site_url
                    .path_segments()
                    .is_some_and(|parts| parts.filter(|p| !p.is_empty()).all(segment)),
            "Ungültiger Gitea-Server oder Installationspfad"
        );
        let site = site_url.as_str().trim_end_matches('/');
        let path: Vec<_> = path.split('/').collect();
        let (scope, id, project_type) = match path.as_slice() {
            ["repos", owner, repo, id] if segment(owner) && segment(repo) => {
                (format!("repos/{owner}/{repo}"), *id, "repository")
            }
            ["orgs", organization, id] if segment(organization) => {
                (format!("orgs/{organization}"), *id, "organization")
            }
            ["user", id] => ("user".into(), *id, "individual"),
            _ => anyhow::bail!(
                "Gitea: repos/EIGENTÜMER/REPOSITORY/ID, orgs/ORGANISATION/ID oder user/ID angeben"
            ),
        };
        let project_id: i64 = id.parse().context("Ungültige Gitea-Projekt-ID")?;
        ensure!(project_id > 0, "Ungültige Gitea-Projekt-ID");
        Ok(Self {
            endpoint: format!("{site}/api/v1/{scope}/projects/{project_id}"),
            project_id,
            project_type,
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
            if let Some(kind) = data["type"].as_str() {
                ensure!(
                    kind == self.project_type,
                    "Gitea-Projekt gehört zu einem anderen Projektbereich"
                );
            }
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
