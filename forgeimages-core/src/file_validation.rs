//! File-Based Validation
//!
//! Reads image metadata from actual file headers using the `image` crate,
//! then delegates to the existing metadata-based Validator.
//!
//! This bridges the gap between:
//! - Agent/bridge path: JSON metadata (AssetInput) — stateless, fast, over HTTP
//! - Desktop/Tauri path: File path — reads actual DPI, dimensions, format from disk

use crate::validation::AssetInput;
use image::ImageReader;
use std::path::Path;

/// Read image metadata from a file and return an AssetInput suitable for validation.
///
/// This is the Tauri entry point: authors upload a JPEG/PNG and ForgeImages reads
/// its actual dimensions, format, and color info — no reliance on declared metadata.
pub fn validate_from_file(path: &Path) -> Result<AssetInput, FileValidationError> {
    if !path.exists() {
        return Err(FileValidationError::FileNotFound(
            path.display().to_string(),
        ));
    }

    let reader = ImageReader::open(path)
        .map_err(|e| FileValidationError::ReadError(format!("{}: {}", path.display(), e)))?;

    let format = reader.format().map(|f| format!("{:?}", f).to_lowercase());

    let img = reader
        .decode()
        .map_err(|e| FileValidationError::DecodeError(format!("{}: {}", path.display(), e)))?;

    let (width, height) = (img.width(), img.height());

    Ok(AssetInput {
        width,
        height,
        color_count: None, // Color counting requires palette analysis — future enhancement
        format,
    })
}

#[derive(Debug, thiserror::Error)]
pub enum FileValidationError {
    #[error("File not found: {0}")]
    FileNotFound(String),

    #[error("Failed to read image: {0}")]
    ReadError(String),

    #[error("Failed to decode image: {0}")]
    DecodeError(String),
}
