"""Pipeline configuration for the BMR Digitization Pipeline."""

from pathlib import Path

# Base directory for the pipeline project
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Storage paths
STORAGE_DIR = BASE_DIR / "storage"
RECORDS_DIR = STORAGE_DIR / "records"
QUEUE_DIR = STORAGE_DIR / "queue"
TRAINING_DIR = STORAGE_DIR / "training"

# Supported input file formats
SUPPORTED_FORMATS: set[str] = {"png", "jpeg", "jpg", "tiff", "tif", "pdf"}

# Number of new validated records before triggering a retraining cycle
RETRAIN_THRESHOLD: int = 10
