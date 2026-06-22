// Échafaudage Tauri v2 — à compiler avec la toolchain Rust + tauri-cli sur ta machine.
// Rôle de cette coquille : lancer le sidecar Python (la barrière de validation) puis
// ouvrir une fenêtre sur http://127.0.0.1:8765. Toute la logique vit dans le sidecar.
//
// DEV : on lance `python3 serveur_validation.py`.
// PROD : remplacer par le binaire figé (PyInstaller) déclaré dans bundle.externalBin.

#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::process::Command;

fn main() {
    // Lance le sidecar de validation. Adapter le chemin du corpus selon le flux réel.
    let _sidecar = Command::new("python3")
        .args([
            "../serveur_validation.py",
            "--corpus", "../../../../data/projets/courant/corpus.md",
            "--out",    "../../../../data/projets/courant/corpus-valide.md",
            "--port",   "8765",
        ])
        .spawn()
        .expect("échec du lancement du sidecar de validation");

    tauri::Builder::default()
        .run(tauri::generate_context!())
        .expect("échec du démarrage de l'application Tauri");
}
