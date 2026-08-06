//! Deterministic raster → PDF/X-1a:2001 writer.
//!
//! This module is the missing half of the cover path. `book-cover-kdp` marks a
//! `PDF/X-1a` export `required`, but nothing could produce one: the pipeline
//! handed back `b"placeholder"` for a file it described as print-ready, and
//! [`crate::source_master`] refused raster→PDF outright rather than emit that
//! lie. This writer makes the honest version possible.
//!
//! # Why hand-write the PDF
//!
//! Law 4 (*Deterministic Output*) is non-negotiable, and every export is hashed
//! into a manifest that attests to reproduction. A general PDF library injects
//! exactly the things that break byte-reproducibility: a wall-clock
//! `CreationDate`, a random file `/ID`, encoder-version-dependent stream
//! compression. So the output here is a **pure function of its inputs** — the
//! samples, the geometry, the output intent — and nothing else. No clock, no
//! RNG, no third-party encoder in the reproducibility path. The image stream is
//! stored uncompressed for the same reason: its bytes are the samples, verbatim,
//! with no compressor version to drift under us. (Flate/DCT are a legitimate
//! future size optimisation, but only once their determinism is audited.)
//!
//! # Why only Gray and CMYK
//!
//! PDF/X-1a is *blind CMYK exchange*: it permits DeviceGray, DeviceCMYK and
//! spot color, and **forbids RGB / device-independent color**. [`DeviceColor`]
//! encodes that at the type level — there is no RGB variant, so an RGB master
//! cannot reach this writer at all. Converting RGB to CMYK for print is a
//! color-managed operation that depends on a chosen output profile; ForgeImages
//! does not invent it (Law 6, and "never invents imagery" applied to color).
//! The refusal lives in [`crate::source_master`]; this writer only ever sees
//! print-admissible samples.
//!
//! # Conformance boundary (read this before trusting the label)
//!
//! The file this writer emits is *structurally* PDF/X-1a:2001: a PDF 1.3 base
//! with the mandated `OutputIntents`, `GTS_PDFXVersion`, `TrimBox`, `Trapped`,
//! device-only color, and no transparency. Its conformance for **blind
//! exchange** is only as strong as the [`OutputIntent`] it is given:
//!
//!   * With an embedded [`IccProfile`] (`DestOutputProfile`), the printing
//!     condition travels with the file — the strongest form.
//!   * With a *registered* condition referenced by name only (the default,
//!     [`OutputIntent::kdp_us_swop`]), the file is spec-permitted but relies on
//!     the recipient resolving the condition. Strict preflight may want the
//!     embedded profile.
//!
//! This module does not — cannot — claim a given file passes a specific
//! vendor's preflight. The tests assert the structural facts that are
//! objectively checkable here; strict conformance against a real RIP is a
//! deployment-time verification with a real profile.

use thiserror::Error;

use crate::ENGINE_VERSION;

/// The device color models admissible in PDF/X-1a.
///
/// There is deliberately no `Rgb`: X-1a forbids RGB, and encoding that absence
/// in the type means an inadmissible master is rejected *before* this writer,
/// where the reason can be named, rather than producing a non-conformant file
/// labelled as conformant.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum DeviceColor {
    /// Single-channel grayscale, 8 bits per sample → `/DeviceGray`.
    Gray,
    /// Four-channel process color, 8 bits per sample → `/DeviceCMYK`.
    Cmyk,
}

impl DeviceColor {
    /// Samples per pixel.
    pub fn components(self) -> usize {
        match self {
            DeviceColor::Gray => 1,
            DeviceColor::Cmyk => 4,
        }
    }

    fn pdf_name(self) -> &'static str {
        match self {
            DeviceColor::Gray => "/DeviceGray",
            DeviceColor::Cmyk => "/DeviceCMYK",
        }
    }

    fn describe(self) -> &'static str {
        match self {
            DeviceColor::Gray => "grayscale",
            DeviceColor::Cmyk => "CMYK",
        }
    }
}

