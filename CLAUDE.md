# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Hailo-Apps is a production-ready AI applications infrastructure for Hailo hardware accelerators (Hailo-8, Hailo-8L, Hailo-10H). It provides 20+ real-time computer vision and GenAI applications built on GStreamer pipelines.

**Version**: 25.12.0
**Python**: 3.10+
**Platforms**: Raspberry Pi 5, x86_64 Ubuntu, edge devices with Hailo accelerators

## Common Commands

```bash
# Environment setup (must source before any work)
source setup_env.sh

# Run pipeline applications
hailo-detect              # Object detection
hailo-pose                # Pose estimation
hailo-seg                 # Instance segmentation
hailo-depth               # Depth estimation
hailo-face-recon          # Face recognition
hailo-tiling              # High-res tiling
hailo-clip                # Zero-shot classification (CLIP)
hailo-ocr                 # OCR with PaddleOCR

# GenAI applications (Hailo-10H only)
python -m hailo_apps.python.gen_ai_apps.agent_tools_example.agent
python -m hailo_apps.python.gen_ai_apps.vlm_chat.vlm_chat
python -m hailo_apps.python.gen_ai_apps.voice_assistant.voice_assistant

# Testing
./run_tests.sh              # All tests
./run_tests.sh --sanity     # Environment validation only
./run_tests.sh --install    # Resource validation only
./run_tests.sh --pipelines  # Functional tests only
pytest tests/test_sanity_check.py -v  # Direct pytest

# Linting (uses ruff)
ruff check .                # Check code
ruff check --fix .          # Auto-fix issues
ruff format .               # Format code
pre-commit run --all-files  # Run all pre-commit hooks

# Resource management
hailo-download-resources              # Auto-detect architecture
hailo-download-resources --arch hailo8
hailo-download-resources --arch hailo10h

# Install optional dependencies
pip install -e ".[dev]"       # Development tools
pip install -e ".[gen-ai]"    # Voice/TTS for GenAI apps
pip install -e ".[ocr]"       # PaddleOCR
pip install -e ".[speech-rec]" # Whisper
pip install -e ".[clip]"      # CLIP
```

## Architecture

### Three-Layer Stack

1. **GStreamer** - Open-source streaming media framework (base layer)
2. **TAPPAS** - Hailo's C/C++ GStreamer plugins for hardware inference
   - `HailoNet` - Neural network inference on Hailo device
   - `HailoFilter` - C++ post-processing
   - `HailoOverlay` - Visualization
   - `HailoTracker` - Object tracking
   - `HailoCropper/Aggregator` - Cascading networks
   - `HailoTileCropper/Aggregator` - Tiling support
3. **Hailo Apps Python Layer** - This repository's framework

### Key Framework Components

- **`hailo_apps/python/core/gstreamer/gstreamer_app.py`** - `GStreamerApp` class: pipeline lifecycle, bus messages, callback integration
- **`hailo_apps/python/core/gstreamer/gstreamer_helper_pipelines.py`** - Pipeline builder functions: `SOURCE_PIPELINE()`, `INFERENCE_PIPELINE()`, `DISPLAY_PIPELINE()`, etc.
- **`hailo_apps/python/core/gstreamer/gstreamer_app.py:app_callback_class`** - Base class for user callbacks with automatic frame counting

### Application Types

| Type | Location | Purpose |
|------|----------|---------|
| Pipeline Apps | `hailo_apps/python/pipeline_apps/` | GStreamer-based real-time video processing |
| GenAI Apps | `hailo_apps/python/gen_ai_apps/` | Voice assistants, VLM chat (Hailo-10H) |
| Standalone Apps | `hailo_apps/python/standalone_apps/` | HailoRT learning examples |
| C++ Apps | `hailo_apps/cpp/` | C++ standalone examples |

### Pipeline App Structure

Each pipeline app follows this pattern:
```
app_name/
├── app_name.py           # User callback + main()
├── app_name_pipeline.py  # GStreamerApp subclass
└── README.md
```

## Development Patterns

### Basic Callback Pattern
```python
from hailo_apps.python.core.gstreamer.gstreamer_app import app_callback_class
import hailo

class user_app_callback_class(app_callback_class):
    def __init__(self):
        super().__init__()
        # Add custom state

def app_callback(element, buffer, user_data):
    frame_idx = user_data.get_count()  # Framework auto-increments
    roi = hailo.get_roi_from_buffer(buffer)
    detections = roi.get_objects_typed(hailo.HAILO_DETECTION)
    # Process detections...
```

**Note**: Frame counting is automatic - do NOT call `user_data.increment()` in callbacks.

### Custom Pipeline Pattern
```python
from hailo_apps.python.core.gstreamer.gstreamer_app import GStreamerApp
from hailo_apps.python.core.gstreamer.gstreamer_helper_pipelines import (
    SOURCE_PIPELINE, INFERENCE_PIPELINE, DISPLAY_PIPELINE
)

class MyApp(GStreamerApp):
    def get_pipeline_string(self):
        return f"{SOURCE_PIPELINE(...)} ! {INFERENCE_PIPELINE(...)} ! {DISPLAY_PIPELINE()}"
```

### Logging
```python
from hailo_apps.python.core.common.hailo_logger import get_logger
hailo_logger = get_logger(__name__)
```

## Configuration System

YAML configs in `hailo_apps/config/`:
- `config.yaml` - Installation/runtime settings
- `resources_config.yaml` - Model/video/image resources
- `test_definition_config.yaml` - Test framework

Access via:
```python
from hailo_apps.config import config_manager
apps = config_manager.get_available_apps()
models = config_manager.get_default_models("detection", "hailo8")
```

## Code Style

- **Formatter**: Ruff
- **Line length**: 100
- **Quote style**: Double quotes
- **Imports**: Absolute imports from `hailo_apps` package
- **Rules**: E, F, I, B, UP, C4, W, RUF (see pyproject.toml)

Pre-commit hooks activate the venv automatically.

## Adding a New Pipeline App

1. Create directory: `hailo_apps/python/pipeline_apps/app_name/`
2. Create `app_name.py` with callback and `main()`
3. Create `app_name_pipeline.py` with `GStreamerApp` subclass
4. Add README.md
5. Register in `hailo_apps/config/resources_config.yaml`
6. Add entry point in `pyproject.toml` under `[project.scripts]`

## Key Documentation

- [App Development Guide](doc/developer_guide/app_development.md) - Primary development reference
- [GStreamer Helper Pipelines](doc/developer_guide/gstreamer_helper_pipelines.md) - Pipeline builder reference
- [Writing Postprocess](doc/developer_guide/writing_postprocess.md) - C++ post-processing
- [GstShark Debugging](doc/developer_guide/debugging_with_gst_shark.md) - Pipeline debugging
