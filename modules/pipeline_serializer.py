"""
Pipeline Serialization - Save/Load pipelines as JSON

Handles preset library management and community preset import/export.
"""
import json
import os
from pathlib import Path
from typing import Dict, List, Optional
from modules.pipeline_engine import Pipeline


class PipelineSerializer:
    """
    Serialize and deserialize pipelines to/from JSON format.
    """
    
    @staticmethod
    def save_pipeline(pipeline: Pipeline, filepath: str) -> bool:
        """
        Save pipeline to JSON file.
        
        Args:
            pipeline: Pipeline to save
            filepath: Output JSON file path
            
        Returns:
            Success status
        """
        try:
            data = pipeline.to_dict()
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                
            return True
        except Exception as e:
            print(f"Error saving pipeline: {e}")
            return False
    
    @staticmethod
    def load_pipeline(filepath: str) -> Optional[Pipeline]:
        """
        Load pipeline from JSON file.
        
        Args:
            filepath: JSON file path
            
        Returns:
            Pipeline instance or None on error
        """
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            pipeline = Pipeline(name=data.get('name', 'Loaded Pipeline'))
            pipeline.description = data.get('description', '')
            
            # Load steps using StepRegistry
            from pipeline_steps import StepRegistry
            
            for step_data in data.get('steps', []):
                try:
                    step = StepRegistry.create_step(step_data)
                    pipeline.add_step(step)
                except Exception as e:
                    print(f"Warning: Could not load step {step_data.get('name')}: {e}")
            
            return pipeline
        except Exception as e:
            print(f"Error loading pipeline: {e}")
            return None


class PresetLibrary:
    """
    Built-in presets ship read-only with the app; presets the user creates are
    stored in the per-user data folder (Program Files is not writable).
    """
    def __init__(self, presets_dir: str = None):
        from modules.paths import resource, user_path
        if presets_dir is None:
            self.builtin_dir = Path(resource('presets'))
            self.presets_dir = Path(user_path('presets'))
        else:
            self.builtin_dir = self.presets_dir = Path(presets_dir)
        try:
            self.presets_dir.mkdir(parents=True, exist_ok=True)
        except OSError:
            pass

    def _files(self) -> Dict[str, Path]:
        files = {}
        for folder in (self.builtin_dir, self.presets_dir):  # user presets win
            if folder.is_dir():
                for f in folder.glob('*.json'):
                    files[f.stem] = f
        return files

    def list_presets(self) -> List[Dict]:
        presets = []
        for stem, preset_file in self._files().items():
            try:
                with open(preset_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                presets.append({
                    'filename': preset_file.name,
                    'name': data.get('name', stem),
                    'description': data.get('description', ''),
                    'path': str(preset_file),
                    'builtin': preset_file.parent == self.builtin_dir and self.builtin_dir != self.presets_dir,
                })
            except Exception as e:
                print(f"Warning: Could not read preset {preset_file}: {e}")
        return sorted(presets, key=lambda x: x['name'].lower())

    def get_preset(self, preset_name: str) -> Optional[Pipeline]:
        preset_file = self._files().get(preset_name)
        if preset_file is None:
            return None
        return PipelineSerializer.load_pipeline(str(preset_file))

    def save_preset(self, pipeline: Pipeline, preset_name: str) -> bool:
        """
        Save a pipeline as a preset.
        
        Args:
            pipeline: Pipeline to save
            preset_name: Name for the preset (without .json)
            
        Returns:
            Success status
        """
        preset_file = self.presets_dir / f"{preset_name}.json"
        return PipelineSerializer.save_pipeline(pipeline, str(preset_file))
    
    def delete_preset(self, preset_name: str) -> bool:
        """
        Delete a preset.
        
        Args:
            preset_name: Name of preset to delete
            
        Returns:
            Success status
        """
        preset_file = self.presets_dir / f"{preset_name}.json"
        
        try:
            if preset_file.exists():
                preset_file.unlink()
                return True
            return False
        except Exception as e:
            print(f"Error deleting preset: {e}")
            return False
    
    def export_preset(self, preset_name: str, export_path: str) -> bool:
        """
        Export a preset to a different location.
        
        Args:
            preset_name: Name of preset to export
            export_path: Destination file path
            
        Returns:
            Success status
        """
        import shutil
        
        preset_file = self.presets_dir / f"{preset_name}.json"
        
        if not preset_file.exists():
            return False
            
        try:
            shutil.copy2(preset_file, export_path)
            return True
        except Exception as e:
            print(f"Error exporting preset: {e}")
            return False
    
    def import_preset(self, import_path: str, preset_name: str = None) -> bool:
        """
        Import a preset from external file.
        
        Args:
            import_path: Source file path
            preset_name: Optional custom name (defaults to original filename)
            
        Returns:
            Success status
        """
        import shutil
        
        if not os.path.exists(import_path):
            return False
            
        if preset_name is None:
            preset_name = Path(import_path).stem
            
        dest_file = self.presets_dir / f"{preset_name}.json"
        
        try:
            # Validate it's a valid pipeline JSON
            pipeline = PipelineSerializer.load_pipeline(import_path)
            if pipeline is None:
                return False
                
            # Copy to presets directory
            shutil.copy2(import_path, dest_file)
            return True
        except Exception as e:
            print(f"Error importing preset: {e}")
            return False
