"""
Aerix Package Manager (arx pm)
Manages project dependencies, manifests (aerix.toml), and library modules.
"""

import os
import json


class AerixPackageManager:
    def __init__(self, project_dir: str = "."):
        self.project_dir = os.path.abspath(project_dir)
        self.manifest_path = os.path.join(self.project_dir, "aerix.toml")
        self.fallback_json = os.path.join(self.project_dir, "aerix.json")

    def init_project(self, name: str = "") -> str:
        if not name:
            name = os.path.basename(self.project_dir) or "aerix_project"
        
        manifest_content = (
            f'[project]\n'
            f'name = "{name}"\n'
            f'version = "1.0.0"\n'
            f'authors = ["developer"]\n'
            f'edition = "2026"\n\n'
            f'[dependencies]\n'
            f'# Add third-party packages here, e.g.:\n'
            f'# raylib = "5.0"\n'
            f'# math_extra = "1.2"\n'
        )

        with open(self.manifest_path, "w", encoding="utf-8") as f:
            f.write(manifest_content)
        return self.manifest_path

    def add_dependency(self, package_name: str, version: str = "*") -> bool:
        if not os.path.exists(self.manifest_path):
            self.init_project()

        with open(self.manifest_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        dep_line = f'{package_name} = "{version}"\n'
        
        # Check if already present
        for i, l in enumerate(lines):
            if l.strip().startswith(f"{package_name} =") or l.strip().startswith(f'"{package_name}" ='):
                lines[i] = dep_line
                with open(self.manifest_path, "w", encoding="utf-8") as f:
                    f.writelines(lines)
                return True

        # Append to [dependencies] section
        dep_idx = -1
        for i, l in enumerate(lines):
            if l.strip() == "[dependencies]":
                dep_idx = i
                break

        if dep_idx != -1:
            lines.insert(dep_idx + 1, dep_line)
        else:
            lines.append("\n[dependencies]\n")
            lines.append(dep_line)

        with open(self.manifest_path, "w", encoding="utf-8") as f:
            f.writelines(lines)
        return True

    def list_dependencies(self) -> dict:
        deps = {}
        if not os.path.exists(self.manifest_path):
            return deps

        with open(self.manifest_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        in_deps = False
        for line in lines:
            trimmed = line.strip()
            if trimmed.startswith("[dependencies]"):
                in_deps = True
                continue
            elif trimmed.startswith("["):
                in_deps = False
                continue

            if in_deps and "=" in trimmed and not trimmed.startswith("#"):
                parts = trimmed.split("=", 1)
                k = parts[0].strip().strip('"').strip("'")
                v = parts[1].strip().strip('"').strip("'")
                deps[k] = v

        return deps
