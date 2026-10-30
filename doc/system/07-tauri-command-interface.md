# §7 — Tauri Command Interface

`forgeimages-tauri` is a library crate. It holds the Tauri 2 IPC commands that the AuthorForge desktop app registers. It has no `main` and no Tauri app of its own. Nothing in this repository runs these commands. AuthorForge does.

## Registration (in AuthorForge, not here)

AuthorForge vendors this repository as the `third_party/forgeimages` git submodule and depends on the crate by path:

```toml
# AuthorForge src-tauri/Cargo.toml
forgeimages-tauri = { path = "../third_party/forgeimages/forgeimages-tauri" }
```

AuthorForge's `src-tauri/src/main.rs` adds the three commands to its `invoke_handler`. At setup it calls `init_state(resource_dir.join("forgeimages-templates"))` and `app.manage(...)`s the result. The templates AuthorForge bundles are its own copies under `src-tauri/forgeimages-templates/`, **not** this repository's `forgeimages-core/templates/`. The two sets can drift. Check both when you change a template (§17).

## Managed State

```rust
pub struct ForgeImagesState {
    pub pipeline: Mutex<CompilationPipeline>,
}

pub fn init_state(templates_dir: PathBuf) -> ForgeImagesState
```

`init_state` loads the template directory with `TemplateRegistry::load_from_dir`. If loading fails, it falls back to an **empty** registry and does not raise. A missing or unreadable templates directory therefore produces a working app where every command reports `Template not found`. It does not fail at startup.

Each command takes the mutex. A poisoned lock returns the error string `"Lock poisoned"`.

## Commands

| Command | Arguments | Returns | Engine call |
| --- | --- | --- | --- |
| `forgeimages_list_templates` | none | `Vec<TemplateInfo>` | `list_templates()` |
| `forgeimages_validate_file` | `asset_path: String`, `template_id: String` | `ValidationResult` | `validate_from_file(path)` then `validate_asset()` |
| `forgeimages_validate_metadata` | `input: AssetInput`, `template_id: String` | `ValidationResult` | `validate_asset()` |

`TemplateInfo` is `{ id, name, version, asset_class, deprecated }`. `asset_class` is the `Debug` form lower-cased (for example `characterportrait`). That differs from the serde form the CLI emits (`character_portrait`). A frontend that compares the two will not match multi-word classes.

All errors cross IPC as `Err(String)`, the `Display` form of the underlying `PipelineError` or `FileValidationError`.

### `forgeimages_validate_file`

This command reads the real file, decodes it with the `image` crate (JPEG, PNG and TIFF are enabled), and validates the actual pixel dimensions. Declared metadata plays no part. `color_count` is always `None` on this path, so the colour-count rule never fires for file validation. The command decodes the whole image to learn its size, so memory use grows with the image.

## What the Desktop Path Does Not Do

- **No compile.** There is no Tauri command for `compile_asset`. Desktop compilation, if AuthorForge needs it, goes through the `forgeimages-bridge` sidecar (§12).
- **No audit log.** The audit log is written by the Python bridge. Tauri validations are not logged by ForgeImages.
- **No `ValidationOutcome`.** The commands return the raw `ValidationResult`. AuthorForge derives any clearance level itself.
