"""
Simple test script to verify pipeline system works correctly.
Run this to verify Phase 1 implementation.
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from modules.pipeline_engine import Pipeline, StepContext
from modules.pipeline_serializer import PipelineSerializer, PresetLibrary
from pipeline_steps import ConversionStep, ExtractAudioStep, NormalizeAudioStep, StepRegistry


def test_basic_pipeline():
    """Test 1: Create and execute a simple pipeline"""
    print("\n=== Test 1: Basic Pipeline ===")
    
    # Create a simple conversion pipeline
    pipeline = Pipeline(name="Test: Image Conversion")
    
    step1 = ConversionStep(step_id="convert", name="Convert to PNG")
    step1.configure(target_format="png", quality="high")
    
    pipeline.add_step(step1)
    
    # Validate
    valid, msg = pipeline.validate()
    print(f"Pipeline valid: {valid} - {msg}")
    
    return pipeline


def test_multi_step_pipeline():
    """Test 2: Create multi-step pipeline"""
    print("\n=== Test 2: Multi-Step Pipeline ===")
    
    pipeline = Pipeline(name="Test: Audio Processing")
    pipeline.description = "Extract audio, normalize, convert to MP3"
    
    # Step 1: Extract audio
    extract = ExtractAudioStep()
    extract.configure(audio_format="wav", audio_quality="high")
    pipeline.add_step(extract)
    
    # Step 2: Normalize
    normalize = NormalizeAudioStep()
    normalize.configure(target_lufs=-16.0)
    pipeline.add_step(normalize)
    
    # Step 3: Convert to MP3
    convert = ConversionStep(step_id="final_convert", name="Convert to MP3")
    convert.configure(target_format="mp3", quality="high")
    pipeline.add_step(convert)
    
    print(f"Pipeline '{pipeline.name}' has {len(pipeline.steps)} steps")
    for i, step in enumerate(pipeline.steps, 1):
        print(f"  Step {i}: {step.name} ({step.__class__.__name__})")
    
    return pipeline


def test_serialization():
    """Test 3: Save and load pipeline"""
    print("\n=== Test 3: Serialization ===")
    
    pipeline = test_multi_step_pipeline()
    
    # Save to JSON
    test_file = "test_pipeline.json"
    success = PipelineSerializer.save_pipeline(pipeline, test_file)
    print(f"Save successful: {success}")
    
    if success:
        # Load it back
        loaded = PipelineSerializer.load_pipeline(test_file)
        if loaded:
            print(f"Loaded pipeline: '{loaded.name}'")
            print(f"  Steps: {len(loaded.steps)}")
            print(f"  Description: {loaded.description}")
        
        # Cleanup
        os.remove(test_file)
    
    return success


def test_preset_library():
    """Test 4: Preset library management"""
    print("\n=== Test 4: Preset Library ===")
    
    library = PresetLibrary()
    presets = library.list_presets()
    
    print(f"Found {len(presets)} presets:")
    for preset in presets:
        print(f"  - {preset['name']}: {preset['description'][:50]}...")
    
    # Try loading one
    if presets:
        first_preset = library.get_preset(presets[0]['filename'].replace('.json', ''))
        if first_preset:
            print(f"\nLoaded preset: {first_preset.name}")
            print(f"  Steps: {len(first_preset.steps)}")
    
    return len(presets) > 0


def test_step_registry():
    """Test 5: Step registry"""
    print("\n=== Test 5: Step Registry ===")
    
    available = StepRegistry.get_available_steps()
    print(f"Available step types: {', '.join(available)}")
    
    # Test creating from dict
    step_data = {
        'type': 'ConversionStep',
        'step_id': 'test_convert',
        'name': 'Test Conversion',
        'config': {'target_format': 'mp3', 'quality': 'high'}
    }
    
    step = StepRegistry.create_step(step_data)
    print(f"Created step from dict: {step.name} ({step.target_format})")
    
    return True


def main():
    """Run all tests"""
    print("=" * 50)
    print("   Pipeline System Verification Tests")
    print("=" * 50)
    
    results = []
    
    try:
        results.append(("Basic Pipeline", test_basic_pipeline() is not None))
        results.append(("Multi-Step Pipeline", test_multi_step_pipeline() is not None))
        results.append(("Serialization", test_serialization()))
        results.append(("Preset Library", test_preset_library()))
        results.append(("Step Registry", test_step_registry()))
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Summary
    print("\n" + "=" * 50)
    print("   Test Results")
    print("=" * 50)
    
    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} - {test_name}")
    
    all_passed = all(r[1] for r in results)
    
    if all_passed:
        print("\n🎉 All tests passed! Pipeline system is working correctly.")
    else:
        print("\n⚠️  Some tests failed. Check the output above.")
    
    return all_passed


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
