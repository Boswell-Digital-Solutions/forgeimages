//! Source master ingestion.
//!
//! `CompileRequest::source_data` carries a caller-supplied master asset as
//! base64. It was declared on the request, threaded through the Python bridge
//! and the skill, canonicalized into the job hash — and then **read by nothing**.
//! Every compile emitted the placeholder export instead, so a caller who
//! supplied a master got back an asset that had no relationship to it, with a
//! job hash that claimed otherwise.
//!
//! This module is the missing half. It decodes the master, identifies what it
//! actually is, and converts it to an export spec. The governing rule is Law 3
//! (*Validation Is Protective*) applied to input rather than output:
//!
//! > **A supplied master is never silently ignored.** If it cannot be decoded,
//! > is not admissible for the template, or cannot be converted to a required
//! > export, the compile fails. It does not fall back to the placeholder.
//!
//! Falling back would be the worst available behaviour: the caller believes
//! their master was compiled, the manifest hash attests to a reproduction that
//! never happened, and nothing in the output says otherwise.
//!
//! What this module does **not** do is invent. SVG rasterization needs a real
//! rasterizer and is out of scope here. Raster→PDF *is* implemented, but only
//! for print-admissible masters (opaque grayscale; CMYK is representable by the
//! writer): an RGB master would require a color-managed RGB→CMYK conversion for
//! PDF/X-1a, and ForgeImages does not invent color. Every unimplemented or
//! inadmissible conversion is refused explicitly rather than approximated, so a
//! path we cannot honour reads as a refusal instead of a wrong file.

use base64::Engine as _;
use thiserror::Error;

use crate::templates::ExportFormat;

/// Dots per inch for the print PDF path. 300 is the KDP requirement and the
/// resolution the `book-cover-kdp` dimensions are computed at (3896x2775 px =
/// 12.987" x 9.25" full-bleed cover). Per-template DPI would mean threading
/// `PrintSpec` through this signature; that is a deliberate future extension,
/// and 300 is correct for the one template that requests a PDF today.
const PRINT_DPI: u32 = 300;

/// Bleed inset, in inches, applied to the `TrimBox`. KDP's print spec is
/// 0.125" bleed on every side.
const KDP_BLEED_INCHES: f64 = 0.125;

/// What a decoded master turned out to be.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum SourceMasterKind {
    /// SVG markup — the vector master of Law 1.
    Svg,
    /// A decodable raster image (PNG/JPEG/TIFF per the enabled `image` features).
    /// This is the shape a diffusion model produces.
    Raster,
}

/// A decoded, identified source master.
#[derive(Debug, Clone)]
pub struct SourceMaster {
    pub kind: SourceMasterKind,
    pub bytes: Vec<u8>,
    /// Raster only: the detected container format.
    pub format: Option<image::ImageFormat>,
    /// Raster only: true pixel dimensions read from the image itself, not from
    /// what the caller claimed in `AssetInput`.
    pub dimensions: Option<(u32, u32)>,
}

impl SourceMaster {
    pub fn is_raster(&self) -> bool {
        self.kind == SourceMasterKind::Raster
    }

    /// A short, log-safe description. Never includes the payload.
    pub fn describe(&self) -> String {
        match (self.kind, self.dimensions) {
            (SourceMasterKind::Svg, _) => "svg".to_string(),
            (SourceMasterKind::Raster, Some((w, h))) => {
                format!("{}x{} raster", w, h)
            }
            (SourceMasterKind::Raster, None) => "raster".to_string(),
        }
    }
}

#[derive(Debug, Error)]
pub enum SourceMasterError {
    #[error("source_data is not valid base64: {0}")]
    InvalidBase64(String),

    #[error("source_data decoded to zero bytes")]
    Empty,

    #[error("source_data is neither SVG markup nor a decodable raster image")]
    UnrecognizedFormat,

    #[error("source_data raster could not be decoded: {0}")]
    RasterDecode(String),

    #[error(
        "template declares vector_master, so a {found} master is not admissible \
         (Law 1: SVG Is Truth)"
    )]
    VectorMasterRequired { found: String },

    #[error(
        "asset_input declares {declared_w}x{declared_h} but the supplied master \
         is {actual_w}x{actual_h}; validation ran against dimensions the master \
         does not have"
    )]
    DeclaredDimensionMismatch {
        declared_w: u32,
        declared_h: u32,
        actual_w: u32,
        actual_h: u32,
    },

    #[error(
        "export '{export_id}' needs {to}, and converting a {from} master to it \
         is not implemented; refusing rather than emitting a placeholder"
    )]
    UnsupportedConversion {
        export_id: String,
        from: String,
        to: String,
    },

    #[error("failed to encode export '{export_id}': {message}")]
    EncodeFailed { export_id: String, message: String },

    #[error(
        "export '{export_id}': PDF/X-1a is a device grayscale/CMYK print standard, \
         but the master is {color_model}. ForgeImages does not perform color-managed \
         RGB→CMYK conversion (it does not invent color); supply an opaque 8-bit \
         grayscale or CMYK master."
    )]
    PrintColorNotAdmissible {
        export_id: String,
        color_model: String,
    },

    #[error(
        "export '{export_id}': the master carries transparency, which PDF/X-1a \
         forbids; flattening it would invent a background. Supply an opaque master."
    )]
    PrintTransparencyNotAllowed { export_id: String },

    #[error("export '{export_id}': PDF generation failed: {message}")]
    PdfWriteFailed { export_id: String, message: String },
}

