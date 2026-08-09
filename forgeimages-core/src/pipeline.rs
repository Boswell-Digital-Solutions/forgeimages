//! Compilation Pipeline - Single Entry Point
//!
//! CRITICAL: compile_asset MUST call validate internally. No bypass.

use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use thiserror::Error;
use uuid::Uuid;

use crate::ENGINE_VERSION;
use crate::hashing::{compute_job_hash, compute_manifest_hash};
use crate::templates::{ExportSpec, Template, TemplateRegistry};
use crate::validation::{AssetInput, ValidationResult, Validator};

#[cfg(feature = "test-hooks")]
use std::sync::atomic::{AtomicU32, Ordering};

#[cfg(feature = "test-hooks")]
static VALIDATION_CALL_COUNT: AtomicU32 = AtomicU32::new(0);

#[cfg(feature = "test-hooks")]
pub fn get_validation_call_count() -> u32 {
    VALIDATION_CALL_COUNT.load(Ordering::SeqCst)
}

#[cfg(feature = "test-hooks")]
pub fn reset_validation_call_count() {
    VALIDATION_CALL_COUNT.store(0, Ordering::SeqCst);
}

#[derive(Debug, Error)]
pub enum PipelineError {
    #[error("Template not found: {0}")]
    TemplateNotFound(String),

    #[error("Validation failed: {0}")]
    ValidationFailed(String),

    #[error("Template version {0} requires engine >= {1}, current is {2}")]
    EngineVersionMismatch(String, String, String),

    #[error("Compilation error: {0}")]
    CompilationError(String),

