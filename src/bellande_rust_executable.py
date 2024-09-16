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
import tempfile

def parse_dependencies(dep_file):
    if not os.path.exists(dep_file):
        print(f"No {dep_file} file found.")
        return {}
    dependencies = {}
    with open(dep_file, 'r') as file:
        for line in file:
            parts = line.strip().split('=')
            if len(parts) == 2:
                dependencies[parts[0].strip()] = parts[1].strip().strip('"')
    return dependencies

def create_cargo_project(rust_file, dependencies, output_file, suppress_warnings):
    with tempfile.TemporaryDirectory() as temp_dir:
        project_name = "temp_rust_project"
        subprocess.run(['cargo', 'new', '--bin', project_name], cwd=temp_dir, check=True)
        project_dir = os.path.join(temp_dir, project_name)
        
        shutil.copy(rust_file, os.path.join(project_dir, 'src', 'main.rs'))
        
        cargo_toml_path = os.path.join(project_dir, 'Cargo.toml')
        with open(cargo_toml_path, 'r') as f:
            cargo_toml = toml.load(f)
        
        cargo_toml['dependencies'] = dependencies
        
        with open(cargo_toml_path, 'w') as f:
            toml.dump(cargo_toml, f)
        
        print("Building Rust project...")
        cargo_command = ['cargo', 'build', '--release']
        if suppress_warnings:
            cargo_command.append('--quiet')
        result = subprocess.run(cargo_command, cwd=project_dir, capture_output=True, text=True)
        print(f"Cargo build output:\n{result.stdout}\n{result.stderr}")
        
        if result.returncode == 0:
            os.makedirs(os.path.dirname(output_file), exist_ok=True)
            
            binary_path = os.path.join(project_dir, 'target', 'release', project_name)
            shutil.copy(binary_path, output_file)
            print(f"Rust code compiled successfully. Output file: {output_file}")
        else:
            print(f"Cargo build failed with return code {result.returncode}")

def main():
    parser = argparse.ArgumentParser(description="Compile Rust code with dependencies using Cargo")
    parser.add_argument("-d", "--dep-file", default="dependencies.txt", help="Path to the dependencies file (default: dependencies.txt)")
    parser.add_argument("-s", "--source", default="src/main.rs", help="Path to the Rust source file (default: src/main.rs)")
    parser.add_argument("-o", "--output", default="my_rust_executable", help="Name for the output executable (default: my_rust_executable)")
    parser.add_argument("--suppress-warnings", action="store_true", help="Suppress compilation warnings")
    
    args = parser.parse_args()
    print("Rust Build Script")
    print("----------------")
    print(f"Dependencies file: {args.dep_file}")
    print(f"Rust source file: {args.source}")
    print(f"Output executable: {args.output}")
    
    dependencies = parse_dependencies(args.dep_file)
    if not dependencies:
        print("No valid dependencies found. Exiting.")
        return
    
    create_cargo_project(args.source, dependencies, args.output, args.suppress_warnings)

if __name__ == "__main__":
    main()