/// An embedded ICC destination profile for an [`OutputIntent`].
///
/// `components` is the profile's own device channel count (the *press*, not the
/// image): 1 for a grayscale printing condition, 4 for CMYK. It is not required
/// to match the image's [`DeviceColor`] — a grayscale image is perfectly valid
/// inside a CMYK-intent X-1a file.
#[derive(Debug, Clone)]
pub struct IccProfile {
    pub bytes: Vec<u8>,
    pub components: u8,
}

/// The printing condition an X-1a file is prepared for.
///
/// This is a real print decision — stock, press, ink — so it is explicit rather
/// than hidden behind a default nobody chose. See [`OutputIntent::kdp_us_swop`]
/// for the ForgeImages default and its rationale.
#[derive(Debug, Clone)]
pub struct OutputIntent {
    /// Registered characterization identifier, e.g. `"CGATS TR 001"`.
    pub condition_identifier: String,
    /// Human-readable condition, e.g. `"U.S. Web Coated (SWOP) v2"`.
    pub condition_info: String,
    /// Registry that lists the identifier. The ICC registry for standard
    /// conditions: `"http://www.color.org"`.
    pub registry_name: String,
    /// Embedded destination profile. When `None`, the file relies on the
    /// registered condition by name (spec-permitted; see the module conformance
    /// note). When `Some`, the profile travels with the file.
    pub dest_output_profile: Option<IccProfile>,
}

impl OutputIntent {
    /// The ForgeImages default: U.S. Web Coated (SWOP) v2, referenced by its
    /// registered CGATS name.
    ///
    /// SWOP is the sheet/web coated condition Amazon KDP (a U.S.-centric print
    /// channel) targets, which is why it is the default for the `book-cover-kdp`
    /// template. It is referenced **by name**, with no embedded profile, so the
    /// default carries no third-party ICC binary and no licensing question into
    /// the repository. A deployment that needs an embedded profile — or a
    /// different condition (e.g. FOGRA for European coated stock) — supplies its
    /// own [`OutputIntent`]; this is the one place that decision is made.
    pub fn kdp_us_swop() -> Self {
        Self {
            condition_identifier: "CGATS TR 001".to_string(),
            condition_info: "U.S. Web Coated (SWOP) v2".to_string(),
            registry_name: "http://www.color.org".to_string(),
            dest_output_profile: None,
        }
    }
}

/// Physical page geometry.
#[derive(Debug, Clone)]
pub struct PrintGeometry {
    /// Dots per inch used to convert pixel dimensions to physical points
    /// (`points = pixels / dpi * 72`). 300 for KDP print.
    pub dpi: u32,
    /// Bleed, in points, that the `TrimBox` is inset from the media edge on all
    /// four sides. `0.125"` (9 pt) for KDP. Clamped so the trim area stays
    /// positive for small pages.
    pub bleed_pts: f64,
}

#[derive(Debug, Error)]
pub enum PdfError {
    #[error(
        "sample buffer is {got} bytes but a {w}x{h} {color} image needs {want} \
         ({components} bytes/pixel)"
    )]
    SampleLengthMismatch {
        w: u32,
        h: u32,
        color: &'static str,
        components: usize,
        want: usize,
        got: usize,
    },

    #[error("image dimensions must be non-zero (got {w}x{h})")]
    ZeroDimension { w: u32, h: u32 },

    #[error("dpi must be non-zero")]
    ZeroDpi,

    #[error(
        "output intent profile declares {declared} components; a PDF/X-1a \
         output intent must describe a grayscale (1) or CMYK (4) device"
    )]
    ProfileComponentInvalid { declared: u8 },
}

/// A fixed synthetic timestamp stamped into every PDF's `CreationDate` /
/// `ModDate`.
///
/// PDF/X-1a requires both dates, but a wall-clock value would make identical
/// inputs produce different bytes and break Law 4. The document's real
/// provenance and time live in the compiled asset's manifest (`created_at`) and
/// the append-only audit log; the value *inside* the PDF is deliberately fixed
/// so reproduction is exact. It is not, and does not claim to be, the moment of
/// creation.
const FIXED_DATE: &str = "D:20200101000000Z";

