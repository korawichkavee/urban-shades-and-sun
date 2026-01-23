#!/usr/bin/env python3
# ABOUTME: Packages YOLO dataset, training script, and dependencies into a tarball for GPU machine
# ABOUTME: Creates timestamped archive with everything needed to train on remote system

import os
import tarfile
import subprocess
import yaml
from pathlib import Path
from datetime import datetime

# Define paths
BASE_DIR = Path("/home/kieran/Documents/Python/sunny_day_SVI")
DATASET_DIR = BASE_DIR / "city7sample/images_to_label/batch2/sunny_batch_from_json"
TRAINING_SCRIPT_PORTABLE = BASE_DIR / "yolo_train_portable.py"

def get_directory_size(path):
    """Calculate total size of a directory in bytes."""
    total = 0
    for entry in os.scandir(path):
        if entry.is_file():
            total += entry.stat().st_size
        elif entry.is_dir():
            total += get_directory_size(entry.path)
    return total

def format_size(bytes_size):
    """Format bytes to human-readable size."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_size < 1024.0:
            return f"{bytes_size:.2f} {unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.2f} TB"

def count_files(directory):
    """Count files in directory recursively."""
    count = 0
    for root, dirs, files in os.walk(directory):
        count += len(files)
    return count

def create_requirements_txt(output_path):
    """Generate requirements.txt with key dependencies."""
    requirements = """# YOLO Training Requirements
ultralytics>=8.3.0
torch>=2.0.0
torchvision>=0.15.0
numpy>=1.24.0
opencv-python>=4.8.0
Pillow>=9.5.0
PyYAML>=6.0
"""
    with open(output_path, 'w') as f:
        f.write(requirements)
    print(f"Created requirements.txt")

def create_portable_data_yaml(output_path, original_yaml_path):
    """Create a portable version of data.yaml with relative paths."""
    # Read original data.yaml
    with open(original_yaml_path, 'r') as f:
        data = yaml.safe_load(f)

    # Update path to be relative to package root (sunny_batch subdirectory)
    data['path'] = 'sunny_batch'

    # Write portable version
    with open(output_path, 'w') as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False)

    print(f"Created portable data.yaml")

def create_remote_setup_script(output_path):
    """Create setup script for remote GPU machine."""
    script = """#!/bin/bash
# ABOUTME: Setup script for YOLO training environment on GPU machine
# ABOUTME: Extracts dataset, creates venv, installs dependencies, verifies GPU

set -e

echo "================================================"
echo "YOLO Dataset Setup Script"
echo "================================================"
echo ""

# Check if running in correct directory
if [ ! -f "requirements.txt" ] || [ ! -f "yolo_train_portable.py" ]; then
    echo "ERROR: Please run this script from the extracted dataset directory"
    exit 1
fi

# Create virtual environment
echo "Creating Python virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo "Installing dependencies from requirements.txt..."
pip install -r requirements.txt

# Verify GPU availability
echo ""
echo "Checking GPU availability..."
python3 -c "import torch; print(f'PyTorch version: {torch.__version__}'); print(f'CUDA available: {torch.cuda.is_available()}'); print(f'CUDA version: {torch.version.cuda if torch.cuda.is_available() else \"N/A\"}'); print(f'GPU count: {torch.cuda.device_count()}'); [print(f'GPU {i}: {torch.cuda.get_device_name(i)}') for i in range(torch.cuda.device_count())]"