/// Decode `source_data` and identify it.
///
/// Deliberately strict: an unreadable master is an error, never an empty
/// `Option` that the caller might treat as "no master supplied". Those two
/// states mean opposite things and must not collapse.
pub fn decode(source_data: &str) -> Result<SourceMaster, SourceMasterError> {
    let bytes = base64::engine::general_purpose::STANDARD
        .decode(source_data.trim())
        .map_err(|e| SourceMasterError::InvalidBase64(e.to_string()))?;

    if bytes.is_empty() {
        return Err(SourceMasterError::Empty);
    }

    if looks_like_svg(&bytes) {
        return Ok(SourceMaster {
            kind: SourceMasterKind::Svg,
            bytes,
            format: None,
            dimensions: None,
        });
    }

    // Not SVG — it must be a raster we can actually decode. `guess_format`
    // alone is not enough: a truncated or corrupt file can carry a valid magic
    // number, and accepting it here would push the failure into export
    // rendering where it is harder to attribute.
    let format = image::guess_format(&bytes).map_err(|_| SourceMasterError::UnrecognizedFormat)?;
    let decoded = image::load_from_memory_with_format(&bytes, format)
        .map_err(|e| SourceMasterError::RasterDecode(e.to_string()))?;

    Ok(SourceMaster {
        kind: SourceMasterKind::Raster,
        dimensions: Some((decoded.width(), decoded.height())),
        format: Some(format),
        bytes,
    })
}

/// Whether the leading bytes are SVG markup.
///
/// Tolerates a UTF-8 BOM, leading whitespace, and an XML prolog before the
/// `<svg` element. Anything else is left to raster detection.
fn looks_like_svg(bytes: &[u8]) -> bool {
    let without_bom = bytes.strip_prefix(&[0xEF, 0xBB, 0xBF]).unwrap_or(bytes);

    // Only the head matters, and a raster file's bytes are not valid UTF-8 in
    // general — so inspect a bounded prefix lossily rather than the whole file.
    let head_len = without_bom.len().min(512);
    let head = String::from_utf8_lossy(&without_bom[..head_len]);
    let head = head.trim_start();

    if head.starts_with("<svg") {
        return true;
    }
    head.starts_with("<?xml") && head.contains("<svg")
}

/// Check the master against template-level and caller-declared constraints.
///
/// Runs before any export is produced, so a rejected master costs nothing and
/// the error names the reason rather than surfacing as a downstream encode
/// failure.
pub fn check_admissible(
    master: &SourceMaster,
    vector_master_required: bool,
    declared: (u32, u32),
) -> Result<(), SourceMasterError> {
    if vector_master_required && master.is_raster() {
        return Err(SourceMasterError::VectorMasterRequired {
            found: master.describe(),
        });
    }

    // The validator ran against `AssetInput`. If the master's real dimensions
    // disagree with what was declared, then validation approved something other
    // than the asset being compiled, and its verdict does not apply.
    if let Some((actual_w, actual_h)) = master.dimensions {
        let (declared_w, declared_h) = declared;
        if actual_w != declared_w || actual_h != declared_h {
            return Err(SourceMasterError::DeclaredDimensionMismatch {
                declared_w,
                declared_h,
                actual_w,
                actual_h,
            });
        }
    }

    Ok(())
}

