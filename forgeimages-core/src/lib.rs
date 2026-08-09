//! ForgeImages Core - Visual Production Compiler
//!
//! # The Six Laws (Non-Negotiable)
//! 1. SVG Is Truth
//! 2. Templates Are Contracts
//! 3. Validation Is Protective
//! 4. Deterministic Output
//! 5. Manifests Enable Reproduction
//! 6. Agents Suggest, Engine Enforces

pub mod cover_params;
pub mod file_validation;
pub mod hashing;
pub mod pdf;
pub mod pipeline;
pub mod print;
pub mod rules;
pub mod source_master;
pub mod templates;
pub mod validation;
pub mod validation_outcome;

pub use cover_params::{CoverTemplateParams, PaperStock, ResolvedCoverDimensions};
pub use file_validation::{FileValidationError, validate_from_file};
pub use hashing::{
    AssetManifest, SourceType, canonical_json, compute_job_hash, compute_manifest_hash,
};
pub use pdf::{DeviceColor, IccProfile, OutputIntent, PdfError, PrintGeometry, write_pdf_x1a};
pub use pipeline::{CompilationPipeline, CompileRequest, CompiledAsset, PipelineError};
pub use print::PrintAuthority;
pub use source_master::{SourceMaster, SourceMasterError, SourceMasterKind};
pub use templates::{AssetClass, ExportSpec, Template, TemplateId};
pub use validation::{ValidationResult, ValidationRule, ValidationViolation, ViolationSeverity};
pub use validation_outcome::ValidationOutcome;

pub const ENGINE_VERSION: &str = env!("CARGO_PKG_VERSION");
pub const MIN_TEMPLATE_VERSION: &str = "1.0.0";