echo ""
echo "================================================"
echo "Setup Complete!"
echo "================================================"
echo ""
echo "Dataset location: $(pwd)/sunny_batch/"
echo "Training script: $(pwd)/yolo_train_portable.py"
echo ""
echo "To start training:"
echo "  1. Activate the virtual environment: source venv/bin/activate"
echo "  2. (Optional) Edit yolo_train_portable.py to adjust epochs, batch size, etc."
echo "  3. Run: python yolo_train_portable.py"
echo ""
"""
    with open(output_path, 'w') as f:
        f.write(script)
    os.chmod(output_path, 0o755)
    print(f"Created remote_setup.sh")

def main():
    # Verify required files exist
    if not DATASET_DIR.exists():
        print(f"ERROR: Dataset directory not found: {DATASET_DIR}")
        return
    if not TRAINING_SCRIPT_PORTABLE.exists():
        print(f"ERROR: Training script not found: {TRAINING_SCRIPT_PORTABLE}")
        return

    # Create temporary directory for packaging
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    package_name = f"yolo_dataset_{timestamp}"
    temp_dir = BASE_DIR / package_name
    temp_dir.mkdir(exist_ok=True)

    print(f"\nPackaging YOLO dataset and training code...")
    print(f"Package: {package_name}")
    print(f"=" * 60)

    # Count files and calculate sizes
    dataset_size = get_directory_size(DATASET_DIR)
    train_images = count_files(DATASET_DIR / "images/train") if (DATASET_DIR / "images/train").exists() else 0
    val_images = count_files(DATASET_DIR / "images/val") if (DATASET_DIR / "images/val").exists() else 0
    train_labels = count_files(DATASET_DIR / "labels/train") if (DATASET_DIR / "labels/train").exists() else 0
    val_labels = count_files(DATASET_DIR / "labels/val") if (DATASET_DIR / "labels/val").exists() else 0

    print(f"\nDataset summary:")
    print(f"  Training: {train_images} images, {train_labels} labels")
    print(f"  Validation: {val_images} images, {val_labels} labels")
    print(f"  Total size: {format_size(dataset_size)}")

    # Create requirements.txt
    create_requirements_txt(temp_dir / "requirements.txt")

    # Create portable data.yaml
    original_data_yaml = DATASET_DIR / "data.yaml"
    portable_data_yaml = temp_dir / "data.yaml"
    create_portable_data_yaml(portable_data_yaml, original_data_yaml)

    # Create remote setup script
    create_remote_setup_script(temp_dir / "remote_setup.sh")

    # Create tarball
    tarball_path = BASE_DIR / f"{package_name}.tar.gz"
    print(f"\nCreating tarball: {tarball_path.name}")

    with tarfile.open(tarball_path, "w:gz") as tar:
        # Add dataset directory (excluding data.yaml - we'll add portable version)
        print(f"  Adding dataset: sunny_batch/")
        def exclude_data_yaml(tarinfo):
            if tarinfo.name.endswith('data.yaml'):
                return None
            return tarinfo
        tar.add(DATASET_DIR, arcname=f"{package_name}/sunny_batch", filter=exclude_data_yaml)

        # Add portable data.yaml
        print(f"  Adding portable data.yaml")
        tar.add(portable_data_yaml, arcname=f"{package_name}/sunny_batch/data.yaml")

        # Add training script
        print(f"  Adding training script: yolo_train_portable.py")
        tar.add(TRAINING_SCRIPT_PORTABLE, arcname=f"{package_name}/yolo_train_portable.py")

        # Add requirements.txt
        print(f"  Adding requirements.txt")
        tar.add(temp_dir / "requirements.txt", arcname=f"{package_name}/requirements.txt")

        # Add setup script
        print(f"  Adding remote_setup.sh")
        tar.add(temp_dir / "remote_setup.sh", arcname=f"{package_name}/remote_setup.sh")

    # Clean up temp directory
    import shutil
    shutil.rmtree(temp_dir)

    # Get final tarball size
    tarball_size = os.path.getsize(tarball_path)

    print(f"\n" + "=" * 60)
    print(f"Package created successfully!")
    print(f"=" * 60)
    print(f"\nLocation: {tarball_path}")
    print(f"Size: {format_size(tarball_size)}")
    print(f"\nTo transfer to GPU machine:")
    print(f"  scp {tarball_path.name} user@gpu-machine:/path/to/destination/")
    print(f"\nOn GPU machine:")
    print(f"  tar -xzf {tarball_path.name}")
    print(f"  cd {package_name}")
    print(f"  ./remote_setup.sh")
    print()

if __name__ == "__main__":
    main()
