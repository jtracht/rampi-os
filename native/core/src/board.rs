use anyhow::{Result, ensure};
use serde::{Deserialize, Serialize};
use std::{collections::BTreeSet, fs::File, io::Read, path::Path};

#[derive(Clone, Debug, Default, Serialize, Deserialize)]
#[serde(default)]
pub struct Card {
    pub id: String,
    pub url: String,
    pub title: String,
    pub description: String,
    pub project: String,
    pub priority: String,
    pub status: String,
}
#[derive(Clone, Debug, Default, Serialize, Deserialize)]
#[serde(default)]
pub struct Board {
    pub title: String,
    pub cards: Vec<Card>,
    pub columns: Vec<String>,
}
impl Board {
    pub fn load(path: &Path) -> Result<Self> {
        const MAX_BYTES: u64 = 5_242_880;
        let file = File::open(path)?;
        ensure!(
            file.metadata()?.len() <= MAX_BYTES,
            "Kanban-Datei ist zu groß"
        );
        let mut data = Vec::new();
        file.take(MAX_BYTES + 1).read_to_end(&mut data)?;
        ensure!(data.len() as u64 <= MAX_BYTES, "Kanban-Datei ist zu groß");
        let board: Self = serde_json::from_slice(&data)?;
        board.validate()?;
        Ok(board)
    }
    pub fn validate(&self) -> Result<()> {
        ensure!(self.cards.len() <= 10_000, "Zu viele Karten");
        ensure!(
            self.columns.len() <= 32 && self.title.len() <= 8192,
            "Ungültige Boarddaten"
        );
        for name in &self.columns {
            ensure!(
                !name.trim().is_empty()
                    && name.chars().count() <= 80
                    && !name.chars().any(char::is_control),
                "Ungültige Quellspalte"
            );
        }
        for card in &self.cards {
            ensure!(
                card.title.len() <= 8192
                    && card.description.len() <= 100_000
                    && card.status.len() <= 1024
                    && card.project.len() <= 1024
                    && card.priority.len() <= 1024
                    && card.id.len() <= 1024
                    && card.url.len() <= 8192,
                "Karte überschreitet das Größenlimit"
            );
        }
        ensure!(
            serde_json::to_vec(self)?.len() <= 5_242_880,
            "Kanban-Daten sind zu groß"
        );
        Ok(())
    }
    pub fn columns(&self, preferred: &[String]) -> Vec<String> {
        let mut columns = preferred.to_vec();
        for name in &self.columns {
            if !columns.contains(name) {
                columns.push(name.clone());
            }
        }
        for c in self
            .cards
            .iter()
            .map(|c| &c.status)
            .collect::<BTreeSet<_>>()
        {
            if !columns.contains(c) {
                columns.push(c.clone());
            }
        }
        if columns.is_empty() {
            columns = ["Offen", "In Arbeit", "Review", "Erledigt"]
                .map(String::from)
                .to_vec();
        }
        columns
    }
    pub fn filtered(&self, query: &str, project: &str, priority: &str, status: &str) -> Vec<&Card> {
        let q = query.to_lowercase();
        self.cards
            .iter()
            .filter(|c| {
                (project.is_empty() || project == c.project)
                    && (priority.is_empty() || priority == c.priority)
                    && (status.is_empty() || status == c.status)
                    && (q.is_empty()
                        || [&c.title, &c.description, &c.project, &c.priority]
                            .iter()
                            .any(|s| s.to_lowercase().contains(&q)))
            })
            .collect()
    }
}
#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn filters_are_combined_without_source_mutation() {
        let board: Board = serde_json::from_str(r#"{"cards":[{"title":"VPN","project":"Infra","priority":"high","status":"Review"},{"title":"Layout","project":"UI","status":"Offen"}]}"#).unwrap();
        assert_eq!(board.filtered("vpn", "Infra", "high", "Review").len(), 1);
        assert_eq!(board.filtered("vpn", "UI", "", "").len(), 0);
        assert_eq!(board.cards.len(), 2);
        assert_eq!(board.columns(&["Review".into()]), vec!["Review", "Offen"]);
    }
}
