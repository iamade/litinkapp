#!/usr/bin/env python3
"""
Test script to verify:
1. Database schema has chapter_id column
2. Celery worker is running and can process tasks
3. Scene image generation task is registered
"""

import asyncio
import sys
from app.core.database import get_supabase
from app.tasks.celery_app import celery_app
from app.tasks.image_tasks import generate_scene_image_task

def test_database_schema():
    """Test that chapter_id column exists in image_generations table"""
    print("\n" + "="*60)
    print("TEST 1: Database Schema Verification")
    print("="*60)

    try:
        supabase = get_supabase()

        # Query to check if chapter_id column exists
        result = supabase.rpc('exec_sql', {
            'query': """
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_name = 'image_generations'
                AND column_name IN ('chapter_id', 'retry_count', 'progress', 'last_attempted_at')
                ORDER BY column_name
            """
        }).execute()

        if result.data:
            print("\n✅ Required columns found in image_generations table:")
            for col in result.data:
                print(f"  - {col['column_name']} ({col['data_type']}) - Nullable: {col['is_nullable']}")
            return True
        else:
            print("\n❌ Required columns NOT found in image_generations table")
            return False

    except Exception as e:
        print(f"\n❌ Database test failed: {str(e)}")
        return False


def test_celery_connection():
    """Test that Celery can connect to Redis broker"""
    print("\n" + "="*60)
    print("TEST 2: Celery Broker Connection")
    print("="*60)

    try:
        # Try to ping the broker
        celery_app.control.inspect().stats()
        print("\n✅ Celery broker connection successful")
        print(f"   Broker URL: {celery_app.conf.broker_url}")
        return True
    except Exception as e:
        print(f"\n❌ Celery broker connection failed: {str(e)}")
        print(f"   Broker URL: {celery_app.conf.broker_url}")
        return False


def test_celery_workers():
    """Test that Celery workers are running"""
    print("\n" + "="*60)
    print("TEST 3: Celery Workers Status")
    print("="*60)

    try:
        inspect = celery_app.control.inspect()
        stats = inspect.stats()

        if stats:
            print(f"\n✅ Found {len(stats)} active Celery worker(s):")
            for worker_name, worker_stats in stats.items():
                print(f"   - {worker_name}")
                print(f"     Total tasks: {worker_stats.get('total', 'N/A')}")
            return True
        else:
            print("\n⚠️  No active Celery workers found")
            print("   Make sure the Celery worker container is running:")
            print("   docker-compose ps celery")
            return False

    except Exception as e:
        print(f"\n❌ Worker status check failed: {str(e)}")
        return False


def test_registered_tasks():
    """Test that image tasks are registered with Celery"""
    print("\n" + "="*60)
    print("TEST 4: Registered Tasks")
    print("="*60)

    try:
        inspect = celery_app.control.inspect()
        registered = inspect.registered()

        if registered:
            all_tasks = []
            for worker, tasks in registered.items():
                all_tasks.extend(tasks)

            # Check for our specific tasks
            image_tasks = [t for t in all_tasks if 'image' in t.lower()]
            scene_task_found = any('generate_scene_image_task' in t for t in all_tasks)
            character_task_found = any('generate_character_image_task' in t for t in all_tasks)

            print(f"\n✅ Found {len(all_tasks)} registered tasks")
            print(f"   Image-related tasks: {len(image_tasks)}")
            print(f"   Scene task registered: {'✅' if scene_task_found else '❌'}")
            print(f"   Character task registered: {'✅' if character_task_found else '❌'}")

            if image_tasks:
                print("\n   Image tasks:")
                for task in image_tasks:
                    print(f"   - {task}")

            return scene_task_found and character_task_found
        else:
            print("\n⚠️  Could not retrieve registered tasks")
            return False

    except Exception as e:
        print(f"\n❌ Task registration check failed: {str(e)}")
        return False


def test_task_execution():
    """Test that we can queue a task (without actually executing it)"""
    print("\n" + "="*60)
    print("TEST 5: Task Queueing Test")
    print("="*60)

    try:
        # Try to get the task signature
        task_sig = generate_scene_image_task.signature()
        print(f"\n✅ Task signature created successfully")
        print(f"   Task name: {generate_scene_image_task.name}")
        print(f"   Task bound: {generate_scene_image_task.bind}")

        # Note: We're NOT actually calling .delay() here to avoid creating a real task
        print("\n   Note: Not actually queueing a task to avoid side effects")
        print("   In production, tasks would be queued with .delay() or .apply_async()")

        return True

    except Exception as e:
        print(f"\n❌ Task queueing test failed: {str(e)}")
        return False


def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("CELERY & DATABASE INTEGRATION TEST")
    print("="*60)

    results = {
        "Database Schema": test_database_schema(),
        "Celery Connection": test_celery_connection(),
        "Celery Workers": test_celery_workers(),
        "Registered Tasks": test_registered_tasks(),
        "Task Queueing": test_task_execution(),
    }

    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)

    passed = sum(results.values())
    total = len(results)

    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name}")

    print(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        print("\n✅ All tests passed! System is ready for scene image generation.")
        return 0
    else:
        print("\n⚠️  Some tests failed. Please review the output above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
