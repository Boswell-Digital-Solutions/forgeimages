//! Source master invariant tests.
//!
//! The governing rule, stated once:
//!
//! > **A supplied master is never silently ignored.**
//!
//! Before this slice, `source_data` was decoded by nothing. Every compile
//! returned the placeholder export — an empty `<svg>` or a 1x1 PNG — while the
//! job hash canonicalized the master and attested to a reproduction that never
//! happened. A caller had no way to tell the difference from a real compile.
//!
//! These tests pin both halves: a master that *can* be honoured must reach the
//! output, and a master that *cannot* must fail the compile rather than fall
//! back to the placeholder.

use base64::Engine as _;

use forgeimages_core::{
    CompilationPipeline, CompileRequest,
    templates::{
        AssetClass, ExportFormat, ExportSpec, FailureMode, ResolutionRule, RuleConfig, Template,
        TemplateRegistry, ValidationConfig, ValidationRules,
    },
    validation::AssetInput,
};

// ── fixtures ─────────────────────────────────────────────────────────────────

/// A real, decodable PNG of the requested size — not a hand-written byte blob,
/// so the dimensions the decoder reports are genuinely the ones under test.
fn png_bytes(w: u32, h: u32) -> Vec<u8> {
    let img = image::DynamicImage::new_rgba8(w, h);
    let mut out = std::io::Cursor::new(Vec::new());
    img.write_to(&mut out, image::ImageFormat::Png)
        .expect("encode test png");
    out.into_inner()
}

fn b64(bytes: &[u8]) -> String {
    base64::engine::general_purpose::STANDARD.encode(bytes)
}

const SVG_MASTER: &str = r#"<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><rect width="64" height="64"/></svg>"#;

fn template(id: &str, vector_master: bool, exports: Vec<ExportSpec>) -> Template {
    Template {
        id: id.to_string(),
        name: id.to_string(),
        description: "fixture".to_string(),
        template_version: "1.0.0".to_string(),
        engine_min_version: "1.0.0".to_string(),
        deprecated: false,
        superseded_by: None,
        asset_class: AssetClass::Icon,
        aspect_ratio: [1, 1],
        canonical_size: [64, 64],
        vector_master,
        validation: ValidationConfig {
            required: true,
            failure_mode: FailureMode::Block,
            rules: ValidationRules {
                aspect_ratio: RuleConfig { enabled: false, tolerance: 0.01 },
                // Kept low so fixtures stay small; resolution is not what these
                // tests are about.
                resolution: ResolutionRule { enabled: true, min_width: 16, min_height: 16 },
                color_count: Default::default(),
            },
        },
        exports,
    }
}

fn export(id: &str, format: ExportFormat, size: [u32; 2]) -> ExportSpec {
    ExportSpec {
        id: id.to_string(),
        description: id.to_string(),
        size,
        format,
        required: true,
    }
}

fn pipeline_with(t: Template) -> CompilationPipeline {
    let mut registry = TemplateRegistry::new();
    registry.register(t);
    CompilationPipeline::new(registry)
}

fn request(template_id: &str, w: u32, h: u32, source_data: Option<String>) -> CompileRequest {
    CompileRequest {
        template_id: template_id.to_string(),
        asset_input: AssetInput { width: w, height: h, color_count: None, format: None },
        source_data,
        seed: None,
        prompt: None,
    }
}

// ── the invariant ────────────────────────────────────────────────────────────

#[test]
fn invariant_supplied_master_reaches_the_output() {
    // The whole point: supplying a master must change the compiled bytes. If
    // this fails, `source_data` is a no-op again.
    let t = template("raster-png", false, vec![export("master", ExportFormat::Png, [64, 64])]);
    let master = png_bytes(64, 64);

    let with_master = pipeline_with(t.clone())
        .compile_asset(&request("raster-png", 64, 64, Some(b64(&master))))
        .expect("compile with master");
    let without_master = pipeline_with(t)
        .compile_asset(&request("raster-png", 64, 64, None))
        .expect("compile without master");

    let got = &with_master.exports[0];
    let placeholder = &without_master.exports[0];

    assert_ne!(
        got.data_base64, placeholder.data_base64,
        "supplying a master produced the placeholder — source_data is being ignored"
    );
    assert_eq!(got.data_base64, b64(&master), "master should pass through unchanged");
    assert_ne!(got.hash, placeholder.hash, "export hash must reflect the master");
}

#[test]
fn invariant_unusable_master_fails_rather_than_falling_back() {
    // A master that cannot produce the export must NOT quietly become a
    // placeholder. Refusal is the only honest outcome.
    let t = template("pdf-only", false, vec![export("cover-pdf", ExportFormat::Pdf, [64, 64])]);
    let result = pipeline_with(t).compile_asset(&request(
        "pdf-only",
        64,
        64,
        Some(b64(&png_bytes(64, 64))),
    ));

    let err = result.expect_err("raster->pdf is unimplemented and must be refused");
    let msg = err.to_string();
    assert!(msg.contains("pdf"), "error should name the conversion: {msg}");
    assert!(
        msg.contains("not implemented") || msg.contains("refusing"),
        "error should say it refused rather than approximated: {msg}"
    );
}

// ── decode failures ──────────────────────────────────────────────────────────

#[test]
fn malformed_base64_is_rejected() {
    let t = template("raster-png", false, vec![export("master", ExportFormat::Png, [64, 64])]);
    let err = pipeline_with(t)
        .compile_asset(&request("raster-png", 64, 64, Some("not!valid!base64".to_string())))
        .expect_err("malformed base64 must fail");
    assert!(err.to_string().contains("base64"), "{err}");
}

