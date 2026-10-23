use crate::connectors::Connector;
use serde_json::json;

#[test]
fn provider_origins_cannot_be_replaced_by_sources_or_pagination() {
    for (kind, source) in [
        ("github", "organization/owner/-1"),
        ("github", "organization/owner/999999999999"),
        ("trello", "board?token=wrong"),
        ("asana", "42&host=other"),
        ("jira", "https://fixture.atlassian.net.evil.invalid#RAMPI"),
        ("jira", "https://user@fixture.atlassian.net#RAMPI"),
        ("jira", "https://fixture.atlassian.net/path#RAMPI"),
        ("jira", "https://api.atlassian.com/ex/jira/not-a-uuid#RAMPI"),
        ("jira", "https://fixture.atlassian.net#P\" or 1=1"),
        ("notion", "not-an-id"),
    ] {
        assert!(
            Connector::new(kind, source, "fixture".into()).is_err(),
            "{kind}: {source}"
        );
    }
    let mut asana = Connector::new("asana", "42", "fixture".into()).unwrap();
    assert!(!asana.accept(&json!({"data":[],"next_page":{"offset":"x+/=","uri":"https://other.invalid/steal"}})).unwrap());
    let next = asana.request().unwrap();
    assert!(next.url.starts_with("https://app.asana.com/"));
    assert!(next.url.ends_with("offset=x%2B%2F%3D"));
    assert!(!next.url.contains("fixture"));
}
#[test]
fn missing_pagination_does_not_publish_a_truncated_board() {
    for (kind, source, response) in [
        (
            "github",
            "organization/owner/1",
            json!({"data":{"organization":{"projectV2":{"title":"Board","items":{"nodes":[],"pageInfo":{}}}}}}),
        ),
        ("asana", "42", json!({"data":[]})),
        (
            "notion",
            "0123456789abcdef0123456789abcdef", // pragma: allowlist secret - synthetic Notion data source ID
            json!({"results":[]}),
        ),
        (
            "jira",
            "https://fixture.atlassian.net#P",
            json!({"issues":[],"isLast":false}),
        ),
    ] {
        let mut connector = Connector::new(kind, source, "fixture".into()).unwrap();
        assert!(connector.accept(&response).is_err());
        assert!(connector.finish().is_err());
    }
}
#[test]
fn repeated_cursors_and_duplicate_cards_are_not_silently_accepted() {
    let mut connector = Connector::new(
        "notion",
        "0123456789abcdef0123456789abcdef", // pragma: allowlist secret - synthetic Notion data source ID
        "fixture".into(),
    )
    .unwrap();
    let page = json!({"results":[],"has_more":true,"next_cursor":"repeated"});
    assert!(!connector.accept(&page).unwrap());
    assert!(connector.accept(&page).is_err());
    assert!(connector.finish().is_err());
    let mut connector =
        Connector::new("jira", "https://fixture.atlassian.net#P", "fixture".into()).unwrap();
    let card = json!({"key":"P-1","fields":{"summary":"Task","status":{"name":"Review"}}});
    assert!(
        connector
            .accept(&json!({"issues":[card.clone(),card],"isLast":true}))
            .unwrap()
    );
    assert!(connector.finish().is_err());
}
#[test]
fn private_headers_and_read_queries_are_separate_from_urls() {
    let github = Connector::new("github", "user/owner/1", "synthetic-token".into())
        .unwrap()
        .request()
        .unwrap();
    assert_eq!(github.url, "https://api.github.com/graphql");
    assert_eq!(github.headers[1].1, "Bearer synthetic-token");
    let body = github.body.unwrap();
    assert!(body["query"].as_str().unwrap().starts_with("query("));
    assert!(!body["query"].as_str().unwrap().contains("mutation"));
    assert_eq!(body["variables"]["owner"], "owner");
    let notion = Connector::new(
        "notion",
        "0123456789abcdef0123456789abcdef", // pragma: allowlist secret - synthetic Notion data source ID
        "synthetic-token".into(),
    )
    .unwrap()
    .request()
    .unwrap();
    assert!(
        notion
            .headers
            .contains(&("Notion-Version".into(), "2026-03-11".into()))
    );
}

#[test]
fn gitea_preserves_project_columns_and_server_page_limits() {
    for source in [
        "http://gitea.test#repos/a/b/1",
        "https://user@gitea.test#repos/a/b/1",
        "https://gitea.test/../other#repos/a/b/1",
        "https://gitea.test?query#repos/a/b/1",
        "https://gitea.test#repos/a/../1",
        "https://gitea.test#repos/a/b/-1",
    ] {
        assert!(Connector::new("gitea", source, "fixture".into()).is_err());
    }
    let copied = Connector::new(
        "gitea",
        "https://gitea.test:8443/git/owner/repo/projects/7/",
        "fixture".into(),
    )
    .unwrap();
    assert_eq!(
        copied.request().unwrap().url,
        "https://gitea.test:8443/git/api/v1/repos/owner/repo/projects/7"
    );
    for source in [
        "https://gitea.test/owner/repo/projects/7?other=1",
        "https://user@gitea.test/owner/repo/projects/7",
        "https://gitea.test/../owner/repo/projects/7",
    ] {
        assert!(Connector::new("gitea", source, "fixture".into()).is_err());
    }
    let mut c = Connector::new(
        "gitea",
        "https://gitea.test:8443/git#repos/owner/repo/7",
        "fixture".into(),
    )
    .unwrap();
    assert_eq!(c.request().unwrap().headers[1].1, "token fixture");
    assert!(!c.accept(&json!({"id":7,"title":"Work"})).unwrap());
    assert!(
        !c.accept(
            &json!([{"id":2,"sorting":2,"title":"Empty"},{"id":1,"sorting":1,"title":"Doing"}])
        )
        .unwrap()
    );
    assert!(
        c.request()
            .unwrap()
            .url
            .ends_with("columns?limit=100&page=2")
    );
    assert!(!c.accept(&json!([])).unwrap());
    assert!(
        c.request()
            .unwrap()
            .url
            .starts_with("https://gitea.test:8443/git/api/v1/")
    );
    assert!(
        c.request()
            .unwrap()
            .url
            .ends_with("columns/1/issues?limit=100&page=1")
    );
    assert!(
        !c.accept(&json!([{"id":99,"title":"Task","body":"Body"}]))
            .unwrap()
    );
    assert!(c.request().unwrap().url.ends_with("page=2"));
    assert!(!c.accept(&json!([])).unwrap());
    assert!(c.accept(&json!([])).unwrap());
    let b = c.finish().unwrap();
    assert_eq!(b.columns, ["Doing", "Empty"]);
    assert_eq!(b.cards[0].status, "Doing");
}
