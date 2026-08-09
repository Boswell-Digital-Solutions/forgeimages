//! Template System - Enforceable Contracts

use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::fs;
use std::path::Path;

pub type TemplateId = String;

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct Template {
    pub id: TemplateId,
    pub name: String,
    pub description: String,
    pub template_version: String,
    pub engine_min_version: String,
    #[serde(default)]
    pub deprecated: bool,
    #[serde(default)]
    pub superseded_by: Option<String>,
    pub asset_class: AssetClass,
    pub aspect_ratio: [u32; 2],
    pub canonical_size: [u32; 2],
    #[serde(default = "default_true")]
    pub vector_master: bool,
    #[serde(default)]
    pub validation: ValidationConfig,
    #[serde(default)]
    pub exports: Vec<ExportSpec>,
}

fn default_true() -> bool {
    true
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "lowercase")]
pub enum AssetClass {
    Icon,
    Cover,
    Banner,
    Logo,
    // Phase 1 additions for AuthorForge integration
    Map,
    Panel,
    #[serde(rename = "character_portrait")]
    CharacterPortrait,
    #[serde(rename = "scene_illustration")]
    SceneIllustration,
    #[serde(rename = "marketing_social")]
    MarketingSocial,
}

#[derive(Debug, Clone, Default, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct ValidationConfig {
    #[serde(default = "default_true")]
    pub required: bool,
    #[serde(default)]
    pub failure_mode: FailureMode,
    #[serde(default)]
    pub rules: ValidationRules,
}

#[derive(Debug, Clone, Default, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "lowercase")]
pub enum FailureMode {
    #[default]
    Block,
    Warn,
    Log,
}

#[derive(Debug, Clone, Default, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct ValidationRules {
    #[serde(default)]
    pub aspect_ratio: RuleConfig,
    #[serde(default)]
    pub resolution: ResolutionRule,
    #[serde(default)]
    pub color_count: ColorCountRule,
}

#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct RuleConfig {
    #[serde(default = "default_true")]
    pub enabled: bool,
    #[serde(default = "default_tolerance")]
    pub tolerance: f64,
}

fn default_tolerance() -> f64 {
    0.01
}

#[derive(Debug, Clone, Default, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct ResolutionRule {
    #[serde(default = "default_true")]
    pub enabled: bool,
    #[serde(default = "default_min_width")]
    pub min_width: u32,
    #[serde(default = "default_min_height")]
    pub min_height: u32,
}

fn default_min_width() -> u32 {
    1024
}
fn default_min_height() -> u32 {
    1024
}

#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct ColorCountRule {
    #[serde(default)]
    pub enabled: bool,
    #[serde(default = "default_max_colors")]
    pub max: u32,
}

fn default_max_colors() -> u32 {
    16
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct ExportSpec {
    pub id: String,
    pub description: String,
    pub size: [u32; 2],
    pub format: ExportFormat,
    #[serde(default)]
    pub required: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "lowercase")]
pub enum ExportFormat {
    Svg,
    Png,
    Ico,
    Pdf,
    Jpg,
}

/// Template registry - loads and caches templates
pub struct TemplateRegistry {
    templates: HashMap<TemplateId, Template>,
}

impl TemplateRegistry {
    pub fn new() -> Self {
        Self {
            templates: HashMap::new(),
        }
    }

    pub fn load_from_dir(dir: &Path) -> Result<Self, std::io::Error> {
        let mut registry = Self::new();
        if dir.exists() {
            for entry in fs::read_dir(dir)? {
                let entry = entry?;
                let path = entry.path();
                if path.extension().map_or(false, |e| e == "json") {
                    if let Ok(content) = fs::read_to_string(&path) {
                        if let Ok(template) = serde_json::from_str::<Template>(&content) {
                            registry.templates.insert(template.id.clone(), template);
                        }
                    }
                }
            }
        }
        Ok(registry)
    }

    pub fn get(&self, id: &str) -> Option<&Template> {
        self.templates.get(id)
    }

    pub fn list(&self) -> Vec<&Template> {
        self.templates.values().collect()
    }

    pub fn register(&mut self, template: Template) {
        self.templates.insert(template.id.clone(), template);
    }
}

impl Default for TemplateRegistry {
    fn default() -> Self {
        Self::new()
    }
}
