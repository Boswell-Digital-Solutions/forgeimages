//! ForgeImages CLI - Bridge interface for Python
//!
//! Commands: templates, validate, compile
//! Outputs JSON to stdout
//! Returns non-zero on validation failure

use clap::{Parser, Subcommand};
use std::path::PathBuf;
use std::process::ExitCode;

use forgeimages_core::{
    CompilationPipeline, CompileRequest, templates::TemplateRegistry, validation::AssetInput,
};

#[derive(Parser)]
#[command(name = "forgeimages-cli")]
#[command(about = "ForgeImages CLI - Visual Production Compiler")]
struct Cli {
    #[command(subcommand)]
    command: Commands,

    /// Path to templates directory
    #[arg(short, long, default_value = "templates")]
    templates_dir: PathBuf,
}

#[derive(Subcommand)]
enum Commands {
    /// List available templates
    Templates,

    /// Validate an asset
    Validate {
        /// Template ID
        #[arg(short, long)]
        template: String,

        /// JSON payload (AssetInput)
        #[arg(short, long)]
        payload: String,
    },

    /// Compile an asset
    Compile {
        /// Template ID
        #[arg(short, long)]
        template: String,

        /// JSON payload (CompileRequest)
        #[arg(short, long)]
        payload: String,
    },
}

fn main() -> ExitCode {
    let cli = Cli::parse();

    // Load templates
    let registry = match TemplateRegistry::load_from_dir(&cli.templates_dir) {
        Ok(r) => r,
        Err(e) => {
            eprintln!(r#"{{"error": "Failed to load templates: {}"}}"#, e);
            return ExitCode::FAILURE;
        }
    };

    let pipeline = CompilationPipeline::new(registry);

    match cli.command {
        Commands::Templates => {
            let templates: Vec<_> = pipeline
                .list_templates()
                .iter()
                .map(|t| {
                    serde_json::json!({
                        "id": t.id,
                        "name": t.name,
                        "version": t.template_version,
                        "asset_class": t.asset_class,
                        "deprecated": t.deprecated,
                    })
                })
                .collect();

            println!("{}", serde_json::to_string_pretty(&templates).unwrap());
            ExitCode::SUCCESS
        }

        Commands::Validate { template, payload } => {
            let input: AssetInput = match serde_json::from_str(&payload) {
                Ok(i) => i,
                Err(e) => {
                    println!(r#"{{"valid": false, "error": "Invalid payload: {}"}}"#, e);
                    return ExitCode::FAILURE;
                }
            };

            match pipeline.validate_asset(&template, &input) {
                Ok(result) => {
                    println!("{}", serde_json::to_string_pretty(&result).unwrap());
                    if result.valid {
                        ExitCode::SUCCESS
                    } else {
                        ExitCode::from(2) // Validation failure
                    }
                }
                Err(e) => {
                    println!(r#"{{"valid": false, "error": "{}"}}"#, e);
                    ExitCode::FAILURE
                }
            }
        }

        Commands::Compile { template, payload } => {
            let request: CompileRequest = match serde_json::from_str(&payload) {
                Ok(r) => r,
                Err(e) => {
                    println!(r#"{{"success": false, "error": "Invalid payload: {}"}}"#, e);
                    return ExitCode::FAILURE;
                }
            };

            // Ensure template_id matches
            let request = CompileRequest {
                template_id: template,
                ..request
            };

            match pipeline.compile_asset(&request) {
                Ok(asset) => {
                    let output = serde_json::json!({
                        "success": true,
                        "asset": asset,
                    });
                    println!("{}", serde_json::to_string_pretty(&output).unwrap());
                    ExitCode::SUCCESS
                }
                Err(e) => {
                    let output = serde_json::json!({
                        "success": false,
                        "error": e.to_string(),
                    });
                    println!("{}", serde_json::to_string(&output).unwrap());
                    ExitCode::from(2) // Compilation failure (validation)
                }
            }
        }
    }
}
