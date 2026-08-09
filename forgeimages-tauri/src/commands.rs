//! Tauri IPC commands for ForgeImages
//!
//! Three commands exposed to the frontend:
//! - forgeimages_list_templates: Returns available templates
//! - forgeimages_validate_file: File-based validation (reads metadata from actual file)
//! - forgeimages_validate_metadata: Metadata-based validation (JSON input, like bridge path)

use forgeimages_core::file_validation::validate_from_file;
use forgeimages_core::pipeline::CompilationPipeline;
use forgeimages_core::templates::TemplateRegistry;
use forgeimages_core::validation::AssetInput;
use serde::Serialize;

use std::path::PathBuf;
use std::sync::Mutex;

/// Managed state for the ForgeImages pipeline
pub struct ForgeImagesState {
    pub pipeline: Mutex<CompilationPipeline>,
}

#[derive(Debug, Serialize)]
pub struct TemplateInfo {
    pub id: String,
    pub name: String,
    pub version: String,
    pub asset_class: String,
    pub deprecated: bool,
}

#[tauri::command]
pub fn forgeimages_list_templates(
    state: tauri::State<'_, ForgeImagesState>,
) -> Result<Vec<TemplateInfo>, String> {
    let guard = state
        .inner()
        .pipeline
        .lock()
        .map_err(|_| "Lock poisoned".to_string())?;
    let templates: Vec<TemplateInfo> = guard
        .list_templates()
        .iter()
        .map(|t| TemplateInfo {
            id: t.id.clone(),
            name: t.name.clone(),
            version: t.template_version.clone(),
            asset_class: format!("{:?}", t.asset_class).to_lowercase(),
            deprecated: t.deprecated,
        })
        .collect();
    Ok(templates)
}

#[tauri::command]
pub fn forgeimages_validate_file(
    state: tauri::State<'_, ForgeImagesState>,
    asset_path: String,
    template_id: String,
) -> Result<forgeimages_core::ValidationResult, String> {
    let guard = state
        .inner()
        .pipeline
        .lock()
        .map_err(|_| "Lock poisoned".to_string())?;
    let path = PathBuf::from(&asset_path);

    let input = validate_from_file(&path).map_err(|e| format!("{}", e))?;
    guard
        .validate_asset(&template_id, &input)
        .map_err(|e| format!("{}", e))
}

#[tauri::command]
pub fn forgeimages_validate_metadata(
    state: tauri::State<'_, ForgeImagesState>,
    input: AssetInput,
    template_id: String,
) -> Result<forgeimages_core::ValidationResult, String> {
    let guard = state
        .inner()
        .pipeline
        .lock()
        .map_err(|_| "Lock poisoned".to_string())?;
    guard
        .validate_asset(&template_id, &input)
        .map_err(|e| format!("{}", e))
}

/// Initialize ForgeImages state with templates loaded from a directory
pub fn init_state(templates_dir: PathBuf) -> ForgeImagesState {
    let registry =
        TemplateRegistry::load_from_dir(&templates_dir).unwrap_or_else(|_| TemplateRegistry::new());
    ForgeImagesState {
        pipeline: Mutex::new(CompilationPipeline::new(registry)),
    }
}
