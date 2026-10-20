use anyhow::{Result, ensure};
use serde::{Deserialize, Serialize};
use std::{collections::BTreeSet, fs, path::Path};

#[derive(Clone, Debug, Default, Serialize, Deserialize)]
#[serde(default)]
pub struct Card {
    pub title: String,
    pub description: String,
    pub project: String,
    pub priority: String,
    pub status: String,
}
#[derive(Clone, Debug, Default, Deserialize)]
#[serde(default)]
pub struct Board {
    pub title: String,
    pub cards: Vec<Card>,
}
impl Board {
    pub fn load(path: &Path) -> Result<Self> {
        ensure!(
            fs::metadata(path)?.len() <= 5_242_880,
            "Kanban-Datei ist zu groß"
        );
        let board: Self = serde_json::from_slice(&fs::read(path)?)?;
        ensure!(board.cards.len() <= 10_000, "Zu viele Karten");
        Ok(board)
    }
    pub fn columns(&self, preferred: &[String]) -> Vec<String> {
        let mut columns = preferred.to_vec();
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
