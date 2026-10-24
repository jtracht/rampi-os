//! Moonlight's RequestClient using existing libcurl and the authenticated peer key.
//! No TLS bypass is permitted without an explicit paired-server SPKI pin.
use base64::{Engine, engine::general_purpose::STANDARD};
use curl::easy::Easy;
use moonlight_common::{
    error::Error,
    http::{ClientInfo, Endpoint, Request, TextResponse, client::blocking_client::RequestClient},
};
use openssl::x509::X509;
use pem::Pem;
use std::{str::FromStr, sync::Arc, time::Duration};

#[derive(Clone)]
struct Identity {
    key: Vec<u8>,
    certificate: Vec<u8>,
    pin: String,
}
// Deliberately no Debug implementation: key material and request URLs are private.
#[derive(Clone)]
pub struct CurlClient {
    identity: Option<Arc<Identity>>,
    timeout: Duration,
}
fn other(error: impl std::error::Error + Send + Sync + 'static) -> Error {
    Error::Other(Box::new(error))
}
impl CurlClient {
    fn request<E: Endpoint>(
        &self,
        https: bool,
        client_info: ClientInfo,
        hostport: &str,
        request: &E::Request,
    ) -> Result<Vec<u8>, Error> {
        if !https && E::https_required() {
            return Err(Error::Unauthenticated);
        }
        let mut url = url::Url::parse(&format!(
            "{}://{hostport}{}",
            if https { "https" } else { "http" },
            E::path()
        ))
        .map_err(other)?;
        if !url.username().is_empty()
            || url.password().is_some()
            || url.fragment().is_some()
            || url.query().is_some()
            || url.path() != E::path()
        {
            return Err(Error::Unauthenticated);
        }
        // Endpoint types provide the existing protocol query. Rampi doesn't
        // implement pairing, launch/resume, cryptography or packet formats.
        let mut query = String::new();
        client_info.append_query_params(&mut query).map_err(other)?;
        request.append_query_params(&mut query).map_err(other)?;
        url.set_query(Some(&query));
        let mut handle = Easy::new();
        handle.url(url.as_str()).map_err(other)?;
        handle
            .connect_timeout(Duration::from_secs(8))
            .map_err(other)?;
        handle.timeout(self.timeout).map_err(other)?;
        handle.follow_location(false).map_err(other)?;
        handle.fail_on_error(true).map_err(other)?;
        handle.max_filesize(4 * 1024 * 1024).map_err(other)?;
        handle.verbose(false).map_err(other)?;
        if https {
            let identity = self.identity.as_ref().ok_or(Error::Unauthenticated)?;
            handle.ssl_cert_blob(&identity.certificate).map_err(other)?;
            handle.ssl_key_blob(&identity.key).map_err(other)?;
            // GameStream certificates are self-signed and don't identify the
            // DNS name. libcurl instead requires the public key authenticated
            // by Moonlight's PIN challenge. A different peer key is rejected.
            handle.pinned_public_key(&identity.pin).map_err(other)?;
            handle.ssl_verify_peer(false).map_err(other)?;
            handle.ssl_verify_host(false).map_err(other)?;
        }
        let mut bytes = Vec::new();
        {
            let mut transfer = handle.transfer();
            transfer
                .write_function(|chunk| {
                    if bytes.len().saturating_add(chunk.len()) > 4 * 1024 * 1024 {
                        return Ok(0);
                    }
                    bytes.extend_from_slice(chunk);
                    Ok(chunk.len())
                })
                .map_err(other)?;
            // Errors deliberately omit the URL, response, certificate and key.
            transfer.perform().map_err(|_| Error::ConnectionFailed)?;
        }
        let status = handle.response_code().map_err(other)?;
        if !(200..300).contains(&status) {
            return Err(Error::StatusCode {
                code: status as i32,
                reason: String::new(),
            });
        }
        Ok(bytes)
    }
}
impl RequestClient for CurlClient {
    fn with_defaults() -> Result<Self, Error> {
        Ok(Self {
            identity: None,
            timeout: Duration::from_secs(20),
        })
    }
    fn with_defaults_long_timeout() -> Result<Self, Error> {
        Ok(Self {
            identity: None,
            timeout: Duration::from_secs(90),
        })
    }
    fn with_certificates(key: &Pem, certificate: &Pem, server: &Pem) -> Result<Self, Error> {
        let peer = X509::from_der(server.contents())?;
        let public_key = peer.public_key()?.public_key_to_der()?;
        let pin = format!(
            "sha256//{}",
            STANDARD.encode(openssl::sha::sha256(&public_key))
        );
        Ok(Self {
            identity: Some(Arc::new(Identity {
                key: key.to_string().into_bytes(),
                certificate: certificate.to_string().into_bytes(),
                pin,
            })),
            timeout: Duration::from_secs(20),
        })
    }
    fn send_http<E>(
        &self,
        info: ClientInfo,
        hostport: &str,
        request: &E::Request,
    ) -> Result<E::Response, Error>
    where
        E: Endpoint,
        E::Response: TextResponse,
    {
        let bytes = self.request::<E>(false, info, hostport, request)?;
        E::Response::from_str(std::str::from_utf8(&bytes).map_err(other)?)
    }
    fn send_https<E>(
        &self,
        info: ClientInfo,
        hostport: &str,
        request: &E::Request,
    ) -> Result<E::Response, Error>
    where
        E: Endpoint,
        E::Response: TextResponse,
    {
        let bytes = self.request::<E>(true, info, hostport, request)?;
        E::Response::from_str(std::str::from_utf8(&bytes).map_err(other)?)
    }
    fn send_https_with_bytes<E>(
        &self,
        info: ClientInfo,
        hostport: &str,
        request: &E::Request,
    ) -> Result<E::Response, Error>
    where
        E: Endpoint<Response = Vec<u8>>,
    {
        self.request::<E>(true, info, hostport, request)
    }
}
