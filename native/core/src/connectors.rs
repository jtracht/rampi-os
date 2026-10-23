//! Read-only provider adapters. HTTP and credential storage belong to existing services.
use crate::board::{Board, Card};
use anyhow::{Context, Result, bail, ensure};
use base64::{Engine, engine::general_purpose::STANDARD};
use serde_json::{Value, json};
use std::collections::{HashMap, HashSet};

pub struct Request {
    pub url: String,
    pub headers: Vec<(String, String)>,
    pub body: Option<Value>,
}
pub struct Connector {
    kind: String,
    source: String,
    token: String,
    cursor: Option<String>,
    seen: HashSet<String>,
    pages: usize,
    lists: Option<HashMap<String, String>>,
    board: Board,
    complete: bool,
    gitea: Option<crate::gitea::Project>,
}
fn identifier(value: &str, punctuation: &[u8], limit: usize) -> bool {
    !value.is_empty()
        && value.len() <= limit
        && value
            .bytes()
            .all(|c| c.is_ascii_alphanumeric() || punctuation.contains(&c))
}
fn uuid(value: &str) -> bool {
    (value.len() == 32 && value.bytes().all(|c| c.is_ascii_hexdigit()))
        || (value.split('-').map(str::len).collect::<Vec<_>>() == [8, 4, 4, 4, 12]
            && value.bytes().all(|c| c.is_ascii_hexdigit() || c == b'-'))
}
fn github_source(source: &str) -> Result<(&str, &str, i32)> {
    let parts: Vec<_> = source.split('/').collect();
    ensure!(
        parts.len() == 3
            && ["organization", "user"].contains(&parts[0])
            && identifier(parts[1], b"_.-", 100),
        "GitHub: organization/NAME/NUMMER oder user/NAME/NUMMER"
    );
    let number: i32 = parts[2].parse().context("Ungültige GitHub-Projektnummer")?;
    ensure!(number > 0, "Ungültige GitHub-Projektnummer");
    Ok((parts[0], parts[1], number))
}
fn jira_source(source: &str) -> Result<(&str, &str)> {
    let (site, project) = source
        .split_once('#')
        .context("Jira: https://SITE.atlassian.net#PROJEKT")?;
    ensure!(
        identifier(project, b"_", 128) && project.as_bytes()[0].is_ascii_alphabetic(),
        "Ungültiger Jira-Projektschlüssel"
    );
    let origin = site
        .strip_prefix("https://")
        .context("Jira benötigt HTTPS")?
        .trim_end_matches('/');
    let cloud = origin
        .strip_suffix(".atlassian.net")
        .is_some_and(|name| identifier(name, b"-", 100));
    let oauth = origin
        .strip_prefix("api.atlassian.com/ex/jira/")
        .is_some_and(uuid);
    ensure!(
        cloud || oauth,
        "Nur eine Jira-Cloud-Site oder offizielle OAuth-Cloud-ID verwenden"
    );
    Ok((site.trim_end_matches('/'), project))
}
pub fn encode(value: &str) -> String {
    value
        .bytes()
        .map(|c| {
            if c.is_ascii_alphanumeric() || b"-._~".contains(&c) {
                (c as char).to_string()
            } else {
                format!("%{c:02X}")
            }
        })
        .collect()
}
fn text(value: &Value, key: &str) -> String {
    value[key].as_str().unwrap_or("").to_string()
}
fn array<'a>(value: &'a Value, key: &str) -> Result<&'a Vec<Value>> {
    value[key]
        .as_array()
        .context("Unvollständige Anbieterantwort")
}
fn required(value: &Value, key: &str) -> Result<String> {
    let s = value[key]
        .as_str()
        .context("Unvollständige Anbieterantwort")?;
    ensure!(!s.is_empty(), "Unvollständige Anbieterantwort");
    Ok(s.into())
}
fn boolean(value: &Value, key: &str) -> Result<bool> {
    value[key]
        .as_bool()
        .context("Unvollständige Anbieter-Paginierung")
}
fn description(value: &Value, depth: usize) -> String {
    if depth > 32 {
        return String::new();
    }
    if let Some(s) = value.as_str() {
        return s.into();
    }
    if value["type"] == "text" {
        return text(value, "text");
    }
    value["content"]
        .as_array()
        .map(|rows| {
            rows.iter()
                .map(|v| description(v, depth + 1))
                .collect::<Vec<_>>()
                .join(
                    if ["doc", "bulletList", "orderedList"]
                        .contains(&value["type"].as_str().unwrap_or(""))
                    {
                        "\n"
                    } else {
                        ""
                    },
                )
        })
        .unwrap_or_default()
}
impl Connector {
    pub fn new(kind: &str, source: &str, token: String) -> Result<Self> {
        ensure!(
            !token.is_empty() && token.len() <= 16384 && !token.chars().any(char::is_control),
            "Gültiges Schlüsselbund-Profil auswählen"
        );
        match kind {
            "gitea" => {
                crate::gitea::Project::new(source)?;
            }
            "github" => {
                github_source(source)?;
            }
            "trello" => ensure!(identifier(source, b"", 128), "Ungültige Trello-Board-ID"),
            "asana" => ensure!(
                !source.is_empty()
                    && source.len() <= 128
                    && source.bytes().all(|c| c.is_ascii_digit()),
                "Asana benötigt eine numerische Projekt-ID"
            ),
            "jira" => {
                jira_source(source)?;
            }
            "notion" => ensure!(uuid(source), "Notion benötigt eine Data-Source-ID"),
            _ => bail!("Unbekannter Cloud-Connector"),
        }
        Ok(Self {
            kind: kind.into(),
            source: source.into(),
            token,
            cursor: None,
            seen: HashSet::new(),
            pages: 0,
            lists: None,
            board: Board {
                title: kind.into(),
                ..Default::default()
            },
            complete: false,
            gitea: if kind == "gitea" {
                Some(crate::gitea::Project::new(source)?)
            } else {
                None
            },
        })
    }
    pub fn request(&self) -> Result<Request> {
        ensure!(
            !self.complete && self.pages < 256,
            "Anbieter-Paginierung überschreitet das Limit"
        );
        let mut headers = vec![
            ("Accept".into(), "application/json".into()),
            ("Authorization".into(), format!("Bearer {}", self.token)),
        ];
        if let Some(project) = &self.gitea {
            headers[1].1 = format!("token {}", self.token);
            return Ok(Request {
                url: project.url(),
                headers,
                body: None,
            });
        }
        let (url, body) = match self.kind.as_str() {
            "github" => {
                let (root, owner, number) = github_source(&self.source)?;
                // Query only: the adapter never constructs a GraphQL mutation.
                let query = "query($owner:String!,$number:Int!,$after:String){ROOT(login:$owner){projectV2(number:$number){title items(first:100,after:$after){pageInfo{hasNextPage endCursor} nodes{id isArchived content{... on Issue{title body url repository{nameWithOwner}} ... on PullRequest{title body url repository{nameWithOwner}} ... on DraftIssue{title body}} fieldValues(first:100){pageInfo{hasNextPage} nodes{... on ProjectV2ItemFieldSingleSelectValue{name field{... on ProjectV2SingleSelectField{name}}}}}}}}}}".replace("ROOT", root);
                (
                    "https://api.github.com/graphql".into(),
                    Some(
                        json!({"query":query,"variables":{"owner":owner,"number":number,"after":self.cursor}}),
                    ),
                )
            }
            "asana" => {
                let mut url = format!(
                    "https://app.asana.com/api/1.0/projects/{}/tasks?limit=100&opt_fields=gid,name,notes,completed,memberships.project.gid,memberships.section.name,permalink_url",
                    self.source
                );
                if let Some(cursor) = &self.cursor {
                    url.push_str(&format!("&offset={}", encode(cursor)));
                }
                (url, None)
            }
            "trello" => {
                let credentials: Value = serde_json::from_str(&self.token)
                    .context("Trello benötigt API-Key und Token im Schlüsselbund")?;
                headers[1].1 = format!(
                    "OAuth oauth_consumer_key=\"{}\", oauth_token=\"{}\"",
                    encode(&required(&credentials, "key")?),
                    encode(&required(&credentials, "token")?)
                );
                let url = if self.lists.is_none() {
                    format!(
                        "https://api.trello.com/1/boards/{}/lists?filter=open",
                        self.source
                    )
                } else {
                    let mut url = format!(
                        "https://api.trello.com/1/boards/{}/cards?filter=open&limit=1000&fields=id,name,desc,idList,closed,url",
                        self.source
                    );
                    if let Some(cursor) = &self.cursor {
                        url.push_str(&format!("&before={}", encode(cursor)));
                    }
                    url
                };
                (url, None)
            }
            "jira" => {
                let (site, project) = jira_source(&self.source)?;
                if !site.starts_with("https://api.atlassian.com/") {
                    let credentials: Value = serde_json::from_str(&self.token)
                        .context("Jira Cloud benötigt E-Mail und API-Token im Schlüsselbund")?;
                    headers[1].1 = format!(
                        "Basic {}",
                        STANDARD.encode(format!(
                            "{}:{}",
                            required(&credentials, "email")?,
                            required(&credentials, "token")?
                        ))
                    );
                }
                let mut body = json!({"jql":format!("project = \"{project}\" ORDER BY key"),"maxResults":100,"fields":["summary","status","description","priority"]});
                if let Some(cursor) = &self.cursor {
                    body["nextPageToken"] = cursor.clone().into();
                }
                (format!("{site}/rest/api/3/search/jql"), Some(body))
            }
            "notion" => {
                headers.push(("Notion-Version".into(), "2026-03-11".into()));
                let mut body = json!({"page_size":100});
                if let Some(cursor) = &self.cursor {
                    body["start_cursor"] = cursor.clone().into();
                }
                (
                    format!(
                        "https://api.notion.com/v1/data_sources/{}/query",
                        self.source
                    ),
                    Some(body),
                )
            }
            _ => unreachable!(),
        };
        Ok(Request { url, headers, body })
    }
    pub fn accept(&mut self, data: &Value) -> Result<bool> {
        ensure!(!self.complete, "Abgeschlossener Connector");
        self.pages += 1;
        if let Some(project) = &mut self.gitea {
            self.complete = project.accept(data, &mut self.board)?;
            self.board.validate()?;
            return Ok(self.complete);
        }
        let next = match self.kind.as_str() {
            "github" => {
                ensure!(
                    data.get("errors").is_none(),
                    "GitHub-Abfrage fehlgeschlagen"
                );
                let (root, _, _) = github_source(&self.source)?;
                let project = &data["data"][root]["projectV2"];
                self.board.title = required(project, "title")?;
                for node in array(&project["items"], "nodes")? {
                    if node["isArchived"] == true || node["content"].is_null() {
                        continue;
                    }
                    ensure!(
                        !boolean(&node["fieldValues"]["pageInfo"], "hasNextPage")?,
                        "Zu viele GitHub-Kartenfelder für eine vollständige Darstellung"
                    );
                    let mut fields = HashMap::new();
                    for field in array(&node["fieldValues"], "nodes")? {
                        if let (Some(key), Some(value)) =
                            (field["field"]["name"].as_str(), field["name"].as_str())
                        {
                            fields.insert(key, value);
                        }
                    }
                    let c = &node["content"];
                    self.board.cards.push(Card {
                        id: required(node, "id")?,
                        title: required(c, "title")?,
                        description: text(c, "body"),
                        url: text(c, "url"),
                        status: fields.get("Status").unwrap_or(&"Offen").to_string(),
                        priority: fields.get("Priority").unwrap_or(&"normal").to_string(),
                        project: text(&c["repository"], "nameWithOwner"),
                    });
                }
                if boolean(&project["items"]["pageInfo"], "hasNextPage")? {
                    Some(required(&project["items"]["pageInfo"], "endCursor")?)
                } else {
                    None
                }
            }
            "asana" => {
                for c in array(data, "data")? {
                    let memberships = array(c, "memberships")?;
                    let status = if c["completed"] == true {
                        "Erledigt".into()
                    } else {
                        memberships
                            .iter()
                            .find(|m| m["project"]["gid"].as_str() == Some(&self.source))
                            .map(|m| text(&m["section"], "name"))
                            .filter(|s| !s.is_empty())
                            .unwrap_or_else(|| "Offen".into())
                    };
                    self.board.cards.push(Card {
                        id: required(c, "gid")?,
                        title: required(c, "name")?,
                        description: text(c, "notes"),
                        url: text(c, "permalink_url"),
                        project: self.source.clone(),
                        status,
                        ..Default::default()
                    });
                }
                if data
                    .get("next_page")
                    .context("Asana-Paginierung fehlt")?
                    .is_null()
                {
                    None
                } else {
                    Some(required(&data["next_page"], "offset")?)
                }
            }
            "trello" => {
                let rows = data.as_array().context("Unvollständige Trello-Antwort")?;
                if self.lists.is_none() {
                    let mut names = HashMap::new();
                    for list in rows {
                        let name = required(list, "name")?;
                        self.board.columns.push(name.clone());
                        names.insert(required(list, "id")?, name);
                    }
                    self.lists = Some(names);
                    self.board.validate()?;
                    return Ok(false);
                }
                for c in rows {
                    if c["closed"] == true {
                        continue;
                    }
                    self.board.cards.push(Card {
                        id: required(c, "id")?,
                        title: required(c, "name")?,
                        description: text(c, "desc"),
                        url: text(c, "url"),
                        status: self
                            .lists
                            .as_ref()
                            .unwrap()
                            .get(&text(c, "idList"))
                            .cloned()
                            .unwrap_or_else(|| "Offen".into()),
                        ..Default::default()
                    });
                }
                if rows.len() == 1000 {
                    Some(required(rows.last().unwrap(), "id")?)
                } else {
                    None
                }
            }
            "jira" => {
                let (_, project) = jira_source(&self.source)?;
                self.board.title = project.into();
                for c in array(data, "issues")? {
                    let f = &c["fields"];
                    self.board.cards.push(Card {
                        id: required(c, "key")?,
                        title: required(f, "summary")?,
                        description: description(&f["description"], 0),
                        status: required(&f["status"], "name")?,
                        priority: text(&f["priority"], "name"),
                        project: project.into(),
                        ..Default::default()
                    });
                }
                ensure!(
                    data["isLast"] != false
                        || data["nextPageToken"]
                            .as_str()
                            .is_some_and(|s| !s.is_empty()),
                    "Jira-Paginierung fehlt"
                );
                data["nextPageToken"]
                    .as_str()
                    .filter(|s| !s.is_empty())
                    .map(String::from)
            }
            "notion" => {
                for c in array(data, "results")? {
                    if c["object"] != "page" || c["in_trash"] == true || c["is_archived"] == true {
                        continue;
                    }
                    let props = c["properties"]
                        .as_object()
                        .context("Notion-Eigenschaften fehlen")?;
                    let title = props
                        .values()
                        .find(|v| v["type"] == "title")
                        .map(|v| {
                            array(v, "title").map(|parts| {
                                parts
                                    .iter()
                                    .map(|t| text(t, "plain_text"))
                                    .collect::<String>()
                            })
                        })
                        .transpose()?
                        .unwrap_or_else(|| "Ohne Titel".into());
                    let status = props
                        .values()
                        .find(|v| v["type"] == "status")
                        .map(|v| text(&v["status"], "name"))
                        .filter(|s| !s.is_empty())
                        .unwrap_or_else(|| "Offen".into());
                    self.board.cards.push(Card {
                        id: required(c, "id")?,
                        title,
                        status,
                        url: text(c, "url"),
                        ..Default::default()
                    });
                }
                if boolean(data, "has_more")? {
                    Some(required(data, "next_cursor")?)
                } else {
                    None
                }
            }
            _ => unreachable!(),
        };
        self.board.validate()?;
        if let Some(cursor) = &next {
            ensure!(
                cursor.len() <= 8192 && self.seen.insert(cursor.clone()),
                "Ungültige oder wiederholte Anbieter-Paginierung"
            );
        }
        self.cursor = next;
        self.complete = self.cursor.is_none();
        Ok(self.complete)
    }
    pub fn finish(self) -> Result<Board> {
        ensure!(self.complete, "Unvollständiges Board wird nicht übernommen");
        let mut ids = HashSet::new();
        ensure!(
            self.board.cards.iter().all(|c| ids.insert(&c.id)),
            "Doppelte Aufgaben in Anbieter-Paginierung"
        );
        Ok(self.board)
    }
}