/// Write a single-image PDF/X-1a:2001 document.
///
/// `samples` are row-major, top row first, `width * height * color.components()`
/// bytes, 8 bits per sample. The image fills the full media (bleed) box; the
/// `TrimBox` is inset by `geometry.bleed_pts`.
pub fn write_pdf_x1a(
    width: u32,
    height: u32,
    samples: &[u8],
    color: DeviceColor,
    geometry: &PrintGeometry,
    intent: &OutputIntent,
) -> Result<Vec<u8>, PdfError> {
    if width == 0 || height == 0 {
        return Err(PdfError::ZeroDimension {
            w: width,
            h: height,
        });
    }
    if geometry.dpi == 0 {
        return Err(PdfError::ZeroDpi);
    }
    let components = color.components();
    let want = (width as usize) * (height as usize) * components;
    if samples.len() != want {
        return Err(PdfError::SampleLengthMismatch {
            w: width,
            h: height,
            color: color.describe(),
            components,
            want,
            got: samples.len(),
        });
    }
    if let Some(icc) = &intent.dest_output_profile
        && icc.components != 1
        && icc.components != 4
    {
        return Err(PdfError::ProfileComponentInvalid {
            declared: icc.components,
        });
    }

    // Physical geometry. MediaBox is the full bleed area (the image is the
    // full-bleed artwork); TrimBox marks where the printer cuts.
    let dpi = geometry.dpi as f64;
    let w_pts = width as f64 / dpi * 72.0;
    let h_pts = height as f64 / dpi * 72.0;
    // Keep the trim area strictly positive even for tiny pages.
    let max_bleed = ((w_pts.min(h_pts)) / 2.0 - 1.0).max(0.0);
    let bleed = geometry.bleed_pts.max(0.0).min(max_bleed);

    // Deterministic file /ID: a function of the pixels and the geometry, so two
    // different covers never collide and the same cover always reproduces.
    let id_hex = {
        let mut src = Vec::with_capacity(samples.len() + 64);
        src.extend_from_slice(
            format!(
                "{}x{}@{} {} b{}",
                width,
                height,
                geometry.dpi,
                color.pdf_name(),
                num(bleed)
            )
            .as_bytes(),
        );
        src.extend_from_slice(samples);
        crate::hashing::sha256_hex(&src)[..32].to_string()
    };

    // Draw the image over the whole media box. Image space is the unit square
    // with the first sample row at the top, so this `cm` places it upright with
    // no flip.
    let content = format!("q\n{} 0 0 {} 0 0 cm\n/Im0 Do\nQ\n", num(w_pts), num(h_pts));

    let embedded = intent.dest_output_profile.is_some();
    let n_objects: u32 = if embedded { 8 } else { 7 };

    let mut buf: Vec<u8> = Vec::with_capacity(samples.len() + 2048);
    let mut offsets: Vec<usize> = Vec::with_capacity(n_objects as usize);

    // PDF/X-1a:2001 is defined on a PDF 1.3 base. The `%âãÏÓ` binary marker
    // tells naive tools to treat the file as binary.
    buf.extend_from_slice(b"%PDF-1.3\n");
    buf.extend_from_slice(b"%\xE2\xE3\xCF\xD3\n");

    // 1 — Catalog. `/OutputIntents` lives here; it is the element that makes an
    // otherwise-1.3 file a PDF/X-1a one.
    obj_header(&mut buf, &mut offsets, 1);
    buf.extend_from_slice(b"<< /Type /Catalog /Pages 2 0 R /OutputIntents [7 0 R] >>\nendobj\n");

    // 2 — Pages
    obj_header(&mut buf, &mut offsets, 2);
    buf.extend_from_slice(b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n");

    // 3 — Page, with the three boxes X-1a cares about.
    obj_header(&mut buf, &mut offsets, 3);
    let page = format!(
        "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {mw} {mh}] \
         /BleedBox [0 0 {mw} {mh}] /TrimBox [{tx0} {ty0} {tx1} {ty1}] \
         /Resources << /XObject << /Im0 4 0 R >> /ProcSet [/PDF /ImageB /ImageC /ImageI] >> \
         /Contents 5 0 R >>\nendobj\n",
        mw = num(w_pts),
        mh = num(h_pts),
        tx0 = num(bleed),
        ty0 = num(bleed),
        tx1 = num(w_pts - bleed),
        ty1 = num(h_pts - bleed),
    );
    buf.extend_from_slice(page.as_bytes());

    // 4 — Image XObject. Uncompressed (no `/Filter`); `/Length` is exact so the
    // arbitrary sample bytes — which may contain `endstream` — parse correctly.
    obj_header(&mut buf, &mut offsets, 4);
    buf.extend_from_slice(
        format!(
            "<< /Type /XObject /Subtype /Image /Width {w} /Height {h} \
             /ColorSpace {cs} /BitsPerComponent 8 /Length {len} >>\nstream\n",
            w = width,
            h = height,
            cs = color.pdf_name(),
            len = samples.len(),
        )
        .as_bytes(),
    );
    buf.extend_from_slice(samples);
    buf.extend_from_slice(b"\nendstream\nendobj\n");

    // 5 — Content stream
    obj_header(&mut buf, &mut offsets, 5);
    buf.extend_from_slice(format!("<< /Length {} >>\nstream\n", content.len()).as_bytes());
    buf.extend_from_slice(content.as_bytes());
    buf.extend_from_slice(b"endstream\nendobj\n");

    // 6 — Info. `GTS_PDFXVersion` and a resolved `/Trapped` are X-1a mandates.
    obj_header(&mut buf, &mut offsets, 6);
    let info = format!(
        "<< /Producer {prod} /Creator {creat} /GTS_PDFXVersion (PDF/X-1a:2001) \
         /Trapped /False /CreationDate ({date}) /ModDate ({date}) >>\nendobj\n",
        prod = pdf_str(&format!("ForgeImages {ENGINE_VERSION}")),
        creat = pdf_str("ForgeImages Visual Production Compiler"),
        date = FIXED_DATE,
    );
    buf.extend_from_slice(info.as_bytes());

    // 7 — OutputIntent
    obj_header(&mut buf, &mut offsets, 7);
    let mut oi = format!(
        "<< /Type /OutputIntent /S /GTS_PDFX /OutputConditionIdentifier {oci} \
         /OutputCondition {oc} /RegistryName {reg}",
        oci = pdf_str(&intent.condition_identifier),
        oc = pdf_str(&intent.condition_info),
        reg = pdf_str(&intent.registry_name),
    );
    if embedded {
        oi.push_str(" /DestOutputProfile 8 0 R");
    }
    oi.push_str(" >>\nendobj\n");
    buf.extend_from_slice(oi.as_bytes());

    // 8 — DestOutputProfile ICC stream (only when embedded).
    if let Some(icc) = &intent.dest_output_profile {
        obj_header(&mut buf, &mut offsets, 8);
        buf.extend_from_slice(
            format!(
                "<< /N {} /Length {} >>\nstream\n",
                icc.components,
                icc.bytes.len()
            )
            .as_bytes(),
        );
        buf.extend_from_slice(&icc.bytes);
        buf.extend_from_slice(b"\nendstream\nendobj\n");
    }

    // Cross-reference table. Each entry is exactly 20 bytes.
    let xref_offset = buf.len();
    buf.extend_from_slice(format!("xref\n0 {}\n", n_objects + 1).as_bytes());
    buf.extend_from_slice(b"0000000000 65535 f \n");
    for off in &offsets {
        buf.extend_from_slice(format!("{off:010} {gen:05} n \n", gen = 0).as_bytes());
    }

    // Trailer. Both `/ID` strings are identical: this is the file's first
    // (and, for a deterministic compiler, only) generation.
    let trailer = format!(
        "trailer\n<< /Size {size} /Root 1 0 R /Info 6 0 R /ID [<{id}> <{id}>] >>\n\
         startxref\n{xoff}\n%%EOF\n",
        size = n_objects + 1,
        id = id_hex,
        xoff = xref_offset,
    );
    buf.extend_from_slice(trailer.as_bytes());

    Ok(buf)
}

/// Record an object's byte offset and write its `N 0 obj` header.
fn obj_header(buf: &mut Vec<u8>, offsets: &mut Vec<usize>, n: u32) {
    offsets.push(buf.len());
    buf.extend_from_slice(format!("{n} 0 obj\n").as_bytes());
}

/// Format a PDF real number: fixed 4-decimal rounding (deterministic, locale
/// independent), trailing zeros trimmed for compactness.
fn num(v: f64) -> String {
    if !v.is_finite() {
        return "0".to_string();
    }
    let mut s = format!("{v:.4}");
    if s.contains('.') {
        while s.ends_with('0') {
            s.pop();
        }
        if s.ends_with('.') {
            s.pop();
        }
    }
    if s == "-0" {
        s = "0".to_string();
    }
    s
}

/// Encode a PDF literal string, escaping the three characters that would
/// otherwise break out of the `( ... )` delimiters.
fn pdf_str(s: &str) -> String {
    let mut out = String::with_capacity(s.len() + 2);
    out.push('(');
    for c in s.chars() {
        match c {
            '(' | ')' | '\\' => {
                out.push('\\');
                out.push(c);
            }
            _ => out.push(c),
        }
    }
    out.push(')');
    out
}

#[cfg(test)]
mod tests {
    use super::*;

    fn gray_geo() -> PrintGeometry {
        // 1px == 1pt keeps the geometry assertions readable.
        PrintGeometry {
            dpi: 72,
            bleed_pts: 0.0,
        }
    }

    fn find(hay: &[u8], needle: &[u8]) -> bool {
        hay.windows(needle.len()).any(|w| w == needle)
    }

    /// Extract the hex of the first `/ID [<HEX> ...]` entry.
    fn id_of(pdf: &[u8]) -> Vec<u8> {
        let marker = b"/ID [<";
        let start = pdf
            .windows(marker.len())
            .position(|w| w == marker)
            .expect("file has an /ID")
            + marker.len();
        let end = start
            + pdf[start..]
                .iter()
                .position(|&c| c == b'>')
                .expect("/ID is terminated");
        pdf[start..end].to_vec()
    }

    /// A `fill`-valued sample buffer. Via a function so large fixtures stay on
    /// the heap rather than becoming multi-hundred-KB stack arrays.
    fn filled(fill: u8, n: usize) -> Vec<u8> {
        vec![fill; n]
    }

    #[test]
    fn gray_pdf_has_x1a_structure_and_geometry() {
        // 100x50 px at 72 dpi -> 100x50 pt.
        let samples = filled(0u8, 100 * 50);
        let pdf = write_pdf_x1a(
            100,
            50,
            &samples,
            DeviceColor::Gray,
            &gray_geo(),
            &OutputIntent::kdp_us_swop(),
        )
        .expect("gray pdf");

        assert!(pdf.starts_with(b"%PDF-1.3"), "must be a PDF 1.3 base");
        assert!(
            find(&pdf, b"/GTS_PDFXVersion (PDF/X-1a:2001)"),
            "must be labelled X-1a"
        );
        assert!(find(&pdf, b"/Subtype /Image"), "must contain an image");
        assert!(find(&pdf, b"/ColorSpace /DeviceGray"), "gray -> DeviceGray");
        assert!(find(&pdf, b"/BitsPerComponent 8"));
        assert!(find(&pdf, b"/MediaBox [0 0 100 50]"), "geometry: 100x50 pt");
        assert!(find(&pdf, b"/TrimBox"), "X-1a requires a TrimBox");
        assert!(find(&pdf, b"/OutputIntents [7 0 R]"));
        assert!(find(&pdf, b"/S /GTS_PDFX"));
        assert!(find(&pdf, b"/Trapped /False"));
        assert!(pdf.ends_with(b"%%EOF\n"));
        // No RGB anywhere — the whole point of X-1a.
        assert!(
            !find(&pdf, b"/DeviceRGB"),
            "an X-1a file must never carry RGB"
        );
    }

    #[test]
    fn dpi_scales_the_media_box() {
        // 600x300 px at 300 dpi -> 2x1 inch -> 144x72 pt.
        let samples = filled(0u8, 600 * 300);
        let pdf = write_pdf_x1a(
            600,
            300,
            &samples,
            DeviceColor::Gray,
            &PrintGeometry {
                dpi: 300,
                bleed_pts: 0.0,
            },
            &OutputIntent::kdp_us_swop(),
        )
        .unwrap();
        assert!(find(&pdf, b"/MediaBox [0 0 144 72]"), "300 dpi geometry");
    }

    #[test]
    fn trim_box_is_inset_by_bleed() {
        // 200x200 pt page, 10 pt bleed -> trim [10 10 190 190].
        let samples = filled(0u8, 200 * 200);
        let pdf = write_pdf_x1a(
            200,
            200,
            &samples,
            DeviceColor::Gray,
            &PrintGeometry {
                dpi: 72,
                bleed_pts: 10.0,
            },
            &OutputIntent::kdp_us_swop(),
        )
        .unwrap();
        assert!(
            find(&pdf, b"/TrimBox [10 10 190 190]"),
            "trim inset by 10 pt"
        );
        assert!(find(&pdf, b"/MediaBox [0 0 200 200]"));
    }

    #[test]
    fn samples_are_embedded_verbatim() {
        // Uncompressed: the exact sample bytes must appear in the file. This is
        // what makes the output a pure function of the input — and catches any
        // future "optimisation" that quietly re-encodes.
        let mut samples = filled(0u8, 4 * 4);
        samples[5] = 0x9A;
        samples[6] = 0xBC;
        samples[7] = 0xDE;
        let pdf = write_pdf_x1a(
            4,
            4,
            &samples,
            DeviceColor::Gray,
            &gray_geo(),
            &OutputIntent::kdp_us_swop(),
        )
        .unwrap();
        assert!(
            find(&pdf, &[0x9A, 0xBC, 0xDE]),
            "sample bytes must be stored verbatim"
        );
    }

    #[test]
    fn cmyk_uses_devicecmyk_and_four_samples() {
        // 2x2 CMYK = 16 bytes.
        let samples = filled(0u8, 2 * 2 * 4);
        let pdf = write_pdf_x1a(
            2,
            2,
            &samples,
            DeviceColor::Cmyk,
            &gray_geo(),
            &OutputIntent::kdp_us_swop(),
        )
        .unwrap();
        assert!(find(&pdf, b"/ColorSpace /DeviceCMYK"));
    }

    #[test]
    fn output_is_deterministic() {
        // Law 4: same inputs, byte-identical output.
        let samples = filled(7u8, 20 * 10);
        let a = write_pdf_x1a(
            20,
            10,
            &samples,
            DeviceColor::Gray,
            &gray_geo(),
            &OutputIntent::kdp_us_swop(),
        )
        .unwrap();
        let b = write_pdf_x1a(
            20,
            10,
            &samples,
            DeviceColor::Gray,
            &gray_geo(),
            &OutputIntent::kdp_us_swop(),
        )
        .unwrap();
        assert_eq!(a, b, "identical inputs must yield identical bytes");
    }

    #[test]
    fn different_pixels_change_the_id() {
        let geo = gray_geo();
        let intent = OutputIntent::kdp_us_swop();
        let a = write_pdf_x1a(4, 4, &filled(0u8, 16), DeviceColor::Gray, &geo, &intent).unwrap();
        let b = write_pdf_x1a(4, 4, &filled(1u8, 16), DeviceColor::Gray, &geo, &intent).unwrap();
        // The /ID is content-derived, so it — not just the image stream — must
        // differ. (Asserting the whole files differ would pass even for a fixed
        // ID, since the pixels already differ.)
        assert_ne!(
            id_of(&a),
            id_of(&b),
            "content-derived /ID must track the pixels"
        );
        assert_ne!(a, b, "distinct pixels must produce distinct files");
    }

    #[test]
    fn identical_inputs_share_the_id() {
        // The other half: the derived /ID is stable, not random.
        let geo = gray_geo();
        let intent = OutputIntent::kdp_us_swop();
        let a = write_pdf_x1a(4, 4, &filled(5u8, 16), DeviceColor::Gray, &geo, &intent).unwrap();
        let b = write_pdf_x1a(4, 4, &filled(5u8, 16), DeviceColor::Gray, &geo, &intent).unwrap();
        assert_eq!(id_of(&a), id_of(&b));
    }

    #[test]
    fn by_name_intent_has_no_dest_profile() {
        let pdf = write_pdf_x1a(
            4,
            4,
            &filled(0u8, 16),
            DeviceColor::Gray,
            &gray_geo(),
            &OutputIntent::kdp_us_swop(),
        )
        .unwrap();
        assert!(find(&pdf, b"/OutputConditionIdentifier (CGATS TR 001)"));
        assert!(
            !find(&pdf, b"/DestOutputProfile"),
            "the named default embeds no profile"
        );
    }

    #[test]
    fn embedded_profile_is_written() {
        let intent = OutputIntent {
            dest_output_profile: Some(IccProfile {
                bytes: b"FAKE-ICC-PROFILE".to_vec(),
                components: 4,
            }),
            ..OutputIntent::kdp_us_swop()
        };
        let pdf = write_pdf_x1a(
            4,
            4,
            &filled(0u8, 16),
            DeviceColor::Gray,
            &gray_geo(),
            &intent,
        )
        .unwrap();
        assert!(find(&pdf, b"/DestOutputProfile 8 0 R"));
        assert!(
            find(&pdf, b"FAKE-ICC-PROFILE"),
            "profile bytes embedded verbatim"
        );
        assert!(
            find(&pdf, b"/N 4"),
            "CMYK press profile declares 4 components"
        );
    }

    #[test]
    fn sample_length_mismatch_is_rejected() {
        let err = write_pdf_x1a(
            4,
            4,
            &filled(0u8, 10),
            DeviceColor::Gray,
            &gray_geo(),
            &OutputIntent::kdp_us_swop(),
        )
        .expect_err("wrong length must fail");
        assert!(matches!(err, PdfError::SampleLengthMismatch { .. }));
    }

    #[test]
    fn zero_dimension_and_zero_dpi_are_rejected() {
        assert!(matches!(
            write_pdf_x1a(
                0,
                4,
                &[],
                DeviceColor::Gray,
                &gray_geo(),
                &OutputIntent::kdp_us_swop()
            ),
            Err(PdfError::ZeroDimension { .. })
        ));
        assert!(matches!(
            write_pdf_x1a(
                4,
                4,
                &filled(0u8, 16),
                DeviceColor::Gray,
                &PrintGeometry {
                    dpi: 0,
                    bleed_pts: 0.0
                },
                &OutputIntent::kdp_us_swop()
            ),
            Err(PdfError::ZeroDpi)
        ));
    }

    #[test]
    fn invalid_output_profile_components_are_rejected() {
        let intent = OutputIntent {
            dest_output_profile: Some(IccProfile {
                bytes: filled(0u8, 8),
                components: 3,
            }),
            ..OutputIntent::kdp_us_swop()
        };
        let err = write_pdf_x1a(
            4,
            4,
            &filled(0u8, 16),
            DeviceColor::Gray,
            &gray_geo(),
            &intent,
        )
        .expect_err("an RGB (3-component) output intent is not X-1a");
        assert!(matches!(
            err,
            PdfError::ProfileComponentInvalid { declared: 3 }
        ));
    }

    #[test]
    fn num_formats_deterministically() {
        assert_eq!(num(935.04), "935.04");
        assert_eq!(num(666.0), "666");
        assert_eq!(num(9.0), "9");
        assert_eq!(num(15.36), "15.36");
        assert_eq!(num(-0.0), "0");
    }
}
