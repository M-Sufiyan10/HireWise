"""
Test Suite for Resume Database API
===================================

Run this file to test all database operations.
"""

from Db import ResumeDatabase
from pymongo.errors import DuplicateKeyError, PyMongoError
import sys


def test_connection():
    """Test database connection"""
    print("\n" + "="*60)
    print("TEST 1: Database Connection")
    print("="*60)
    
    try:
        db = ResumeDatabase()
        print("✓ Successfully connected to MongoDB")
        db.close_connection()
        print("✓ Connection closed successfully")
        return True
    except Exception as e:
        print(f"✗ Connection failed: {e}")
        return False


def test_insert():
    """Test insert operation"""
    print("\n" + "="*60)
    print("TEST 2: Insert Resume")
    print("="*60)
    
    db = ResumeDatabase()
    
    test_resume = {
        '_id': 'test_resume_001',
        'name': 'Alice Johnson',
        'contact_information': '+1-234-567-8900',
        'email_address': 'alice@example.com',
        'linkedin_profile': 'linkedin.com/in/alice',
        'skills': ['Python', 'MongoDB', 'FastAPI', 'React'],
        'experience': [
            {
                'company': 'Tech Corp',
                'position': 'Senior Developer',
                'duration': '2020-2023',
                'description': 'Led development team'
            }
        ],
        'education': [
            {
                'degree': 'BS Computer Science',
                'university': 'MIT',
                'year': 2020
            }
        ],
        'projects': [
            {
                'name': 'E-commerce Platform',
                'description': 'Built scalable e-commerce solution',
                'technologies': ['Python', 'MongoDB', 'React']
            }
        ],
        'extras': ['AWS Certified', 'Published 3 research papers']
    }
    
    try:
        # Clean up if exists
        db.delete_resume('test_resume_001')
        
        result = db.insert_resume(test_resume)
        print(f"✓ Resume inserted: {result['id']}")
        print(f"  Message: {result['message']}")
        
        # Verify insertion
        retrieved = db.get_resume('test_resume_001')
        if retrieved and retrieved['name'] == 'Alice Johnson':
            print("✓ Resume verified in database")
            return True
        else:
            print("✗ Resume not found after insertion")
            return False
            
    except DuplicateKeyError:
        print("✗ Resume with this ID already exists")
        return False
    except Exception as e:
        print(f"✗ Insert failed: {e}")
        return False
    finally:
        db.close_connection()


def test_get():
    """Test get operation"""
    print("\n" + "="*60)
    print("TEST 3: Get Resume")
    print("="*60)
    
    db = ResumeDatabase()
    
    try:
        resume = db.get_resume('test_resume_001')
        if resume:
            print(f"✓ Resume retrieved: {resume['name']}")
            print(f"  Email: {resume.get('email_address', 'N/A')}")
            print(f"  Skills: {', '.join(resume.get('skills', []))}")
            return True
        else:
            print("✗ Resume not found")
            return False
    except Exception as e:
        print(f"✗ Get failed: {e}")
        return False
    finally:
        db.close_connection()


def test_update():
    """Test update operation"""
    print("\n" + "="*60)
    print("TEST 4: Update Resume")
    print("="*60)
    
    db = ResumeDatabase()
    
    try:
        # Add a new skill
        result = db.update_resume('test_resume_001', {
            'skills': ['Python', 'MongoDB', 'FastAPI', 'React', 'Docker']
        })
        
        print(f"✓ Update result:")
        print(f"  Matched: {result['matched_count']}")
        print(f"  Modified: {result['modified_count']}")
        
        # Verify update
        resume = db.get_resume('test_resume_001')
        if 'Docker' in resume.get('skills', []):
            print("✓ Update verified - Docker skill added")
            return True
        else:
            print("✗ Update not reflected")
            return False
            
    except Exception as e:
        print(f"✗ Update failed: {e}")
        return False
    finally:
        db.close_connection()


def test_search():
    """Test search operation"""
    print("\n" + "="*60)
    print("TEST 5: Search Resumes")
    print("="*60)
    
    db = ResumeDatabase()
    
    try:
        # Search for Python developers
        results = db.search_resumes({
            'skills': {'$in': ['Python']}
        })
        
        print(f"✓ Found {len(results)} Python developer(s)")
        for resume in results:
            print(f"  - {resume.get('name', 'Unknown')}")
        
        return len(results) > 0
        
    except Exception as e:
        print(f"✗ Search failed: {e}")
        return False
    finally:
        db.close_connection()