#[test]
fn empty_master_is_rejected() {
    let t = template("raster-png", false, vec![export("master", ExportFormat::Png, [64, 64])]);
    let err = pipeline_with(t)
        .compile_asset(&request("raster-png", 64, 64, Some(b64(b""))))
        .expect_err("empty master must fail");
    assert!(err.to_string().contains("zero bytes"), "{err}");
}

#[test]
fn unrecognized_payload_is_rejected() {
    let t = template("raster-png", false, vec![export("master", ExportFormat::Png, [64, 64])]);
    let err = pipeline_with(t)
        .compile_asset(&request("raster-png", 64, 64, Some(b64(b"this is just text"))))
        .expect_err("non-image, non-svg payload must fail");
    assert!(err.to_string().contains("neither SVG"), "{err}");
}

#[test]
fn corrupt_raster_with_valid_magic_is_rejected() {
    // A truncated PNG still carries the PNG magic number. Sniffing alone would
    // accept it and push the failure into encoding, where it is harder to
    // attribute — so decoding is proven up front.
    let mut truncated = png_bytes(64, 64);
    truncated.truncate(16);

    let t = template("raster-png", false, vec![export("master", ExportFormat::Png, [64, 64])]);
    let err = pipeline_with(t)
        .compile_asset(&request("raster-png", 64, 64, Some(b64(&truncated))))
        .expect_err("corrupt raster must fail");
    assert!(err.to_string().contains("could not be decoded"), "{err}");
}

// ── admissibility ────────────────────────────────────────────────────────────

#[test]
fn raster_master_is_refused_by_a_vector_master_template() {
    // Law 1: SVG Is Truth. A template that declares vector_master does not
    // accept a diffusion raster.
    let t = template("vector-only", true, vec![export("master", ExportFormat::Svg, [64, 64])]);
    let err = pipeline_with(t)
        .compile_asset(&request("vector-only", 64, 64, Some(b64(&png_bytes(64, 64)))))
        .expect_err("raster master must be refused for a vector_master template");
    assert!(err.to_string().contains("vector_master"), "{err}");
}

#[test]
fn declared_dimensions_must_match_the_master() {
    // Validation ran against AssetInput. If the master is a different size then
    // the validator approved something other than what is being compiled, and
    // its verdict does not apply to this asset.
    let t = template("raster-png", false, vec![export("master", ExportFormat::Png, [64, 64])]);
    let err = pipeline_with(t)
        .compile_asset(&request("raster-png", 64, 64, Some(b64(&png_bytes(32, 32)))))
        .expect_err("dimension mismatch must fail");
    let msg = err.to_string();
    assert!(msg.contains("64x64") && msg.contains("32x32"), "{msg}");
}

// ── supported conversions ────────────────────────────────────────────────────

#[test]
fn svg_master_passes_through_to_an_svg_export() {
    let t = template("vector-only", true, vec![export("master", ExportFormat::Svg, [64, 64])]);
    let asset = pipeline_with(t)
        .compile_asset(&request("vector-only", 64, 64, Some(b64(SVG_MASTER.as_bytes()))))
        .expect("svg master should compile");
    assert_eq!(asset.exports[0].data_base64, b64(SVG_MASTER.as_bytes()));
}

#[test]
fn raster_master_is_resized_to_the_export_spec() {
    // Master matches the declared asset size; the export spec asks for smaller.
    let t = template("raster-png", false, vec![export("thumb", ExportFormat::Png, [32, 32])]);
    let master = png_bytes(64, 64);
    let asset = pipeline_with(t)
        .compile_asset(&request("raster-png", 64, 64, Some(b64(&master))))
        .expect("resize should succeed");

    let out = base64::engine::general_purpose::STANDARD
        .decode(&asset.exports[0].data_base64)
        .expect("decode export");
    let decoded = image::load_from_memory(&out).expect("export must be a real image");
    assert_eq!((decoded.width(), decoded.height()), (32, 32));
    assert_ne!(out, master, "a resized export cannot be the original bytes");
}

#[test]
fn resizing_is_deterministic() {
    // Law 4: Deterministic Output. Same master and spec, twice, byte-identical.
    let t = template("raster-png", false, vec![export("thumb", ExportFormat::Png, [32, 32])]);
    let master = b64(&png_bytes(64, 64));

    let first = pipeline_with(t.clone())
        .compile_asset(&request("raster-png", 64, 64, Some(master.clone())))
        .expect("first compile");
    let second = pipeline_with(t)
        .compile_asset(&request("raster-png", 64, 64, Some(master)))
        .expect("second compile");

    assert_eq!(first.exports[0].data_base64, second.exports[0].data_base64);
    assert_eq!(first.exports[0].hash, second.exports[0].hash);
}

// ── back-compatibility ───────────────────────────────────────────────────────

#[test]
fn no_master_keeps_the_legacy_placeholder_path() {
    // Callers that never supplied a master are unaffected by this change.
    let t = template("raster-png", false, vec![export("master", ExportFormat::Png, [64, 64])]);
    let asset = pipeline_with(t)
        .compile_asset(&request("raster-png", 64, 64, None))
        .expect("compile without a master still succeeds");
    assert_eq!(asset.exports.len(), 1);
    assert!(!asset.exports[0].data_base64.is_empty());
}
