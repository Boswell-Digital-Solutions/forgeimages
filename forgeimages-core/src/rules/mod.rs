//! Validation Rules
//!
//! Each rule category lives in its own submodule.
//! The existing 3 rules (aspect_ratio, resolution, color_count) are preserved
//! and re-exported here. New rules for Cover Forge are added alongside them.

pub mod aspect_ratio;
pub mod color_count;
pub mod color_space;
pub mod dimensions;
pub mod file_size;
pub mod resolution;

pub use aspect_ratio::AspectRatioRule;
pub use color_count::ColorCountRule as ColorCountCheckRule;
pub use color_space::ColorSpaceRule;
pub use dimensions::DimensionMatchRule;
pub use file_size::FileSizeRule;
pub use resolution::ResolutionRule as ResolutionCheckRule;