def test_ranking():
    """Test ranking operation"""
    print("\n" + "="*60)
    print("TEST 6: Add Ranking")
    print("="*60)
    
    db = ResumeDatabase()
    
    try:
        ranking_data = {
            'skills': {
                'score': 38,
                'justification': 'Strong Python and MongoDB skills'
            },
            'experience': {
                'score': 32,
                'justification': 'Senior developer with leadership experience'
            },
            'projects': {
                'score': 9,
                'justification': 'Impressive e-commerce platform project'
            },
            'other_relevant_skills': {
                'score': 8,
                'justification': 'Cloud expertise with AWS'
            },
            'extras': {
                'score': 5,
                'justification': 'AWS certification and publications'
            },
            'total_score': 92
        }
        
        job_description = "Looking for Senior Full Stack Developer with Python and MongoDB"
        
        result = db.add_ranking('test_resume_001', ranking_data, job_description)
        
        if result['success']:
            print(f"✓ Ranking added: Total Score = {ranking_data['total_score']}/100")
            
            # Verify ranking
            resume = db.get_resume('test_resume_001')
            if 'rankings' in resume and len(resume['rankings']) > 0:
                print(f"✓ Ranking verified - {len(resume['rankings'])} ranking(s) in database")
                return True
            else:
                print("✗ Ranking not found in database")
                return False
        else:
            print("✗ Ranking addition failed")
            return False
            
    except Exception as e:
        print(f"✗ Ranking failed: {e}")
        return False
    finally:
        db.close_connection()


def test_get_all():
    """Test get all with pagination"""
    print("\n" + "="*60)
    print("TEST 7: Get All Resumes (Pagination)")
    print("="*60)
    
    db = ResumeDatabase()
    
    try:
        resumes = db.get_all_resumes(limit=5, skip=0, sort_by='created_at', ascending=False)
        print(f"✓ Retrieved {len(resumes)} resume(s)")
        
        for i, resume in enumerate(resumes, 1):
            print(f"  {i}. {resume.get('name', 'Unknown')} - Created: {resume.get('created_at', 'N/A')}")
        
        return True
        
    except Exception as e:
        print(f"✗ Get all failed: {e}")
        return False
    finally:
        db.close_connection()


def test_count():
    """Test count operation"""
    print("\n" + "="*60)
    print("TEST 8: Count Resumes")
    print("="*60)
    
    db = ResumeDatabase()
    
    try:
        total_count = db.get_resume_count()
        python_count = db.get_resume_count({'skills': {'$in': ['Python']}})
        
        print(f"✓ Total resumes: {total_count}")
        print(f"✓ Python developers: {python_count}")
        
        return True
        
    except Exception as e:
        print(f"✗ Count failed: {e}")
        return False
    finally:
        db.close_connection()


def test_bulk_insert():
    """Test bulk insert"""
    print("\n" + "="*60)
    print("TEST 9: Bulk Insert")
    print("="*60)
    
    db = ResumeDatabase()
    
    try:
        resumes = [
            {
                'name': 'Bob Smith',
                'email_address': 'bob@example.com',
                'skills': ['JavaScript', 'Node.js', 'React'],
                'experience': [],
                'education': [],
                'projects': [],
                'extras': []
            },
            {
                'name': 'Carol White',
                'email_address': 'carol@example.com',
                'skills': ['Java', 'Spring Boot', 'AWS'],
                'experience': [],
                'education': [],
                'projects': [],
                'extras': []
            }
        ]
        
        result = db.bulk_insert_resumes(resumes)
        print(f"✓ {result['message']}")
        print(f"  IDs: {', '.join(result['inserted_ids'][:2])}...")
        
        return result['success']
        
    except Exception as e:
        print(f"✗ Bulk insert failed: {e}")
        return False
    finally:
        db.close_connection()


def test_delete():
    """Test delete operation"""
    print("\n" + "="*60)
    print("TEST 10: Delete Resume")
    print("="*60)
    
    db = ResumeDatabase()
    
    try:
        result = db.delete_resume('test_resume_001')
        
        if result['success']:
            print(f"✓ Resume deleted")
            print(f"  Deleted count: {result['deleted_count']}")
            
            # Verify deletion
            resume = db.get_resume('test_resume_001')
            if resume is None:
                print("✓ Deletion verified - resume not found")
                return True
            else:
                print("✗ Resume still exists after deletion")
                return False
        else:
            print("✗ Delete failed")
            return False
            
    except Exception as e:
        print(f"✗ Delete failed: {e}")
        return False
    finally:
        db.close_connection()


def run_all_tests():
    """Run all tests"""
    print("\n" + "#"*60)
    print("# Resume Database API Test Suite")
    print("#"*60)
    
    tests = [
        test_connection,
        test_insert,
        test_get,
        test_update,
        test_search,
        test_ranking,
        test_get_all,
        test_count,
        test_bulk_insert,
        test_delete
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"\n✗ Test crashed: {e}")
            results.append(False)
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    passed = sum(results)
    total = len(results)
    
    print(f"Passed: {passed}/{total}")
    print(f"Failed: {total - passed}/{total}")
    
    if passed == total:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    exit_code = run_all_tests()
    sys.exit(exit_code)

