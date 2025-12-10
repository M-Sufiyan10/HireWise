"""
Professional MongoDB CRUD API Usage Examples
=============================================

This file demonstrates how to use the ResumeDatabase API
with various operations and best practices.
"""

from Db import ResumeDatabase
from pymongo.errors import DuplicateKeyError, PyMongoError


# ============================================================================
# BASIC USAGE - Using the new class-based API (Recommended)
# ============================================================================

def example_basic_usage():
    """Example of basic CRUD operations"""
    
    # Initialize database connection
    db = ResumeDatabase()
    
    # 1. INSERT a new resume
    resume_data = {
        '_id': 'resume_001',
        'name': 'John Doe',
        'skills': ['Python', 'JavaScript', 'MongoDB'],
        'experience': [
            {
                'company': 'Tech Corp',
                'position': 'Senior Developer',
                'duration': '2020-2023'
            }
        ],
        'education': [
            {
                'degree': 'BS Computer Science',
                'university': 'MIT',
                'year': 2020
            }
        ],
        'projects': [],
        'extras': []
    }
    
    try:
        result = db.insert_resume(resume_data)
        print(f"✓ Insert: {result}")
    except DuplicateKeyError:
        print("Resume already exists!")
    
    # 2. GET a resume by ID
    resume = db.get_resume('resume_001')
    if resume:
        print(f"✓ Retrieved: {resume['name']}")
    
    # 3. UPDATE a resume
    update_result = db.update_resume(
        'resume_001',
        {'skills': ['Python', 'JavaScript', 'MongoDB', 'React']}
    )
    print(f"✓ Update: {update_result}")
    
    # 4. DELETE a resume
    delete_result = db.delete_resume('resume_001')
    print(f"✓ Delete: {delete_result}")
    
    # Close connection when done
    db.close_connection()


# ============================================================================
# ADVANCED OPERATIONS
# ============================================================================

def example_advanced_operations():
    """Example of advanced database operations"""
    
    db = ResumeDatabase()
    
    # Get all resumes with pagination
    resumes = db.get_all_resumes(limit=10, skip=0, sort_by='created_at', ascending=False)
    print(f"✓ Retrieved {len(resumes)} resumes")
    
    # Search resumes with custom query
    python_devs = db.search_resumes({
        'skills': {'$in': ['Python']},
        'experience.position': {'$regex': 'Developer', '$options': 'i'}
    })
    print(f"✓ Found {len(python_devs)} Python developers")
    
    # Get count of resumes
    total_count = db.get_resume_count()
    print(f"✓ Total resumes in database: {total_count}")
    
    # Update with upsert (insert if not exists)
    result = db.update_resume(
        'resume_new',
        {'name': 'Jane Smith', 'skills': ['Java', 'Spring']},
        upsert=True
    )
    print(f"✓ Upsert: {result}")
    
    db.close_connection()


# ============================================================================
# BULK OPERATIONS
# ============================================================================

def example_bulk_operations():
    """Example of bulk insert operations"""
    
    db = ResumeDatabase()
    
    # Prepare multiple resumes
    resumes = [
        {
            'name': 'Alice Johnson',
            'skills': ['Python', 'Django', 'PostgreSQL'],
            'experience': [],
            'education': [],
            'projects': [],
            'extras': []
        },
        {
            'name': 'Bob Smith',
            'skills': ['JavaScript', 'Node.js', 'React'],
            'experience': [],
            'education': [],
            'projects': [],
            'extras': []
        },
        {
            'name': 'Carol White',
            'skills': ['Java', 'Spring Boot', 'AWS'],
            'experience': [],
            'education': [],
            'projects': [],
            'extras': []
        }
    ]
    
    # Bulk insert
    try:
        result = db.bulk_insert_resumes(resumes)
        print(f"✓ Bulk Insert: {result['message']}")
        print(f"  Inserted IDs: {result['inserted_ids']}")
    except PyMongoError as e:
        print(f"✗ Bulk insert failed: {e}")
    
    db.close_connection()


# ============================================================================
# RANKING OPERATIONS
# ============================================================================

