//! Color Space Rule — NEW for Cover Forge
//!
//! Validates that the asset's color space matches requirements.
//! Print assets should be CMYK; ebook assets should be RGB.
//!
//! Note: ForgeImages VALIDATES color space — it does NOT convert.
//! Color conversion is Cover Forge's responsibility (GAP-11 decision).

use crate::templates::Template;
use crate::validation::{AssetInput, ValidationRule, ValidationViolation, ViolationSeverity};

/// Validates that the declared color space matches the expected value.
///
/// Uses the `format` field on AssetInput to detect color space hints.
/// For full file-based inspection, the file_validation module extracts
/// actual color space from file headers before calling this rule.
pub struct ColorSpaceRule {
    /// Expected color space string (e.g., "cmyk", "rgb")
    pub expected: String,
    /// Whether this is a blocking requirement or advisory
    pub blocking: bool,
}

impl ColorSpaceRule {
    pub fn cmyk_required() -> Self {
        Self {
            expected: "cmyk".to_string(),
            blocking: false, // Warning for now — Cover Forge can convert
        }
    }

    pub fn rgb_required() -> Self {
        Self {
            expected: "rgb".to_string(),
            blocking: false,
        }
    }
}

impl ValidationRule for ColorSpaceRule {
    fn name(&self) -> &'static str {
        "color_space"
    }

    fn validate(&self, input: &AssetInput, _template: &Template) -> Vec<ValidationViolation> {
        // Only check if format/color info is provided
        let Some(ref format) = input.format else {
            return vec![];
        };

        let format_lower = format.to_lowercase();

        // Simple heuristic: check if the format string contains a color space indicator
        let detected_space = if format_lower.contains("cmyk") {
            "cmyk"
        } else if format_lower.contains("rgb")
            || format_lower.contains("png")
            || format_lower.contains("jpeg")
        {
            "rgb"
        } else {
            return vec![]; // Can't determine, skip
        };

        if detected_space != self.expected {
            let severity = if self.blocking {
                ViolationSeverity::Error
            } else {
                ViolationSeverity::Warning
            };

            vec![ValidationViolation {
                rule: self.name().to_string(),
                severity,
                message: format!("Color space mismatch: expected {}", self.expected),
                expected: Some(self.expected.clone()),
                actual: Some(detected_space.to_string()),
                remediation: vec![format!(
                    "Convert to {} color space before submission",
                    self.expected.to_uppercase()
                )],
            }]
        } else {
            vec![]
        }
    }
}