/// Produce the bytes for one export from the master.
///
/// Supported, all deterministic:
///   * SVG master  → SVG export   (pass-through)
///   * raster master → PNG/JPEG export (pass-through when the format and size
///     already match, otherwise a fixed-filter resize and re-encode)
///   * raster master → PDF export, when the master is print-admissible
///     (opaque grayscale): a PDF/X-1a:2001 file via [`crate::pdf`]. This is what
///     lets `book-cover-kdp` — whose `cover-pdf` export is `required` — actually
///     compile from a supplied cover master.
///
/// Everything else is refused, and the refusal names why. An RGB master to a PDF
/// export is the important case: PDF/X-1a is device CMYK/grayscale, and turning
/// RGB into CMYK is a color-managed step ForgeImages will not invent — so it
/// refuses rather than emit a "print-ready" file built on made-up color.
pub fn render_export(
    master: &SourceMaster,
    export_id: &str,
    target: ExportFormat,
    size: [u32; 2],
) -> Result<Vec<u8>, SourceMasterError> {
    let unsupported = |to: &str| SourceMasterError::UnsupportedConversion {
        export_id: export_id.to_string(),
        from: match master.kind {
            SourceMasterKind::Svg => "svg".to_string(),
            SourceMasterKind::Raster => "raster".to_string(),
        },
        to: to.to_string(),
    };

    // Matched by reference: `ExportFormat` is not `Copy`, and the raster arm
    // needs `target` again to pick the encoder.
    match (master.kind, &target) {
        // Vector in, vector out. No rasterizer needed and none is pretended.
        (SourceMasterKind::Svg, ExportFormat::Svg) => Ok(master.bytes.clone()),

        (SourceMasterKind::Raster, ExportFormat::Png)
        | (SourceMasterKind::Raster, ExportFormat::Jpg) => {
            let target_format = match target {
                ExportFormat::Png => image::ImageFormat::Png,
                _ => image::ImageFormat::Jpeg,
            };

            // Exact match: hand back the original bytes untouched. Re-encoding
            // an already-correct file would change its hash for no reason and
            // lose whatever the encoder chose.
            if master.format == Some(target_format) && master.dimensions == Some((size[0], size[1]))
            {
                return Ok(master.bytes.clone());
            }

            let decoded = image::load_from_memory(&master.bytes).map_err(|e| {
                SourceMasterError::EncodeFailed {
                    export_id: export_id.to_string(),
                    message: e.to_string(),
                }
            })?;

            // Fixed filter, so the same master and spec always yield the same
            // bytes (Law 4: Deterministic Output).
            let resized = if decoded.width() == size[0] && decoded.height() == size[1] {
                decoded
            } else {
                decoded.resize_exact(size[0], size[1], image::imageops::FilterType::Lanczos3)
            };

            let mut out = std::io::Cursor::new(Vec::new());
            resized.write_to(&mut out, target_format).map_err(|e| {
                SourceMasterError::EncodeFailed {
                    export_id: export_id.to_string(),
                    message: e.to_string(),
                }
            })?;
            Ok(out.into_inner())
        }

        // The master IS the artwork, so this is a real conversion, not a
        // rasterization. Admissibility (color, transparency) is decided inside.
        (SourceMasterKind::Raster, ExportFormat::Pdf) => raster_to_pdf_x1a(master, export_id, size),
        // An SVG master would need rasterizing first; no rasterizer, so refuse.
        (SourceMasterKind::Svg, ExportFormat::Pdf) => Err(unsupported("pdf")),

        (_, ExportFormat::Ico) => Err(unsupported("ico")),
        (SourceMasterKind::Raster, ExportFormat::Svg) => Err(unsupported("svg")),
        (SourceMasterKind::Svg, _) => Err(unsupported("a raster format")),
    }
}

/// Convert a raster master to a PDF/X-1a:2001 export.
///
/// Only opaque grayscale is admissible today: X-1a is a device grayscale/CMYK
/// standard, and an RGB master would need a color-managed RGB→CMYK conversion
/// that ForgeImages does not perform. Both inadmissible cases (RGB, and
/// transparency) are refused by name rather than flattened or approximated.
fn raster_to_pdf_x1a(
    master: &SourceMaster,
    export_id: &str,
    size: [u32; 2],
) -> Result<Vec<u8>, SourceMasterError> {
    let decoded =
        image::load_from_memory(&master.bytes).map_err(|e| SourceMasterError::PdfWriteFailed {
            export_id: export_id.to_string(),
            message: format!("could not decode master: {e}"),
        })?;

    // Reduce to opaque 8-bit grayscale samples, or refuse with the reason.
    let gray: image::GrayImage = match decoded.color() {
        image::ColorType::L8 => decoded.into_luma8(),
        image::ColorType::La8 => {
            let la = decoded.into_luma_alpha8();
            // A fully-opaque alpha channel carries no information and can be
            // dropped; a partially-transparent one cannot be honoured without
            // inventing what shows through.
            if la.pixels().any(|p| p[1] != u8::MAX) {
                return Err(SourceMasterError::PrintTransparencyNotAllowed {
                    export_id: export_id.to_string(),
                });
            }
            let luma: Vec<u8> = la.pixels().map(|p| p[0]).collect();
            image::GrayImage::from_raw(la.width(), la.height(), luma)
                .expect("luma buffer has exactly width*height samples")
        }
        other => {
            return Err(SourceMasterError::PrintColorNotAdmissible {
                export_id: export_id.to_string(),
                color_model: format!("{other:?}").to_lowercase(),
            });
        }
    };

    // Match the export spec. When it already matches, keep the pixels verbatim
    // (no needless resample, and the samples embed byte-for-byte).
    let gray = if gray.width() == size[0] && gray.height() == size[1] {
        gray
    } else {
        image::imageops::resize(
            &gray,
            size[0],
            size[1],
            image::imageops::FilterType::Lanczos3,
        )
    };

    let geometry = crate::pdf::PrintGeometry {
        dpi: PRINT_DPI,
        bleed_pts: KDP_BLEED_INCHES * 72.0,
    };
    crate::pdf::write_pdf_x1a(
        size[0],
        size[1],
        gray.as_raw(),
        crate::pdf::DeviceColor::Gray,
        &geometry,
        &crate::pdf::OutputIntent::kdp_us_swop(),
    )
    .map_err(|e| SourceMasterError::PdfWriteFailed {
        export_id: export_id.to_string(),
        message: e.to_string(),
    })
}