def example_ranking_operations():
    """Example of adding ranking to resumes"""
    
    db = ResumeDatabase()
    
    # Sample ranking data (from RankResume.py)
    ranking_data = {
        'skills': {
            'score': 35,
            'justification': 'Strong Python and JavaScript skills'
        },
        'experience': {
            'score': 28,
            'justification': 'Relevant experience in full-stack development'
        },
        'projects': {
            'score': 8,
            'justification': 'Good portfolio of projects'
        },
        'other_relevant_skills': {
            'score': 7,
            'justification': 'Cloud and DevOps knowledge'
        },
        'extras': {
            'score': 4,
            'justification': 'Certifications in AWS'
        },
        'total_score': 82
    }
    
    job_description = "Looking for a Full Stack Developer with Python and JavaScript experience"
    
    # Add ranking to a resume
    result = db.add_ranking('resume_001', ranking_data, job_description)
    print(f"✓ Ranking added: {result}")
    
    # A resume can have multiple rankings for different job descriptions
    result = db.add_ranking('resume_001', ranking_data, "Another job description")
    print(f"✓ Another ranking added: {result}")
    
    db.close_connection()


# ============================================================================
# ERROR HANDLING
# ============================================================================

def example_error_handling():
    """Example of proper error handling"""
    
    try:
        db = ResumeDatabase()
        
        # Try to insert duplicate
        resume = {'_id': 'test_001', 'name': 'Test User'}
        db.insert_resume(resume)
        
        # This will raise DuplicateKeyError
        db.insert_resume(resume)
        
    except DuplicateKeyError as e:
        print(f"✗ Duplicate key error: {e}")
    except ValueError as e:
        print(f"✗ Validation error: {e}")
    except PyMongoError as e:
        print(f"✗ Database error: {e}")
    finally:
        db.close_connection()


# ============================================================================
# LEGACY API SUPPORT (for backward compatibility)
# ============================================================================

def example_legacy_api():
    """Example using legacy function-based API"""
    
    from Db import load_mongodb, insert_resume, get_resume, update_resume, delete_resume
    
    # Get collection (old way)
    collection = load_mongodb()
    
    # Use legacy functions with collection
    resume = {'_id': 'legacy_001', 'name': 'Legacy User'}
    
    try:
        insert_resume(resume, collection)
        print("✓ Legacy insert successful")
    except DuplicateKeyError:
        print("Resume already exists")
    
    # Or use without collection (will create new connection each time)
    resume_data = get_resume('legacy_001')
    print(f"✓ Legacy get: {resume_data}")


# ============================================================================
# CONTEXT MANAGER (Best Practice)
# ============================================================================

class ResumeDatabaseContext(ResumeDatabase):
    """Context manager version for automatic connection cleanup"""
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close_connection()


def example_context_manager():
    """Example using context manager for automatic cleanup"""
    
    with ResumeDatabaseContext() as db:
        # All operations here
        resume = db.get_resume('resume_001')
        print(f"✓ Retrieved: {resume}")
        
        # Connection automatically closed when exiting the context
    
    print("✓ Connection closed automatically")


# ============================================================================
# MAIN EXECUTION
# ============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("MongoDB CRUD API Examples")
    print("=" * 60)
    
    print("\n1. Basic Usage:")
    print("-" * 60)
    # example_basic_usage()
    
    print("\n2. Advanced Operations:")
    print("-" * 60)
    # example_advanced_operations()
    
    print("\n3. Bulk Operations:")
    print("-" * 60)
    # example_bulk_operations()
    
    print("\n4. Ranking Operations:")
    print("-" * 60)
    # example_ranking_operations()
    
    print("\n5. Error Handling:")
    print("-" * 60)
    # example_error_handling()
    
    print("\n6. Legacy API:")
    print("-" * 60)
    # example_legacy_api()
    
    print("\n7. Context Manager:")
    print("-" * 60)
    # example_context_manager()
    
    print("\n" + "=" * 60)
    print("Uncomment the examples above to run them!")
    print("=" * 60)

