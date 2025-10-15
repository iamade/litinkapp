#!/usr/bin/env python3
"""
Verification script for Celery setup
Run this to check if all components are correctly configured
"""

import sys
import os

# Add backend to path
sys.path.insert(0, os.path.dirname(__file__))

def check_imports():
    """Check if all required imports work"""
    print("✓ Checking imports...")
    try:
        from app.tasks.celery_app import celery_app
        print("  ✓ Celery app imports successfully")
        
        from app.tasks.image_tasks import generate_scene_image_task, generate_character_image_task
        print("  ✓ Image tasks import successfully")
        
        return True
    except Exception as e:
        print(f"  ✗ Import error: {e}")
        return False

def check_task_registration():
    """Check if tasks are registered with Celery"""
    print("\n✓ Checking task registration...")
    try:
        from app.tasks.celery_app import celery_app
        
        registered_tasks = list(celery_app.tasks.keys())
        scene_task = 'app.tasks.image_tasks.generate_scene_image_task'
        char_task = 'app.tasks.image_tasks.generate_character_image_task'
        
        if scene_task in registered_tasks:
            print(f"  ✓ Scene image task registered: {scene_task}")
        else:
            print(f"  ✗ Scene image task NOT registered")
            return False
            
        if char_task in registered_tasks:
            print(f"  ✓ Character image task registered: {char_task}")
        else:
            print(f"  ✗ Character image task NOT registered")
            
        return True
    except Exception as e:
        print(f"  ✗ Registration check error: {e}")
        return False

def check_redis_config():
    """Check Redis configuration"""
    print("\n✓ Checking Redis configuration...")
    try:
        from app.tasks.celery_app import celery_app
        
        broker_url = celery_app.conf.broker_url
        result_backend = celery_app.conf.result_backend
        
        print(f"  ✓ Broker URL: {broker_url}")
        print(f"  ✓ Result backend: {result_backend}")
        
        return True
    except Exception as e:
        print(f"  ✗ Config check error: {e}")
        return False

def check_api_endpoint():
    """Check if API endpoint is using the task"""
    print("\n✓ Checking API endpoint configuration...")
    try:
        with open('app/api/v1/chapters.py', 'r') as f:
            content = f.read()
            
        if 'generate_scene_image_task.delay(' in content:
            print("  ✓ API endpoint uses .delay() for async execution")
        else:
            print("  ✗ API endpoint NOT using .delay() - still synchronous")
            return False
            
        if 'ImageGenerationQueuedResponse' in content:
            print("  ✓ API returns queued response")
        else:
            print("  ✗ API NOT returning queued response")
            return False
            
        return True
    except Exception as e:
        print(f"  ✗ Endpoint check error: {e}")
        return False

def main():
    print("="*60)
    print("Celery Setup Verification")
    print("="*60)
    
    checks = [
        ("Imports", check_imports()),
        ("Task Registration", check_task_registration()),
        ("Redis Config", check_redis_config()),
        ("API Endpoint", check_api_endpoint()),
    ]
    
    print("\n" + "="*60)
    print("Summary")
    print("="*60)
    
    all_passed = True
    for check_name, passed in checks:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{check_name:<20} {status}")
        if not passed:
            all_passed = False
    
    print("="*60)
    
    if all_passed:
        print("\n✓ All checks passed!")
        print("\nNext step: Start Celery workers")
        print("  docker-compose up -d celery")
        print("\nOr manually:")
        print("  celery -A app.tasks.celery_app worker --loglevel=info")
        return 0
    else:
        print("\n✗ Some checks failed. Review the errors above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
