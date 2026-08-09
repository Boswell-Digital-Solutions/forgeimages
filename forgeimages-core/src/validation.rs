//! Validation System - Rule/Policy Separation
//!
//! Rules produce structured violations.
//! Policy maps violations to actions.

use crate::templates::{FailureMode, Template};
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "snake_case")]
pub enum ViolationSeverity {
    Error,
    Warning,
    Info,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ValidationViolation {
    pub rule: String,
    pub severity: ViolationSeverity,
    pub message: String,
    pub expected: Option<String>,
    pub actual: Option<String>,
    pub remediation: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ValidationResult {
    pub valid: bool,
    pub violations: Vec<ValidationViolation>,
    pub template_id: String,
    pub template_version: String,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub asset_digest: Option<String>,
}

impl ValidationResult {
    pub fn success(template: &Template) -> Self {
        Self {
            valid: true,
            violations: vec![],
            template_id: template.id.clone(),
            template_version: template.template_version.clone(),
            asset_digest: None,
        }
    }

    pub fn failure(template: &Template, violations: Vec<ValidationViolation>) -> Self {
        Self {
            valid: false,
            violations,
            template_id: template.id.clone(),
            template_version: template.template_version.clone(),
            asset_digest: None,
        }
    }

    pub fn has_errors(&self) -> bool {
        self.violations
            .iter()
            .any(|v| v.severity == ViolationSeverity::Error)
    }
}

/// Validation rule trait - produces violations
pub trait ValidationRule {
    fn name(&self) -> &'static str;
    fn validate(&self, input: &AssetInput, template: &Template) -> Vec<ValidationViolation>;
}

/// Input for validation
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AssetInput {
    pub width: u32,
    pub height: u32,
    #[serde(default)]
    pub color_count: Option<u32>,
    #[serde(default)]
    pub format: Option<String>,
}

// --- Concrete Rules ---

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
                message: format!("Aspect ratio mismatch"),
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

pub struct ResolutionRule;

impl ValidationRule for ResolutionRule {
    fn name(&self) -> &'static str {
        "resolution"
    }

    fn validate(&self, input: &AssetInput, template: &Template) -> Vec<ValidationViolation> {
        if !template.validation.rules.resolution.enabled {
            return vec![];
        }

        let mut violations = vec![];
        let min_w = template.validation.rules.resolution.min_width;
        let min_h = template.validation.rules.resolution.min_height;

        if input.width < min_w || input.height < min_h {
            violations.push(ValidationViolation {
                rule: self.name().to_string(),
                severity: ViolationSeverity::Error,
                message: "Resolution too low".to_string(),
                expected: Some(format!("{}x{} minimum", min_w, min_h)),
                actual: Some(format!("{}x{}", input.width, input.height)),
                remediation: vec!["Provide higher resolution source image".to_string()],
            });
        }

        violations
    }
}

pub struct ColorCountRule;

impl ValidationRule for ColorCountRule {
    fn name(&self) -> &'static str {
        "color_count"
    }

    fn validate(&self, input: &AssetInput, template: &Template) -> Vec<ValidationViolation> {
        if !template.validation.rules.color_count.enabled {
            return vec![];
        }

        if let Some(count) = input.color_count {
            let max = template.validation.rules.color_count.max;
            if count > max {
                return vec![ValidationViolation {
                    rule: self.name().to_string(),
                    severity: ViolationSeverity::Warning,
                    message: "Too many colors for clean icon".to_string(),
                    expected: Some(format!("{} colors max", max)),
                    actual: Some(format!("{} colors", count)),
                    remediation: vec!["Reduce color palette".to_string()],
                }];
            }
        }
        vec![]
    }
}

/// Validator orchestrates rules and applies policy
pub struct Validator {
    rules: Vec<Box<dyn ValidationRule + Send + Sync>>,
}

impl Validator {
    pub fn new() -> Self {
        Self {
            rules: vec![
                Box::new(AspectRatioRule),
                Box::new(ResolutionRule),
                Box::new(ColorCountRule),
            ],
        }
    }

    /// Add a rule dynamically (used for parameterized cover templates)
    pub fn add_rule(&mut self, rule: Box<dyn ValidationRule + Send + Sync>) {
        self.rules.push(rule);
    }

    pub fn validate(&self, input: &AssetInput, template: &Template) -> ValidationResult {
        let mut all_violations = vec![];

        for rule in &self.rules {
            let violations = rule.validate(input, template);
            all_violations.extend(violations);
        }

        // Apply failure mode policy
        let has_errors = all_violations
            .iter()
            .any(|v| v.severity == ViolationSeverity::Error);

        match template.validation.failure_mode {
            FailureMode::Block if has_errors => ValidationResult::failure(template, all_violations),
            FailureMode::Block => {
                // Warnings don't block
                let errors: Vec<_> = all_violations
                    .into_iter()
                    .filter(|v| v.severity == ViolationSeverity::Error)
                    .collect();
                if errors.is_empty() {
                    ValidationResult::success(template)
                } else {
                    ValidationResult::failure(template, errors)
                }
            }
            FailureMode::Warn | FailureMode::Log => {
                // Never block, just record
                ValidationResult {
                    valid: true,
                    violations: all_violations,
                    template_id: template.id.clone(),
                    template_version: template.template_version.clone(),
                    asset_digest: None,
                }
            }
        }
    }
}

impl Default for Validator {
    fn default() -> Self {
        Self::new()
    }
}
