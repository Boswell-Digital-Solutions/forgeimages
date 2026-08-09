//! Dimension Match Rule — NEW for Cover Forge
//!
//! Validates that asset dimensions match expected values within tolerance.
//! Used for book covers where exact dimensions matter (trim + spine + bleed).

use crate::templates::Template;
use crate::validation::{AssetInput, ValidationRule, ValidationViolation, ViolationSeverity};

/// Validates exact pixel dimensions against expected values.
///
/// Unlike ResolutionRule (which checks minimums), this checks that dimensions
/// match a target within a tolerance, critical for print-ready covers.
pub struct DimensionMatchRule {
    /// Expected width in pixels
    pub expected_width: u32,
    /// Expected height in pixels
    pub expected_height: u32,
    /// Tolerance in pixels (default 2px for rounding)
    pub tolerance_px: u32,
}

impl DimensionMatchRule {
    pub fn new(expected_width: u32, expected_height: u32) -> Self {
        Self {
            expected_width,
            expected_height,
            tolerance_px: 2,
        }
    }

    pub fn with_tolerance(mut self, tolerance_px: u32) -> Self {
        self.tolerance_px = tolerance_px;
        self
    }
}

impl ValidationRule for DimensionMatchRule {
    fn name(&self) -> &'static str {
        "dimension_match"
    }

    fn validate(&self, input: &AssetInput, _template: &Template) -> Vec<ValidationViolation> {
        let mut violations = vec![];

        let w_diff = (input.width as i64 - self.expected_width as i64).unsigned_abs() as u32;
        let h_diff = (input.height as i64 - self.expected_height as i64).unsigned_abs() as u32;

        if w_diff > self.tolerance_px {
            violations.push(ValidationViolation {
                rule: self.name().to_string(),
                severity: ViolationSeverity::Error,
                message: "Width does not match expected dimensions".to_string(),
                expected: Some(format!(
                    "{}px (±{}px)",
                    self.expected_width, self.tolerance_px
                )),
                actual: Some(format!("{}px", input.width)),
                remediation: vec![format!("Resize to {}px width", self.expected_width)],
            });
        }

        if h_diff > self.tolerance_px {
            violations.push(ValidationViolation {
                rule: self.name().to_string(),
                severity: ViolationSeverity::Error,
                message: "Height does not match expected dimensions".to_string(),
                expected: Some(format!(
                    "{}px (±{}px)",
                    self.expected_height, self.tolerance_px
                )),
                actual: Some(format!("{}px", input.height)),
                remediation: vec![format!("Resize to {}px height", self.expected_height)],
            });
        }

        violations
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::templates::*;

    fn dummy_template() -> Template {
        Template {
            id: "test".to_string(),
            name: "Test".to_string(),
            description: "Test".to_string(),
            template_version: "1.0.0".to_string(),
            engine_min_version: "1.0.0".to_string(),
            deprecated: false,
            superseded_by: None,
            asset_class: AssetClass::Cover,
            aspect_ratio: [1, 1],
            canonical_size: [1024, 1024],
            vector_master: false,
            validation: ValidationConfig::default(),
            exports: vec![],
        }
    }

    #[test]
    fn test_exact_match() {
        let rule = DimensionMatchRule::new(3896, 2775);
        let input = AssetInput {
            width: 3896,
            height: 2775,
            color_count: None,
            format: None,
        };
        assert!(rule.validate(&input, &dummy_template()).is_empty());
    }

    #[test]
    fn test_within_tolerance() {
        let rule = DimensionMatchRule::new(3896, 2775).with_tolerance(5);
        let input = AssetInput {
            width: 3893,
            height: 2778,
            color_count: None,
            format: None,
        };
        assert!(rule.validate(&input, &dummy_template()).is_empty());
    }

    #[test]
    fn test_outside_tolerance() {
        let rule = DimensionMatchRule::new(3896, 2775).with_tolerance(2);
        let input = AssetInput {
            width: 3800,
            height: 2775,
            color_count: None,
            format: None,
        };
        let v = rule.validate(&input, &dummy_template());
        assert_eq!(v.len(), 1);
        assert_eq!(v[0].severity, ViolationSeverity::Error);
    }
}
