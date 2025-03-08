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
import json
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
    raw_content = bellande_parser.parse_bellande(dep_file)
    
    print(f"Raw content from bellande file: {raw_content[:200]}...")
    
    lines = raw_content.strip().splitlines()
    processed_dependencies = {}
    
    current_dep = None
    
    for line in lines:
        line = line.strip()
        print(f"Processing line: {line}")
        
        if not line or line.startswith("#"):
            continue
        
        if ":" in line and not line.startswith(" "):
            parts = line.split(":", 1)
            dep_name = parts[0].strip()
            dep_value = parts[1].strip().strip('"')
            
            print(f"Found dependency: {dep_name} = {dep_value}")
            
            processed_dependencies[dep_name] = dep_value
            current_dep = dep_name
            
        elif "=" in line and line.startswith(" ") and current_dep:
            parts = line.strip().split("=", 1)
            attr_name = parts[0].strip()
            attr_value = parts[1].strip()
            
            print(f"  Found attribute for {current_dep}: {attr_name} = {attr_value}")
            
            if not isinstance(processed_dependencies[current_dep], dict):
                version = processed_dependencies[current_dep]
                processed_dependencies[current_dep] = {"version": version}
            
            # Handle different attribute types
            if attr_name == "features":
                if attr_value.startswith("[") and attr_value.endswith("]"):
                    features_list = [f.strip() for f in attr_value[1:-1].split(",")]
                    processed_dependencies[current_dep]["features"] = features_list
                else:
                    processed_dependencies[current_dep]["features"] = [attr_value.strip()]
            elif attr_name == "optional":
                processed_dependencies[current_dep]["optional"] = attr_value.lower() == "true"
            else:
                processed_dependencies[current_dep][attr_name] = attr_value
    
    print(f"Processed dependencies: {json.dumps(processed_dependencies, indent=2)}")
    
    return processed_dependencies

def update_cargo_toml_dependencies(project_dir, dependencies):
    """Update the dependencies in Cargo.toml."""
    
    cargo_toml_path = os.path.join(project_dir, 'Cargo.toml')
    
    # Load the existing Cargo.toml file
    with open(cargo_toml_path, 'r') as f:
        cargo_config = toml.load(f)
    
    # Debug: Print current Cargo.toml configuration
    print(f"Current Cargo.toml config: {json.dumps(cargo_config, indent=2)}")
    
    # Update the dependencies section
    cargo_config['dependencies'] = dependencies
    
    # Debug: Print updated configuration
    print(f"Updated Cargo.toml config: {json.dumps(cargo_config, indent=2)}")
    
    # Write the updated config back to Cargo.toml
    with open(cargo_toml_path, 'w') as f:
        toml.dump(cargo_config, f)
    
    # Debug: Read back the written file to verify
    with open(cargo_toml_path, 'r') as f:
        content = f.read()
        print(f"Written Cargo.toml content: {content[:200]}...")

def build_project(project_dir, output_path, binary_name):
    """Build the Rust project as an executable."""
    cargo_command = ['cargo', 'build', '--release']
    
    try:
        version_check = subprocess.run(['cargo', '--version'], 
                                      capture_output=True, text=True, check=True)
        print(f"Using Cargo: {version_check.stdout.strip()}")
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        print(f"Error checking Cargo version: {e}")
        return False
    
    print(f"Running build command: {' '.join(cargo_command)} in {project_dir}")
    result = subprocess.run(cargo_command, cwd=project_dir, capture_output=True, text=True)
    
    if result.returncode == 0:
        print("Build succeeded!")
        exe_extension = '.exe' if os.name == 'nt' else ''
        built_exe = os.path.join(project_dir, 'target', 'release', f"{binary_name}{exe_extension}")
        ensure_directory(os.path.dirname(output_path))
        shutil.copy2(built_exe, output_path)
        
        if os.name != 'nt':
            os.chmod(output_path, 0o755)
        
        print(f"Executable copied to {output_path}")
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
    parser.add_argument("--debug", action="store_true", help="Enable additional debug output")
    
    args = parser.parse_args()
    
    binary_name = os.path.splitext(args.main_file)[0]
    build_dir = f"build_{binary_name}"
    ensure_directory(build_dir)
    
    print(f"Creating build in directory: {build_dir}")
    print(f"Source directory: {args.src_dir}")
    print(f"Dependencies file: {args.dep_file}")
    
    try:
        print("Copying source files...")
        copy_source_files(args.src_dir, build_dir, args.src_path)
        
        print("Creating initial Cargo.toml...")
        create_cargo_toml(build_dir, args.main_file, binary_name, args.src_path)        
        
        print("Parsing dependencies...")
        dependencies = parse_dependencies(args.dep_file)
        
        print("Updating Cargo.toml with dependencies...")
        update_cargo_toml_dependencies(build_dir, dependencies)
        
        print("Building project...")
        output_path = f"{args.output}.exe" if os.name == 'nt' else args.output
        
        if build_project(build_dir, output_path, binary_name):
            print(f"Successfully built and copied to {output_path}")
            return 0
        else:
            print("Build failed")
            return 1
    
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    finally:
        if not args.debug:
            print(f"Cleaning up build directory: {build_dir}")
            shutil.rmtree(build_dir, ignore_errors=True)
        else:
            print(f"Debug mode: Keeping build directory: {build_dir}")

if __name__ == "__main__":
    exit(main())
