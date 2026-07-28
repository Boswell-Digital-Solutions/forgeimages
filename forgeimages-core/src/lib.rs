//! ForgeImages Core - Visual Production Compiler
//!
//! # The Six Laws (Non-Negotiable)
//! 1. SVG Is Truth
//! 2. Templates Are Contracts
//! 3. Validation Is Protective
//! 4. Deterministic Output
//! 5. Manifests Enable Reproduction
//! 6. Agents Suggest, Engine Enforces

pub mod templates;
pub mod validation;
pub mod hashing;
pub mod print;
pub mod pipeline;
pub mod rules;
pub mod file_validation;
pub mod validation_outcome;
pub mod cover_params;
pub mod source_master;
pub mod pdf;

pub use templates::{Template, TemplateId, ExportSpec, AssetClass};
pub use validation::{ValidationResult, ValidationRule, ValidationViolation, ViolationSeverity};
pub use hashing::{compute_manifest_hash, compute_job_hash, canonical_json, SourceType, AssetManifest};
pub use print::PrintAuthority;
pub use pipeline::{CompilationPipeline, CompiledAsset, CompileRequest, PipelineError};
pub use validation_outcome::ValidationOutcome;
pub use file_validation::{validate_from_file, FileValidationError};
pub use cover_params::{CoverTemplateParams, ResolvedCoverDimensions, PaperStock};
pub use source_master::{SourceMaster, SourceMasterError, SourceMasterKind};
pub use pdf::{write_pdf_x1a, DeviceColor, IccProfile, OutputIntent, PdfError, PrintGeometry};

pub const ENGINE_VERSION: &str = env!("CARGO_PKG_VERSION");
pub const MIN_TEMPLATE_VERSION: &str = "1.0.0";
