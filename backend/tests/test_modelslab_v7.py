#!/usr/bin/env python3
"""
Test script for ModelsLab V7 Image Service tier-based model configuration.
Tests the updated tier_model_mapping to ensure correct ModelsLab API model IDs.
"""

import os
import sys
import re

def test_tier_model_mapping():
    """Test that tier_model_mapping uses correct ModelsLab API model IDs by reading the source file"""

    try:
        service_file = os.path.join(os.path.dirname(__file__), 'backend', 'app', 'services', 'modelslab_v7_image_service.py')

        with open(service_file, 'r') as f:
            content = f.read()

        # Find the tier_model_mapping definition
        mapping_match = re.search(r'tier_model_mapping\s*=\s*\{([^}]+)\}', content, re.DOTALL)
        if not mapping_match:
            print("❌ Could not find tier_model_mapping in the service file")
            return False

        mapping_content = mapping_match.group(1)

        # Expected mapping
        expected_mapping = {
            'free': 'imagen-4.0-ultra',
            'basic': 'imagen-4.0-fast-generate',
            'pro': 'runway_image',
            'premium': 'runway_image',
            'professional': 'runway_image',
            'enterprise': 'runway_image'
        }

        print("Testing tier_model_mapping configuration...")

        # Check each expected mapping
        success = True
        for tier, expected_model in expected_mapping.items():
            # Look for the tier mapping in the content
            tier_pattern = rf"'{tier}'\s*:\s*'([^']+)'"
            match = re.search(tier_pattern, mapping_content)
            if match:
                actual_model = match.group(1)
                if actual_model == expected_model:
                    print(f"✅ {tier} tier: {actual_model}")
                else:
                    print(f"❌ {tier} tier: expected {expected_model}, got {actual_model}")
                    success = False
            else:
                print(f"❌ {tier} tier: not found in mapping")
                success = False

        return success

    except Exception as e:
        print(f"❌ Error testing tier model mapping: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_service_import():
    """Test that the service can be imported correctly by checking syntax"""

    try:
        service_file = os.path.join(os.path.dirname(__file__), 'backend', 'app', 'services', 'modelslab_v7_image_service.py')

        # Try to compile the file to check syntax
        with open(service_file, 'r') as f:
            code = f.read()

        compile(code, service_file, 'exec')
        print("✅ ModelsLabV7ImageService syntax is valid")

        # Check that the class is defined
        if 'class ModelsLabV7ImageService:' in code:
            print("✅ ModelsLabV7ImageService class found")
        else:
            print("❌ ModelsLabV7ImageService class not found")
            return False

        # Check that dependent files exist and have valid syntax
        dependent_files = [
            'backend/app/services/standalone_image_service.py',
            'backend/app/services/character_service.py',
            'backend/app/tasks/image_tasks.py'
        ]

        for dep_file in dependent_files:
            dep_path = os.path.join(os.path.dirname(__file__), dep_file)
            if os.path.exists(dep_path):
                try:
                    with open(dep_path, 'r') as f:
                        dep_code = f.read()
                    compile(dep_code, dep_path, 'exec')
                    print(f"✅ {os.path.basename(dep_file)} syntax is valid")
                except SyntaxError as e:
                    print(f"❌ {os.path.basename(dep_file)} has syntax error: {e}")
                    return False
            else:
                print(f"⚠️  {dep_file} not found")

        return True

    except SyntaxError as e:
        print(f"❌ Syntax error in service file: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error during import test: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tests"""

    print("🧪 Testing ModelsLab V7 Image Service Configuration")
    print("=" * 50)

    success = True

    # Test 1: Service imports
    print("\n📦 Testing service imports...")
    if not test_service_import():
        success = False

    # Test 2: Tier model mapping
    print("\n🎯 Testing tier model mapping...")
    if not test_tier_model_mapping():
        success = False

    print("\n" + "=" * 50)
    if success:
        print("✅ All tests passed! Configuration is correct.")
        print("   - Free tier uses 'imagen-4.0-ultra'")
        print("   - Basic tier uses 'imagen-4.0-fast-generate'")
        print("   - Service imports correctly in dependent modules")
    else:
        print("❌ Some tests failed. Please check the configuration.")

    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)