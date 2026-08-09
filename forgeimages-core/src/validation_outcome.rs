//! Validation Outcome
//!
//! Classifies what an asset is ALLOWED TO DO after validation.
//!
//! NOTE: This is orthogonal to PrintAuthority (print.rs), which determines
//! WHERE print specifications come from (System | Template | User).
//! ValidationOutcome determines the PERMISSION LEVEL of the validated asset.

use crate::validation::ValidationResult;
use serde::{Deserialize, Serialize};

/// The permission level / clearance of a validated asset.
///
/// Derived from ValidationResult by examining violation severities and categories.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum ValidationOutcome {
    /// Asset passes all rules — suitable for digital display only (no print checks run)
    ScreenOnly,
    /// Asset passes all print-readiness rules — cleared for production
    PrintReady,
    /// Asset passes with warnings — print is possible but has advisory notices
    PrintAdvisory,
    /// Asset is in draft state — incomplete validation or missing required fields
    Draft,
    /// Asset fails one or more blocking rules — cannot proceed
    Rejected,
}

impl ValidationOutcome {
    /// Derive outcome from a ValidationResult.
    ///
    /// Logic:
    /// - If validation failed (has errors): Rejected
    /// - If validation passed with no violations: PrintReady (if print rules ran) or ScreenOnly
    /// - If validation passed with warnings: PrintAdvisory
    pub fn from_result(result: &ValidationResult, print_rules_ran: bool) -> Self {
        if !result.valid {
            return Self::Rejected;
        }

        let has_warnings = !result.violations.is_empty();

        if has_warnings {
            Self::PrintAdvisory
        } else if print_rules_ran {
            Self::PrintReady
        } else {
            Self::ScreenOnly
        }
    }

    /// Whether the asset can be used (not rejected)
    pub fn is_usable(&self) -> bool {
        !matches!(self, Self::Rejected)
    }

    /// Whether the asset is cleared for print production
    pub fn is_print_ready(&self) -> bool {
        matches!(self, Self::PrintReady)
    }
}
