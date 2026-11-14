//! Offline fixture producer using published 0.1.0 crates, matching sc-decidr 0.1.0.
//! Run `cargo run --manifest-path tests/sc-judge-jev/fixtures/native-keyring-redaction/Cargo.toml`
//! to reproduce detail.json. KeyringSource and transport are controlled: no OS
//! keychain, credentials, network, sleeps or elapsed-time assertions.
//! This verifies native Rust library behavior, not the Python wheel boundary.

use sc_agent_http::testing::{ManualClock, ScriptedTransport};
use sc_agent_http::{
    Attempts, Endpoint, HttpClient, HttpError, HttpRequest, LogContext, Method, NetworkKind,
    ResendPolicy, SecretHeader, Start,
};
use sc_agent_log::testing::MemoryLog;
use sc_agent_secrets::{EnvSource, KeySource, KeySources, KeyringSource, SecretsError, resolve};
use sc_agent_types::{ErrorDetail, ErrorId, Provider};
use std::sync::Arc;

const KEY: &str = "sk-controlled-keyring-redaction-sentinel-77";
struct NoEnv;
impl EnvSource for NoEnv {
    fn var(&self, _: &str) -> Option<String> {
        None
    }
}
struct ControlledKeyring;
impl KeyringSource for ControlledKeyring {
    fn password(&self, service: &str, account: &str) -> Result<Option<String>, SecretsError> {
        assert_eq!(service, sc_agent_secrets::TYPESAFE_API_KEY);
        assert!(!account.is_empty());
        Ok(Some(KEY.to_owned()))
    }
}
fn main() -> Result<(), Box<dyn std::error::Error>> {
    let sources = KeySources {
        env: &NoEnv,
        repo_root: None,
        keyring: &ControlledKeyring,
    };
    let resolved = resolve(Provider::TypeSafe, &sources)?;
    assert_eq!(resolved.source, KeySource::Keyring);
    let request = HttpRequest::new(
        Method::Post,
        Endpoint::parse("https://api.example.test/v1")?,
        b"{}".as_slice(),
    )
    .with_secret(SecretHeader::bearer(resolved.key))?;
    let echo = HttpError::network(
        NetworkKind::Other,
        1,
        format!("proxy echoed Authorization={KEY}"),
    )
    .with_cause(ErrorDetail::new(
        "io.Other",
        format!("outer {KEY}"),
        Some(ErrorDetail::new(
            "foreign.source",
            format!("inner {KEY}"),
            None,
        )),
    ));
    let transport = ScriptedTransport::new(vec![Err(echo)]);
    let memory = MemoryLog::new()?;
    let client = HttpClient::new(
        Arc::new(transport.clone()),
        ResendPolicy::default(),
        memory.general(),
    );
    let clock = ManualClock::new().clock();
    let Start::Go(permit) = client
        .may_start(&request, Attempts::new(), clock.now())
        .map_err(|reason| format!("unexpected busy: {reason:?}"))?
    else {
        return Err("fresh request unexpectedly held".into());
    };
    let error = match client.send_once(&request, permit, LogContext::NONE, &clock) {
        Err(error) => error,
        Ok(_) => return Err("scripted error unexpectedly succeeded".into()),
    };
    assert_eq!(transport.sends(), 1);
    let detail = error.detail();
    let text = serde_json::to_string(&detail)?;
    assert!(!text.contains(KEY));
    assert!(text.contains("[redacted]"));
    let records = memory.records()?;
    assert!(!format!("{records:?}").contains(KEY));
    println!(
        "{}",
        serde_json::to_string_pretty(
            &serde_json::json!({"credential_source":"keyring", "transport":"scripted, no network", "detail":detail})
        )?
    );
    Ok(())
}
