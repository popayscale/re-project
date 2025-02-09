import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
import os
import platform
import json
import shutil
import subprocess
import requests
from zipfile import ZipFile
from io import BytesIO
import webbrowser
import sys
from pathlib import Path

class GitHubCompilerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("GitHub Project Compiler")
        self.root.geometry("600x400")

        # Variables
        self.github_url = tk.StringVar()
        self.selected_os = tk.StringVar(value=platform.system())
        self.output_dir = tk.StringVar(value=os.path.expanduser("~/Downloads"))
        self.project_info = None
        self.skip_installation = False

        # Interface
        self.create_widgets()

    def create_widgets(self):
        # URL input
        url_frame = ttk.LabelFrame(self.root, text="GitHub Repository", padding="10")
        url_frame.pack(fill="x", padx=10, pady=5)

        ttk.Label(url_frame, text="Repository URL:").pack(side="left")
        ttk.Entry(url_frame, textvariable=self.github_url, width=50).pack(side="left", padx=5)

        # OS Selection
        os_frame = ttk.LabelFrame(self.root, text="System", padding="10")
        os_frame.pack(fill="x", padx=10, pady=5)

        os_systems = ["Windows", "Linux", "Darwin"]
        os_dropdown = ttk.Combobox(os_frame, textvariable=self.selected_os, values=os_systems)
        os_dropdown.pack(side="left", padx=5)
        os_dropdown.set(platform.system())

        # Output directory
        dir_frame = ttk.LabelFrame(self.root, text="Output Directory", padding="10")
        dir_frame.pack(fill="x", padx=10, pady=5)

        ttk.Entry(dir_frame, textvariable=self.output_dir, width=50).pack(side="left", padx=5)
        ttk.Button(dir_frame, text="Browse", command=self.browse_directory).pack(side="left")

        # Action buttons
        button_frame = ttk.Frame(self.root, padding="10")
        button_frame.pack(fill="x", padx=10, pady=5)

        ttk.Button(button_frame, text="Download & Install",
                   command=self.process_project).pack(side="left", padx=5)

        # Log area
        log_frame = ttk.LabelFrame(self.root, text="Logs", padding="10")
        log_frame.pack(fill="both", expand=True, padx=10, pady=5)

        self.log_text = tk.Text(log_frame, height=10)
        self.log_text.pack(fill="both", expand=True)

    def browse_directory(self):
        directory = filedialog.askdirectory()
        if directory:
            self.output_dir.set(directory)

    def log(self, message):
        self.log_text.insert("end", f"{message}\n")
        self.log_text.see("end")
        self.root.update()

    def handle_output_directory(self, output_path):
        """Gère la création et la vérification du dossier de sortie."""
        try:
            # Vérifier si le dossier parent existe
            parent_dir = os.path.dirname(output_path)
            if not os.path.exists(parent_dir):
                os.makedirs(parent_dir)
                self.log(f"Dossier parent créé : {parent_dir}")

            # Vérifier si le dossier de sortie existe
            if os.path.exists(output_path):
                if os.path.isdir(output_path) and os.listdir(output_path):
                    # Créer une boîte de dialogue de confirmation
                    result = messagebox.askquestion(
                        "Dossier non vide",
                        f"Le dossier {output_path} existe déjà et n'est pas vide.\nVoulez-vous supprimer son contenu ?",
                        icon='warning'
                    )
                    if result == 'yes':
                        shutil.rmtree(output_path)
                        os.makedirs(output_path)
                        self.log("Dossier nettoyé et recréé")
                        return True
                    else:
                        self.log("Opération annulée par l'utilisateur")
                        return False
            else:
                os.makedirs(output_path)
                self.log(f"Dossier de sortie créé : {output_path}")
                return True

        except Exception as e:
            self.log(f"Erreur lors de la gestion du dossier : {str(e)}")
            messagebox.showerror("Erreur", f"Impossible de gérer le dossier de sortie : {str(e)}")
            return False

    def check_tool_installed(self, tool):
        """Vérifie si un outil est installé sur le système."""
        try:
            subprocess.run([tool, "--version"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            return True
        except Exception:
            return False

    def show_missing_programs_dialog(self, project_type):
        """Affiche une boîte de dialogue pour les programmes manquants."""
        dialog = tk.Toplevel(self.root)
        dialog.title("Logiciels manquants")
        dialog.geometry("400x300")

        message = f"Ce projet nécessite l'installation de dépendances pour {project_type}.\n\n"
        message += "Veuillez vérifier les outils nécessaires :\n"

        # Définir les outils nécessaires en fonction du type de projet
        tools_needed = {
            "CMake": ["cmake"],
            "Make": ["make"],
            "Python": ["python"],
            "Node.js": ["node"],
            "Java": ["java"],
            "Executable": []
        }

        frame = ttk.Frame(dialog)
        frame.pack(padx=10, pady=10, fill="both", expand=True)

        for tool in tools_needed.get(project_type, []):
            status = "Installé" if self.check_tool_installed(tool) else "Non installé"
            label = ttk.Label(frame, text=f"- {tool.capitalize()} : {status}")
            label.pack(anchor="w")

            if status == "Non installé":
                download_button = ttk.Button(frame, text=f"Télécharger {tool.capitalize()}",
                                             command=lambda t=tool: self.open_download_link(t))
                download_button.pack(anchor="w", padx=20)

        ttk.Button(dialog, text="Continuer", command=self.download_without_install).pack(pady=5)
        ttk.Button(dialog, text="Annuler et effacer les fichiers", command=self.cancel_process).pack(pady=5)

        dialog.transient(self.root)
        dialog.grab_set()
        self.root.wait_window(dialog)

    def open_download_link(self, tool):
        """Ouvre le lien de téléchargement pour l'outil spécifié."""
        link = self.get_main_tool_link(tool)
        webbrowser.open(link)

    def get_main_tool_link(self, project_type):
        """Retourne le lien vers l'outil principal pour le type de projet."""
        main_tool_links = {
            "Python": "https://www.python.org/downloads/",
            "Node.js": "https://nodejs.org/",
            "Java": "https://www.oracle.com/java/technologies/javase-downloads.html",
            "CMake": "https://cmake.org/download/",
            "Make": "https://www.gnu.org/software/make/",
            "Executable": "https://example.com/executable-tool"
        }
        return main_tool_links.get(project_type, "https://www.google.com")

    def download_without_install(self):
        self.skip_installation = True
        self.open_project_folder()
        self.generate_tree_file()
        self.root.destroy()

    def cancel_process(self):
        if self.project_info and 'path' in self.project_info:
            project_path = self.project_info['path']
            if os.path.exists(project_path):
                shutil.rmtree(project_path)
                self.log(f"Contenu téléchargé supprimé : {project_path}")
        self.root.destroy()

    def open_project_folder(self):
        """Ouvre le dossier du projet dans l'explorateur de fichiers."""
        if self.project_info:
            project_path = self.project_info['path']
            if platform.system() == "Windows":
                os.startfile(project_path)
            elif platform.system() == "Darwin":
                subprocess.Popen(["open", project_path])
            else:
                subprocess.Popen(["xdg-open", project_path])

    def generate_tree_file(self):
        """Génère un fichier tree.txt avec l'arborescence du projet."""
        if self.project_info:
            project_path = self.project_info['path']
            tree_file_path = os.path.join(project_path, "tree.txt")

            with open(tree_file_path, "w", encoding='utf-8') as tree_file:
                for root, dirs, files in os.walk(project_path):
                    level = root.replace(project_path, '').count(os.sep)
                    indent = ' ' * 4 * level
                    tree_file.write(f"{indent}{os.path.basename(root)}/\n")
                    subindent = ' ' * 4 * (level + 1)
                    for f in files:
                        tree_file.write(f"{subindent}{f}\n")

            self.log(f"Arborescence du projet générée dans {tree_file_path}")

    def process_project(self):
        """Point d'entrée principal pour le traitement du projet."""
        try:
            if not self.github_url.get():
                messagebox.showwarning("Attention", "Veuillez entrer une URL GitHub")
                return

            # Construire le chemin de sortie
            repo_name = self.github_url.get().split('/')[-1]
            if repo_name.endswith('.git'):
                repo_name = repo_name[:-4]

            output_path = os.path.join(self.output_dir.get(), repo_name)

            # Gérer le dossier de sortie
            if self.handle_output_directory(output_path):
                self.download_and_analyze(output_path)
            else:
                self.log("Opération annulée")

        except Exception as e:
            self.log(f"Erreur lors du processus : {str(e)}")
            messagebox.showerror("Erreur", f"Une erreur est survenue : {str(e)}")

    def download_and_analyze(self, output_path):
        try:
            url = self.github_url.get().strip()
            if not url:
                self.log("Erreur : Veuillez entrer une URL GitHub")
                return

            # Normaliser l'URL en retirant le dernier slash si présent
            if url.endswith('/'):
                url = url[:-1]

            parts = url.split('/')
            owner = parts[-2]
            repo = parts[-1]

            # Construire les URLs de téléchargement pour main et master
            urls_to_try = [
                f"https://github.com/{owner}/{repo}/archive/refs/heads/main.zip",
                f"https://github.com/{owner}/{repo}/archive/refs/heads/master.zip"
            ]

            self.log(f"Téléchargement du dépôt vers {output_path}...")

            # Essayer de télécharger depuis main ou master
            success = False
            for download_url in urls_to_try:
                response = requests.get(download_url)
                if response.status_code == 200:
                    with ZipFile(BytesIO(response.content)) as zip_file:
                        zip_file.extractall(output_path)
                    success = True
                    break

            if not success:
                raise Exception("Impossible de télécharger le dépôt")

            # Trouver le dossier extrait et déplacer son contenu
            extracted_folders = [d for d in os.listdir(output_path)
                                 if os.path.isdir(os.path.join(output_path, d))]
            if extracted_folders:
                extracted_path = os.path.join(output_path, extracted_folders[0])
                for item in os.listdir(extracted_path):
                    shutil.move(
                        os.path.join(extracted_path, item),
                        os.path.join(output_path, item)
                    )
                shutil.rmtree(extracted_path)

            self.log("Dépôt téléchargé avec succès")
            self.analyze_project(output_path, repo)

        except Exception as e:
            self.log(f"Erreur lors du téléchargement : {str(e)}")
            raise

    def analyze_project(self, project_path, repo_name):
        self.log("\nAnalyse de la structure du projet...")

        # Détection du type de projet
        project_files = os.listdir(project_path)

        # Définition des types de projets et leurs fichiers/dossiers caractéristiques
        project_signatures = {
            "CMake": (["CMakeLists.txt"], self.compile_cmake_project),
            "Make": (["Makefile"], self.compile_make_project),
            "Python": (["setup.py", "main.py", "requirements.txt"], self.compile_python_project),
            "Node.js": (["package.json"], self.compile_node_project),
            "Java": (["pom.xml", "build.gradle"], self.compile_java_project),
            "Executable": ([".exe", ".app", ".out"], self.handle_executable)
        }

        detected_type = None
        compile_method = None

        for proj_type, (signatures, method) in project_signatures.items():
            for signature in signatures:
                if any(f for f in project_files if signature in f):
                    detected_type = proj_type
                    compile_method = method
                    break
            if detected_type:
                break

        # Si aucun type n'est détecté, chercher des scripts ou exécutables
        if not detected_type:
            self.log("Type de projet inconnu, recherche de scripts ou exécutables...")
            main_executable = self.find_main_executable(project_path)
            if main_executable:
                detected_type = "Script/Executable"
                compile_method = self.handle_executable

        # Recherche de l'exécutable principal
        main_executable = self.find_main_executable(project_path)

        self.project_info = {
            "path": project_path,
            "type": detected_type or "Unknown",
            "name": repo_name,
            "os": self.selected_os.get(),
            "compile_method": compile_method.__name__ if compile_method else None,
            "main_executable": main_executable,
        }

        self.log(f"Type de projet détecté : {self.project_info['type']}")

        # Sauvegarder les informations du projet
        with open(os.path.join(project_path, ".compiler_info.json"), "w", encoding='utf-8') as f:
            json.dump(self.project_info, f, default=str, ensure_ascii=False, indent=2)

        self.show_missing_programs_dialog(self.project_info['type'])

    def create_windows_shortcut(self, desktop_path, target_path, project_name):
        try:
            import winshell
            from win32com.client import Dispatch
            shortcut_path = os.path.join(desktop_path, f"{project_name}.lnk")
            shell = Dispatch('WScript.Shell')
            shortcut = shell.CreateShortCut(shortcut_path)

            if target_path.endswith('.py'):
                python_path = sys.executable
                shortcut.Targetpath = python_path
                shortcut.Arguments = f'"{target_path}"'
            elif target_path.endswith('.js'):
                shortcut.Targetpath = 'node'
                shortcut.Arguments = f'"{target_path}"'
            elif target_path.endswith('.jar'):
                shortcut.Targetpath = 'javaw'
                shortcut.Arguments = f'-jar "{target_path}"'
            else:
                shortcut.Targetpath = target_path

            shortcut.WorkingDirectory = os.path.dirname(target_path)
            shortcut.save()
            self.log(f"Raccourci créé avec succès : {shortcut_path}")

        except Exception as e:
            self.log(f"Erreur lors de la création du raccourci : {str(e)}")
            raise

    def create_unix_shortcut(self, desktop_path, target_path, project_name):
        try:
            shortcut_path = os.path.join(desktop_path, f"{project_name}.desktop")
            with open(shortcut_path, "w") as f:
                f.write(f"""[Desktop Entry]
Name={project_name}
Exec={target_path}
Type=Application
Terminal=false
""")
            os.chmod(shortcut_path, 0o755)
            self.log(f"Raccourci créé avec succès : {shortcut_path}")
        except Exception as e:
            self.log(f"Erreur lors de la création du raccourci : {str(e)}")
            raise

    def compile_cmake_project(self, project_path):
        try:
            build_path = os.path.join(project_path, "build")
            os.makedirs(build_path, exist_ok=True)

            self.log("Configuration CMake...")
            subprocess.run(["cmake", ".."], cwd=build_path, check=True)

            self.log("Compilation...")
            subprocess.run(["cmake", "--build", "."], cwd=build_path, check=True)

            self.project_info['main_executable'] = self.find_main_executable(build_path)
            self.log("Projet CMake compilé avec succès")
        except Exception as e:
            self.log(f"Erreur de compilation CMake : {str(e)}")
            raise

    def compile_make_project(self, project_path):
        try:
            self.log("Compilation avec Makefile...")
            subprocess.run(["make"], cwd=project_path, check=True)

            self.project_info['main_executable'] = self.find_main_executable(project_path)
            self.log("Projet Makefile compilé avec succès")
        except Exception as e:
            self.log(f"Erreur de compilation Make : {str(e)}")
            raise

    def compile_python_project(self, project_path):
        try:
            # Installation des dépendances si requirements.txt existe
            if os.path.exists(os.path.join(project_path, "requirements.txt")):
                self.log("Installation des dépendances Python...")
                subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"],
                             cwd=project_path, check=True)

            # Chercher le script principal
            main_files = ["main.py", "app.py", "__main__.py"]
            main_script = None
            for file in os.listdir(project_path):
                if file in main_files:
                    main_script = file
                    break

            if not main_script:
                # Si aucun fichier principal trouvé, prendre le premier .py
                py_files = [f for f in os.listdir(project_path) if f.endswith('.py')]
                if py_files:
                    main_script = py_files[0]

            if main_script:
                launcher_script = os.path.join(project_path, "launch.py")
                with open(launcher_script, "w") as f:
                    f.write(f"""import subprocess
import os
import sys

if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    main_script = os.path.join(script_dir, "{main_script}")
    subprocess.run([sys.executable, main_script], cwd=script_dir)
""")
                self.project_info['main_executable'] = launcher_script
                self.log("Script de lancement Python créé")

                # Compiler en exécutable si Windows est sélectionné
                if self.selected_os.get() == "Windows":
                    self.compile_to_exe(project_path, main_script)
            else:
                self.log("Aucun fichier Python trouvé")
                raise Exception("Aucun fichier Python trouvé")

        except Exception as e:
            self.log(f"Erreur de compilation Python : {str(e)}")
            raise

    def compile_to_exe(self, project_path, main_script):
        try:
            self.log("Compilation en exécutable Windows...")
            output_dir = os.path.join(project_path, "dist")

            # Nettoyage des anciennes compilations
            if os.path.exists(output_dir):
                shutil.rmtree(output_dir)

            # Compilation avec PyInstaller
            subprocess.run([
                'pyinstaller',
                '--onefile',
                '--noconsole',
                os.path.join(project_path, main_script)
            ], cwd=project_path, check=True)

            # Chercher l'exécutable généré
            exe_name = os.path.splitext(main_script)[0] + '.exe'
            exe_path = os.path.join(project_path, 'dist', exe_name)

            if os.path.exists(exe_path):
                self.project_info['main_executable'] = exe_path
                self.log(f"Exécutable créé avec succès : {exe_path}")

                # Nettoyage
                build_dir = os.path.join(project_path, 'build')
                if os.path.exists(build_dir):
                    shutil.rmtree(build_dir)

                for spec_file in Path(project_path).glob('*.spec'):
                    spec_file.unlink()
            else:
                raise Exception("L'exécutable n'a pas été créé")

        except Exception as e:
            self.log(f"Erreur lors de la compilation en exe : {str(e)}")
            raise

    def compile_node_project(self, project_path):
        try:
            self.log("Installation des dépendances Node.js...")
            subprocess.run(["npm", "install"], cwd=project_path, check=True)

            package_json_path = os.path.join(project_path, "package.json")
            if os.path.exists(package_json_path):
                with open(package_json_path) as f:
                    package_data = json.load(f)
                main_script = package_data.get("main", "index.js")
            else:
                main_script = "index.js"

            launcher_script = os.path.join(project_path, "launch.js")
            with open(launcher_script, "w") as f:
                f.write(f"""const path = require('path');
const child_process = require('child_process');

const scriptPath = path.join(__dirname, '{main_script}');
child_process.spawn('node', [scriptPath], {{ stdio: 'inherit' }});
""")

            self.project_info['main_executable'] = launcher_script
            self.log("Script de lancement Node.js créé")
        except Exception as e:
            self.log(f"Erreur de compilation Node.js : {str(e)}")
            raise

    def compile_java_project(self, project_path):
        try:
            # Vérifier si le projet utilise Maven ou Gradle
            if os.path.exists(os.path.join(project_path, "pom.xml")):
                self.log("Compilation avec Maven...")
                subprocess.run(["mvn", "clean", "install"], cwd=project_path, check=True)
            elif os.path.exists(os.path.join(project_path, "build.gradle")):
                self.log("Compilation avec Gradle...")
                subprocess.run(["gradle", "build"], cwd=project_path, check=True)
            else:
                self.log("Aucun fichier de configuration Maven ou Gradle trouvé")
                raise Exception("Aucun fichier de configuration Maven ou Gradle trouvé")

            # Trouver l'exécutable principal
            self.project_info['main_executable'] = self.find_main_executable(project_path)
            self.log("Projet Java compilé avec succès")
        except Exception as e:
            self.log(f"Erreur de compilation Java : {str(e)}")
            raise

    def handle_executable(self, project_path):
        try:
            self.log("Projet avec exécutable déjà présent...")

            # Trouver l'exécutable principal
            self.project_info['main_executable'] = self.find_main_executable(project_path)

            if self.project_info['main_executable']:
                self.log(f"Exécutable principal trouvé : {self.project_info['main_executable']}")
            else:
                self.log("Aucun exécutable trouvé")
                raise Exception("Aucun exécutable trouvé")

        except Exception as e:
            self.log(f"Erreur dans la gestion de l'exécutable : {str(e)}")
            raise

    def create_shortcut(self):
        try:
            if not self.project_info:
                self.log("Erreur : Projet non analysé")
                return

            desktop_path = os.path.expanduser("~/Desktop")
            target_path = self.project_info['main_executable']
            project_name = self.project_info['name']

            if self.selected_os.get() == "Windows":
                self.create_windows_shortcut(desktop_path, target_path, project_name)
            else:
                self.create_unix_shortcut(desktop_path, target_path, project_name)

            self.log("Raccourci créé avec succès")
        except Exception as e:
            self.log(f"Erreur lors de la création du raccourci : {str(e)}")
            raise

    def find_main_executable(self, project_path):
        # Logique pour trouver l'exécutable principal
        # Cela peut être personnalisé en fonction des besoins spécifiques
        executables = [f for f in os.listdir(project_path) if os.path.isfile(os.path.join(project_path, f))]
        for ext in ['.exe', '.jar', '.out', '.py', '.js', '.sh', '.bat']:
            for exe in executables:
                if exe.endswith(ext):
                    return os.path.join(project_path, exe)
        return None

if __name__ == "__main__":
    root = tk.Tk()
    app = GitHubCompilerApp(root)
    root.mainloop()
