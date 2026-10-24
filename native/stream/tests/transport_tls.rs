//! Actual loopback TLS sockets; no Sunshine/protocol/GTK acceptance claim.
#![cfg(target_os = "linux")]
use moonlight_common::{
    AppId,
    http::{
        ClientInfo,
        box_art::{AppBoxArtEndpoint, AppBoxArtRequest},
        client::blocking_client::RequestClient,
    },
};
use openssl::{
    asn1::Asn1Time,
    hash::MessageDigest,
    pkey::{PKey, Private},
    rsa::Rsa,
    ssl::{SslAcceptor, SslMethod, SslVerifyMode},
    x509::{X509, X509NameBuilder},
};
use rampi_stream::transport::CurlClient;
use std::{
    io::{Read, Write},
    net::TcpListener,
    thread,
    time::Duration,
};

fn certificate() -> (X509, PKey<Private>) {
    let key = PKey::from_rsa(Rsa::generate(2048).unwrap()).unwrap();
    let mut name = X509NameBuilder::new().unwrap();
    name.append_entry_by_text("CN", "disposable.invalid")
        .unwrap();
    let name = name.build();
    let mut cert = X509::builder().unwrap();
    cert.set_version(2).unwrap();
    cert.set_subject_name(&name).unwrap();
    cert.set_issuer_name(&name).unwrap();
    cert.set_pubkey(&key).unwrap();
    cert.set_not_before(Asn1Time::days_from_now(0).unwrap().as_ref())
        .unwrap();
    cert.set_not_after(Asn1Time::days_from_now(1).unwrap().as_ref())
        .unwrap();
    cert.sign(&key, MessageDigest::sha256()).unwrap();
    (cert.build(), key)
}
fn server(
    cert: &X509,
    key: &PKey<Private>,
    client: &X509,
    response: &'static [u8],
) -> (String, thread::JoinHandle<usize>) {
    let listener = TcpListener::bind("127.0.0.1:0").unwrap();
    let address = listener.local_addr().unwrap().to_string();
    let mut tls = SslAcceptor::mozilla_intermediate(SslMethod::tls_server()).unwrap();
    tls.set_certificate(cert).unwrap();
    tls.set_private_key(key).unwrap();
    tls.cert_store_mut().add_cert(client.clone()).unwrap();
    tls.set_verify(SslVerifyMode::PEER | SslVerifyMode::FAIL_IF_NO_PEER_CERT);
    let tls = tls.build();
    let thread = thread::spawn(move || {
        let (socket, _) = listener.accept().unwrap();
        socket
            .set_read_timeout(Some(Duration::from_secs(5)))
            .unwrap();
        socket
            .set_write_timeout(Some(Duration::from_secs(5)))
            .unwrap();
        let Ok(mut stream) = tls.accept(socket) else {
            return 0;
        };
        let mut bytes = [0; 4096];
        let Ok(count) = stream.read(&mut bytes) else {
            return 0;
        };
        if count == 0 {
            return 0;
        }
        assert!(bytes[..count].starts_with(b"GET /appasset?"));
        let _ = stream.write_all(response);
        count
    });
    (address, thread)
}
fn client(cert: &X509, key: &PKey<Private>, server: &X509) -> CurlClient {
    CurlClient::with_certificates(
        &pem::parse(key.private_key_to_pem_pkcs8().unwrap()).unwrap(),
        &pem::parse(cert.to_pem().unwrap()).unwrap(),
        &pem::parse(server.to_pem().unwrap()).unwrap(),
    )
    .unwrap()
}
fn request(client: &CurlClient, address: &str) -> Result<Vec<u8>, moonlight_common::error::Error> {
    client.send_https_with_bytes::<AppBoxArtEndpoint>(
        ClientInfo::default(),
        address,
        &AppBoxArtRequest {
            app_id: AppId(1),
            asset_type: 2,
            asset_idx: 0,
        },
    )
}

#[test]
fn actual_mutual_tls_requires_the_paired_server_key() {
    let (peer, peer_key) = certificate();
    let (local, local_key) = certificate();
    let (other, _) = certificate();
    let (address, good) = server(
        &peer,
        &peer_key,
        &local,
        b"HTTP/1.1 200 OK\r\nContent-Length: 5\r\nConnection: close\r\n\r\nrampi",
    );
    assert_eq!(
        request(&client(&local, &local_key, &peer), &address).unwrap(),
        b"rampi"
    );
    assert!(good.join().unwrap() > 0);
    let (address, rejected) = server(
        &peer,
        &peer_key,
        &local,
        b"HTTP/1.1 200 OK\r\nContent-Length: 5\r\n\r\nrampi",
    );
    assert!(request(&client(&local, &local_key, &other), &address).is_err());
    assert_eq!(
        rejected.join().unwrap(),
        0,
        "A wrong peer received an application request"
    );
    // A client without a confirmed peer must reject HTTPS before network I/O.
    assert!(request(&CurlClient::with_defaults().unwrap(), "127.0.0.1:1").is_err());
}

#[test]
fn actual_redirect_and_oversized_response_fail_closed() {
    let (peer, peer_key) = certificate();
    let (local, local_key) = certificate();
    let client = client(&local, &local_key, &peer);
    for response in [
        b"HTTP/1.1 302 Found\r\nLocation: https://127.0.0.1:1/stolen\r\nContent-Length: 0\r\n\r\n"
            .as_slice(),
        b"HTTP/1.1 200 OK\r\nContent-Length: 4194305\r\n\r\n".as_slice(),
    ] {
        let (address, server) = server(&peer, &peer_key, &local, response);
        assert!(request(&client, &address).is_err());
        assert!(server.join().unwrap() > 0);
    }
}

#[test]
fn secure_endpoint_cannot_be_sent_as_cleartext() {
    use moonlight_common::http::app_list::{AppListEndpoint, AppListRequest};
    let client = CurlClient::with_defaults().unwrap();
    assert!(
        client
            .send_http::<AppListEndpoint>(ClientInfo::default(), "127.0.0.1:1", &AppListRequest {})
            .is_err()
    );
}
