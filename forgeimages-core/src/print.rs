//! Print Authority System
//!
//! Defines the source of print specifications to prevent conditional sprawl.

use serde::{Deserialize, Serialize};

/// PrintAuthority determines where print specifications come from.
/// This prevents if/else sprawl throughout the codebase.
#[derive(Debug, Clone, Copy, Default, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum PrintAuthority {
    /// System defaults (fallback)
    #[default]
    System,
    /// Template-defined specifications
    Template,
    /// User-provided overrides (with validation)
    User,
}

/// Print specifications for physical output
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PrintSpec {
    pub authority: PrintAuthority,
    pub dpi: u32,
    pub color_space: ColorSpace,
    pub bleed_inches: f64,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "UPPERCASE")]
pub enum ColorSpace {
    Rgb,
    Cmyk,
    Grayscale,
}

impl Default for PrintSpec {
    fn default() -> Self {
        Self {
            authority: PrintAuthority::System,
            dpi: 300,
            color_space: ColorSpace::Rgb,
            bleed_inches: 0.125,
        }
    }
}

impl PrintSpec {
    /// Create from template authority
    pub fn from_template(dpi: u32, color_space: ColorSpace, bleed: f64) -> Self {
        Self {
            authority: PrintAuthority::Template,
            dpi,
            color_space,
            bleed_inches: bleed,
        }
    }

    /// Create from user with validation
    pub fn from_user(dpi: u32, color_space: ColorSpace, bleed: f64) -> Result<Self, &'static str> {
        if !(72..=1200).contains(&dpi) {
            return Err("DPI must be between 72 and 1200");
        }
        if !(0.0..=1.0).contains(&bleed) {
            return Err("Bleed must be between 0 and 1 inch");
        }
        Ok(Self {
            authority: PrintAuthority::User,
            dpi,
            color_space,
            bleed_inches: bleed,
        })
    }
}