    #[error("Serialization error: {0}")]
    SerializationError(#[from] serde_json::Error),

    /// A master was supplied and could not be honoured.
    ///
    /// Separate from `CompilationError` because it is never a partial outcome:
    /// the compile is refused outright rather than completing with placeholder
    /// exports that misrepresent the caller's master.
    #[error("Source master rejected: {0}")]
    SourceMasterRejected(#[from] crate::source_master::SourceMasterError),
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CompileRequest {
    pub template_id: String,
    pub asset_input: AssetInput,
    #[serde(default)]
    pub source_data: Option<String>, // Base64 encoded source
    #[serde(default)]
    pub seed: Option<u64>,
    #[serde(default)]
    pub prompt: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CompiledAsset {
    pub id: String,
    pub template_id: String,
    pub template_version: String,
    pub engine_version: String,
    pub created_at: DateTime<Utc>,
    pub manifest_hash: String,
    pub job_hash: String,
    pub validation: ValidationResult,
    pub exports: Vec<ExportedFile>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ExportedFile {
    pub id: String,
    pub filename: String,
    pub format: String,
    pub size: [u32; 2],
    pub data_base64: String,
    pub hash: String,
}

/// The compilation pipeline - single entry point for all asset operations
pub struct CompilationPipeline {
    registry: TemplateRegistry,
    validator: Validator,
}

impl CompilationPipeline {
    pub fn new(registry: TemplateRegistry) -> Self {
        Self {
            registry,
            validator: Validator::new(),
        }
    }

    /// List all available templates
    pub fn list_templates(&self) -> Vec<&Template> {
        self.registry.list()
    }

    /// Get a specific template
    pub fn get_template(&self, id: &str) -> Option<&Template> {
        self.registry.get(id)
    }

    /// Validate an asset against a template
    ///
    /// This is the ONLY validation entry point.
    pub fn validate_asset(
        &self,
        template_id: &str,
        input: &AssetInput,
    ) -> Result<ValidationResult, PipelineError> {
        #[cfg(feature = "test-hooks")]
        VALIDATION_CALL_COUNT.fetch_add(1, Ordering::SeqCst);

        let template = self
            .registry
            .get(template_id)
            .ok_or_else(|| PipelineError::TemplateNotFound(template_id.to_string()))?;

        // Check engine version compatibility
        self.check_engine_version(template)?;

        Ok(self.validator.validate(input, template))
    }

    /// Compile an asset
    ///
    /// CRITICAL: This ALWAYS calls validate_asset internally. No bypass possible.
    pub fn compile_asset(&self, request: &CompileRequest) -> Result<CompiledAsset, PipelineError> {
        let template = self
            .registry
            .get(&request.template_id)
            .ok_or_else(|| PipelineError::TemplateNotFound(request.template_id.clone()))?;

        // MANDATORY: Validation is always called. This is non-negotiable.
        let validation = self.validate_asset(&request.template_id, &request.asset_input)?;

        // If validation failed with errors, reject compilation
        if !validation.valid {
            let messages: Vec<_> = validation
                .violations
                .iter()
                .map(|v| format!("{}: {}", v.rule, v.message))
                .collect();
            return Err(PipelineError::ValidationFailed(messages.join("; ")));
        }

        // Ingest the caller's master, if one was supplied.
        //
        // This runs after validation (so a malformed asset is still reported as
        // a validation failure first) but before any export is produced, so an
        // inadmissible master costs nothing and is attributed precisely.
        let master = match request.source_data.as_deref() {
            Some(data) => {
                let decoded = crate::source_master::decode(data)?;
                crate::source_master::check_admissible(
                    &decoded,
                    template.vector_master,
                    (request.asset_input.width, request.asset_input.height),
                )?;
                Some(decoded)
            }
            None => None,
        };

        // Generate exports (placeholder only when no master was supplied)
        let exports = self.generate_exports(template, request, master.as_ref())?;

        // Build manifest
        let asset_id = Uuid::new_v4().to_string();
        let created_at = Utc::now();

        let job_hash = compute_job_hash(
            &request.template_id,
            &template.template_version,
            request,
            ENGINE_VERSION,
        )?;

        let mut asset = CompiledAsset {
            id: asset_id,
            template_id: request.template_id.clone(),
            template_version: template.template_version.clone(),
            engine_version: ENGINE_VERSION.to_string(),
            created_at,
            manifest_hash: String::new(), // Computed after
            job_hash,
            validation,
            exports,
        };

        // Compute manifest hash (includes everything)
        asset.manifest_hash = compute_manifest_hash(&asset)?;

        Ok(asset)
    }

    fn check_engine_version(&self, template: &Template) -> Result<(), PipelineError> {
        let engine_ver = semver::Version::parse(ENGINE_VERSION)
            .map_err(|_| PipelineError::CompilationError("Invalid engine version".into()))?;
        let min_ver = semver::Version::parse(&template.engine_min_version)
            .map_err(|_| PipelineError::CompilationError("Invalid template min version".into()))?;

        if engine_ver < min_ver {
            return Err(PipelineError::EngineVersionMismatch(
                template.template_version.clone(),
                template.engine_min_version.clone(),
                ENGINE_VERSION.to_string(),
            ));
        }

        Ok(())
    }

    fn generate_exports(
        &self,
        template: &Template,
        request: &CompileRequest,
        master: Option<&crate::source_master::SourceMaster>,
    ) -> Result<Vec<ExportedFile>, PipelineError> {
        let mut exports = vec![];

        for spec in &template.exports {
            let data = self.render_export(spec, request, master)?;
            let hash = crate::hashing::sha256_hex(&data);

            exports.push(ExportedFile {
                id: spec.id.clone(),
                filename: format!("{}.{}", spec.id, format_extension(&spec.format)),
                format: format!("{:?}", spec.format).to_lowercase(),
                size: spec.size,
                data_base64: base64::Engine::encode(
                    &base64::engine::general_purpose::STANDARD,
                    &data,
                ),
                hash,
            });
        }

        Ok(exports)
    }

    fn render_export(
        &self,
        spec: &ExportSpec,
        _request: &CompileRequest,
        master: Option<&crate::source_master::SourceMaster>,
    ) -> Result<Vec<u8>, PipelineError> {
        // A supplied master is authoritative. If it cannot produce this export,
        // the compile fails — it does NOT fall through to the placeholder below.
        // Falling through is what made `source_data` a no-op: the caller got an
        // asset unrelated to their master, with a job hash asserting otherwise.
        if let Some(master) = master {
            return Ok(crate::source_master::render_export(
                master,
                &spec.id,
                spec.format.clone(),
                spec.size,
            )?);
        }

        // No master supplied — unchanged legacy behaviour.
        //
        // These are placeholders, not renders: an empty <svg> and a 1x1 PNG.
        // Note that `book-cover-kdp` marks a PDF/X-1a export `required`, so this
        // branch will hand back b"placeholder" for a file described as
        // print-ready. That predates this change and is left alone here rather
        // than silently widened; it is tracked as unimplemented rendering.
        match spec.format {
            crate::templates::ExportFormat::Svg => Ok(format!(
                r#"<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {} {}"></svg>"#,
                spec.size[0], spec.size[1]
            )
            .into_bytes()),
            crate::templates::ExportFormat::Png => {
                // Minimal 1x1 transparent PNG
                Ok(vec![
                    0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A, 0x00, 0x00, 0x00, 0x0D, 0x49,
                    0x48, 0x44, 0x52, 0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x01, 0x08, 0x06,
                    0x00, 0x00, 0x00, 0x1F, 0x15, 0xC4, 0x89, 0x00, 0x00, 0x00, 0x0A, 0x49, 0x44,
                    0x41, 0x54, 0x78, 0x9C, 0x63, 0x00, 0x01, 0x00, 0x00, 0x05, 0x00, 0x01, 0x0D,
                    0x0A, 0x2D, 0xB4, 0x00, 0x00, 0x00, 0x00, 0x49, 0x45, 0x4E, 0x44, 0xAE, 0x42,
                    0x60, 0x82,
                ])
            }
            _ => Ok(b"placeholder".to_vec()),
        }
    }
}

fn format_extension(format: &crate::templates::ExportFormat) -> &'static str {
    match format {
        crate::templates::ExportFormat::Svg => "svg",
        crate::templates::ExportFormat::Png => "png",
        crate::templates::ExportFormat::Ico => "ico",
        crate::templates::ExportFormat::Pdf => "pdf",
        crate::templates::ExportFormat::Jpg => "jpg",
    }
}

impl Default for CompilationPipeline {
    fn default() -> Self {
        Self::new(TemplateRegistry::default())
    }
}
