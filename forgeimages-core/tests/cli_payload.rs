//! CLI payload transport.
//!
//! The bridge hands the CLI a base64 raster master. A diffusion master is
//! megabytes, and Linux refuses any single argument over 128 KiB (`E2BIG`), so
//! the bridge sends the payload on stdin with `--payload -`. These tests run the
//! real binary with a master far over that limit.

use std::io::Write;
use std::process::{Command, Stdio};

use base64::Engine as _;

/// A noise PNG: incompressible, so its base64 is several MiB like a real master.
fn noise_png_base64(w: u32, h: u32) -> String {
    let mut state: u32 = 0x9e37_79b9;
    let img = image::RgbImage::from_fn(w, h, |_, _| {
        let mut px = [0u8; 3];
        for c in &mut px {
            state ^= state << 13;
            state ^= state >> 17;
            state ^= state << 5;
            *c = state as u8;
        }
        image::Rgb(px)
    });
    let mut out = std::io::Cursor::new(Vec::new());
    img.write_to(&mut out, image::ImageFormat::Png)
        .expect("encode noise png");
    base64::engine::general_purpose::STANDARD.encode(out.into_inner())
}

fn run_cli(args: &[&str], stdin: &str) -> (i32, serde_json::Value) {
    let templates = concat!(env!("CARGO_MANIFEST_DIR"), "/templates");
    let mut child = Command::new(env!("CARGO_BIN_EXE_forgeimages-cli"))
        .args(["--templates-dir", templates])
        .args(args)
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .spawn()
        .expect("spawn forgeimages-cli");
    child
        .stdin
        .take()
        .unwrap()
        .write_all(stdin.as_bytes())
        .unwrap();
    let out = child.wait_with_output().unwrap();
    let body = serde_json::from_slice(&out.stdout).expect("CLI prints JSON");
    (out.status.code().unwrap_or(-1), body)
}

#[test]
fn compile_reads_a_multi_megabyte_master_from_stdin() {
    let master = noise_png_base64(1080, 1080);
    assert!(
        master.len() > 128 * 1024 * 8,
        "fixture must exceed the argv limit by far"
    );
    let payload = serde_json::json!({
        "template_id": "panel-square",
        "asset_input": {"width": 1080, "height": 1080},
        "source_data": master,
        "seed": 1,
    });

    let (code, body) = run_cli(
        &["compile", "--template", "panel-square", "--payload", "-"],
        &payload.to_string(),
    );

    assert_eq!(code, 0, "{body}");
    assert_eq!(body["success"], true);
    let png = body["asset"]["exports"]
        .as_array()
        .unwrap()
        .iter()
        .find(|e| e["format"] == "png")
        .expect("png export");
    assert_eq!(png["size"], serde_json::json!([1080, 1080]));
    // The master reached the output; it is not the placeholder.
    assert_eq!(png["data_base64"].as_str().unwrap().len(), master.len());
}

#[test]
fn validate_reads_the_payload_from_stdin() {
    let (code, body) = run_cli(
        &["validate", "--template", "panel-square", "--payload", "-"],
        r#"{"width": 1080, "height": 1080}"#,
    );
    assert_eq!(code, 0, "{body}");
    assert_eq!(body["valid"], true);
    assert_eq!(body["template_id"], "panel-square");
}

#[test]
fn an_unreadable_payload_is_reported_not_guessed() {
    let (code, body) = run_cli(
        &["compile", "--template", "panel-square", "--payload", "-"],
        "not json",
    );
    assert_ne!(code, 0);
    assert_eq!(body["success"], false);
}
