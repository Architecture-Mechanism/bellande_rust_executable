# Copyright (C) 2024 Bellande Architecture Mechanism Research Innovation Center, Ronaldson Bellande

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

#!/usr/bin/env python3

import subprocess
import os
import shutil
import argparse
import toml
from bellande_parser.bellande_parser import Bellande_Format

def ensure_directory(path):
    """Ensure a directory exists and create one if it does not"""
    os.makedirs(path, exist_ok=True)

def copy_source_files(src_dir, dest_dir, project_src_path="src"):
    """Maintained the structure of the src file; or assigned"""
    if not os.path.exists(src_dir):
        raise FileNotFoundError(f"Source directory '{src_dir}' not found")
    
    dest_src_dir = os.path.join(dest_dir, project_src_path)
    ensure_directory(dest_src_dir)
    
    for root, _, files in os.walk(src_dir):
        for file in files:
            src_path = os.path.join(root, file)
            rel_path = os.path.relpath(src_path, src_dir)
            dest_path = os.path.join(dest_src_dir, rel_path)
            ensure_directory(os.path.dirname(dest_path))
            shutil.copy2(src_path, dest_path)

def create_cargo_toml(project_dir, main_file, binary_name, project_src_path="src"):
    """Create a Cargo.toml file for a binary target."""
    cargo_config = {
        'package': {
            'name': binary_name,
            'version': "0.1.0",
            'edition': "2021"
        },
        'dependencies': {}
    }
    
    if main_file != 'main.rs':
        cargo_config['bin'] = [{
            'name': binary_name,
            'path': os.path.join(project_src_path, main_file)
        }]
    
    cargo_toml_path = os.path.join(project_dir, 'Cargo.toml')
    with open(cargo_toml_path, 'w') as f:
        toml.dump(cargo_config, f)

def parse_dependencies(dep_file):
    """Parse dependencies from the specified .bellande file using Bellande Format."""
    bellande_parser = Bellande_Format()
    # Get the raw content as a string
    parsed_data = bellande_parser.parse_bellande(dep_file)
    
    dependencies = {}
    current_package = None
    
    # Process line by line
    for line in parsed_data.strip().split('\n'):
        line = line.strip()
        if not line:
            continue
        
        # Check if this line defines a package with version
        if ': "' in line and not line.startswith(' '):
            # Parse the package name and version
            parts = line.split(': "', 1)
            package_name = parts[0].strip()
            version = parts[1].rstrip('"')
            
            # Reset package processing state
            current_package = package_name
            
            # Add as simple version dependency if no features follow
            dependencies[current_package] = version
        
        # Handle features
        elif line.startswith('features = ') and current_package:
            features_str = line.replace('features = ', '').strip()
            features = [f.strip() for f in features_str.split(',')]
            
            # Convert the simple version to a complex config
            if isinstance(dependencies[current_package], str):
                version = dependencies[current_package]
                dependencies[current_package] = {
                    "version": version,
                    "features": features
                }
            else:
                dependencies[current_package]["features"] = features
        
        # Handle optional flag
        elif line.startswith('optional = ') and current_package:
            optional_value = line.replace('optional = ', '').strip().lower() == 'true'
            
            # Convert the simple version to a complex config if needed
            if isinstance(dependencies[current_package], str):
                version = dependencies[current_package]
                dependencies[current_package] = {
                    "version": version,
                    "optional": optional_value
                }
            else:
                dependencies[current_package]["optional"] = optional_value
    
    return dependencies

def update_cargo_toml_dependencies(project_dir, dependencies):
    """Update the dependencies in Cargo.toml."""
    cargo_toml_path = os.path.join(project_dir, 'Cargo.toml')
    with open(cargo_toml_path, 'r') as f:
        cargo_config = toml.load(f)
    
    # Process dependencies for proper Cargo.toml formatting
    processed_deps = {}
    for name, config in dependencies.items():
        if isinstance(config, str):
            # Simple version dependency
            processed_deps[name] = config
        else:
            # Complex dependency with features or optional flag
            cargo_dep = {}
            if "version" in config:
                cargo_dep["version"] = config["version"]
            if "features" in config and config["features"]:
                cargo_dep["features"] = config["features"]
            if "optional" in config:
                cargo_dep["optional"] = config["optional"]
            processed_deps[name] = cargo_dep
    
    cargo_config['dependencies'] = processed_deps
    
    with open(cargo_toml_path, 'w') as f:
        toml.dump(cargo_config, f)

def build_project(project_dir, output_path, binary_name):
    """Build the Rust project as an executable."""
    cargo_command = ['cargo', 'build', '--release']
    result = subprocess.run(cargo_command, cwd=project_dir, capture_output=True, text=True)
    
    if result.returncode == 0:
        exe_extension = '.exe' if os.name == 'nt' else ''
        built_exe = os.path.join(project_dir, 'target', 'release', f"{binary_name}{exe_extension}")
        ensure_directory(os.path.dirname(output_path))
        shutil.copy2(built_exe, output_path)
        
        if os.name != 'nt':
            os.chmod(output_path, 0o755)
        
        return True
    else:
        print("Build failed. Cargo output:")
        print(result.stdout)
        print(result.stderr)
        return False

def main():
    parser = argparse.ArgumentParser(description="Universal Rust Executable Builder")
    parser.add_argument("-d", "--dep-file", required=True, help="Path to the .bellande dependencies file")
    parser.add_argument("-sp", "--src-path", default="src", help="Source path within the project (default: src)")
    parser.add_argument("-s", "--src-dir", required=True, help="Source directory containing Rust files")
    parser.add_argument("-m", "--main-file", required=True, help="Main Rust file name (e.g., main.rs)")
    parser.add_argument("-o", "--output", required=True, help="Output path for the compiled executable")
    
    args = parser.parse_args()
    
    binary_name = os.path.splitext(args.main_file)[0]
    build_dir = f"build_{binary_name}"
    ensure_directory(build_dir)
    
    try:
        copy_source_files(args.src_dir, build_dir, args.src_path)
        create_cargo_toml(build_dir, args.main_file, binary_name, args.src_path)        
        
        dependencies = parse_dependencies(args.dep_file)
        update_cargo_toml_dependencies(build_dir, dependencies)
        
        output_path = f"{args.output}.exe" if os.name == 'nt' else args.output
        
        if build_project(build_dir, output_path, binary_name):
            print(f"Successfully built and copied to {output_path}")
            return 0
        else:
            print("Build failed")
            return 1
    
    finally:
        shutil.rmtree(build_dir, ignore_errors=True)

if __name__ == "__main__":
    exit(main())
