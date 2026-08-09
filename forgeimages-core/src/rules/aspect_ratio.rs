//! Aspect Ratio Rule — extracted from validation.rs
//!
//! Checks that the asset's aspect ratio matches the template within tolerance.

use crate::templates::Template;
use crate::validation::{AssetInput, ValidationRule, ValidationViolation, ViolationSeverity};

pub struct AspectRatioRule;

impl ValidationRule for AspectRatioRule {
    fn name(&self) -> &'static str {
        "aspect_ratio"
    }

    fn validate(&self, input: &AssetInput, template: &Template) -> Vec<ValidationViolation> {
        if !template.validation.rules.aspect_ratio.enabled {
            return vec![];
        }

        let expected = template.aspect_ratio[0] as f64 / template.aspect_ratio[1] as f64;
        let actual = input.width as f64 / input.height as f64;
        let tolerance = template.validation.rules.aspect_ratio.tolerance;

        if (expected - actual).abs() > tolerance {
            vec![ValidationViolation {
                rule: self.name().to_string(),
                severity: ViolationSeverity::Error,
                message: "Aspect ratio mismatch".to_string(),
                expected: Some(format!(
                    "{}:{}",
                    template.aspect_ratio[0], template.aspect_ratio[1]
                )),
                actual: Some(format!("{:.3}", actual)),
                remediation: vec!["Crop or resize to match template aspect ratio".to_string()],
            }]
        } else {
            vec![]
        }
    }
}
