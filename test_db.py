"""
Test Suite for Resume Database API
===================================

Runs against an isolated test database (see conftest.py) and cleans up after
itself. Requires a reachable MongoDB at MONGO_URI; skipped otherwise.

    pytest test_db.py        # or: python test_db.py
"""
import sys

import pytest
from pymongo.errors import DuplicateKeyError

import Db
from Db import ResumeDatabase


def make_resume(**overrides):
    resume = {
        '_id': 'test_resume_001',
        'name': 'Alice Johnson',
        'contact_information': '+1-234-567-8900',
        'email_address': 'alice@example.com',
        'linkedin_profile': 'linkedin.com/in/alice',
        'skills': ['Python', 'MongoDB', 'FastAPI', 'React'],
        'experience': [{'company': 'Tech Corp', 'position': 'Senior Developer',
                        'duration': '2020-2023', 'description': 'Led development team'}],
        'education': [{'degree': 'BS Computer Science', 'university': 'MIT', 'year': 2020}],
        'projects': [{'name': 'E-commerce Platform', 'technologies': ['Python', 'MongoDB']}],
        'extras': ['AWS Certified'],
    }
    resume.update(overrides)
    return resume


RANKING = {
    'skills': {'score': 38, 'justification': 'Strong Python and MongoDB skills'},
    'experience': {'score': 32, 'justification': 'Senior developer'},
    'projects': {'score': 9, 'justification': 'E-commerce platform'},
    'other_relevant_skills': {'score': 8, 'justification': 'AWS'},
    'extras': {'score': 5, 'justification': 'Certification'},
    'total_score': 92,
}


def test_connection(db):
    assert db.client.admin.command('ping')['ok'] == 1


def test_context_manager_closes_connection(db):
    with ResumeDatabase() as other:
        assert other.client is not None
    assert other.client is None
    other.close_connection()  # idempotent


def test_missing_uri_raises(monkeypatch):
    monkeypatch.setattr(Db, 'load_dotenv', lambda: None)
    monkeypatch.delenv('MONGO_URI', raising=False)
    with pytest.raises(ValueError, match='MONGO_URI'):
        ResumeDatabase()


def test_insert_and_get(db):
    resume = make_resume()
    result = db.insert_resume(resume)
    assert result == {'success': True, 'id': 'test_resume_001', 'message': 'Resume inserted successfully'}
    assert 'created_at' not in resume, "insert_resume must not mutate the caller's dict"

    stored = db.get_resume('test_resume_001')
    assert stored['name'] == 'Alice Johnson'
    assert stored['created_at'] is not None and stored['updated_at'] is not None


def test_insert_generates_id(db):
    result = db.insert_resume({'name': 'No Id'})
    assert db.get_resume(result['id'])['name'] == 'No Id'


def test_insert_empty_raises(db):
    with pytest.raises(ValueError):
        db.insert_resume({})


def test_insert_duplicate_raises(db):
    db.insert_resume(make_resume())
    with pytest.raises(DuplicateKeyError):
        db.insert_resume(make_resume())


def test_get_missing_returns_none(db):
    assert db.get_resume('does-not-exist') is None


def test_update(db):
    db.insert_resume(make_resume())
    update = {'skills': ['Python', 'Docker']}
    result = db.update_resume('test_resume_001', update)
    assert result['success'] and result['matched_count'] == 1 and result['modified_count'] == 1
    assert 'updated_at' not in update, "update_resume must not mutate the caller's dict"
    assert db.get_resume('test_resume_001')['skills'] == ['Python', 'Docker']


def test_update_ignores_id_field(db):
    db.insert_resume(make_resume())
    result = db.update_resume('test_resume_001', {'_id': 'test_resume_001', 'name': 'Alice J'})
    assert result['success']
    assert db.get_resume('test_resume_001')['name'] == 'Alice J'


def test_update_missing_and_empty(db):
    assert db.update_resume('nope', {'name': 'x'})['success'] is False
    with pytest.raises(ValueError):
        db.update_resume('nope', {})


def test_update_upsert(db):
    result = db.update_resume('upserted', {'name': 'New'}, upsert=True)
    assert result['upserted_id'] == 'upserted'
    assert db.get_resume('upserted')['name'] == 'New'


def test_search_and_count(db):
    db.insert_resume(make_resume())
    db.insert_resume(make_resume(_id='js', name='Bob', skills=['JavaScript']))
    results = db.search_resumes({'skills': {'$in': ['Python']}})
    assert [r['name'] for r in results] == ['Alice Johnson']
    assert db.get_resume_count() == 2
    assert db.get_resume_count({'skills': {'$in': ['Python']}}) == 1


def test_add_ranking_keeps_history_and_sets_score(db):
    db.insert_resume(make_resume())
    jd = 'Senior Full Stack Developer with Python and MongoDB'
    assert db.add_ranking('test_resume_001', RANKING, jd)['success']
    assert db.add_ranking('test_resume_001', {**RANKING, 'total_score': 50}, 'other jd')['success']

    stored = db.get_resume('test_resume_001')
    assert len(stored['rankings']) == 2
    assert stored['rankings'][0]['job_description'] == jd
    assert stored['total_score'] == 50
    assert stored['latest_ranking']['job_description'] == 'other jd'
    # resume content must be untouched by ranking
    assert stored['skills'] == make_resume()['skills']


def test_add_ranking_missing_resume(db):
    assert db.add_ranking('nope', RANKING, 'jd')['success'] is False


def test_get_top_resumes(db):
    for i, score in enumerate([40, 90, 70]):
        db.insert_resume(make_resume(_id=f'r{i}', name=f'C{i}'))
        db.add_ranking(f'r{i}', {**RANKING, 'total_score': score}, 'jd')
    db.insert_resume(make_resume(_id='unranked', name='U'))
    assert [r['total_score'] for r in db.get_top_resumes(limit=2)] == [90, 70]


def test_get_all_pagination(db):
    for i in range(5):
        db.insert_resume({'_id': f'p{i}', 'name': f'P{i}'})
    page1 = db.get_all_resumes(limit=2, skip=0, sort_by='name', ascending=True)
    page2 = db.get_all_resumes(limit=2, skip=2, sort_by='name', ascending=True)
    assert [r['name'] for r in page1] == ['P0', 'P1']
    assert [r['name'] for r in page2] == ['P2', 'P3']


def test_bulk_insert(db):
    resumes = [{'name': 'Bob Smith', 'skills': ['JavaScript']},
               {'name': 'Carol White', 'skills': ['Java']}]
    result = db.bulk_insert_resumes(resumes)
    assert result['success'] and len(result['inserted_ids']) == 2
    assert '_id' not in resumes[0], "bulk insert must not mutate the caller's dicts"
    assert db.get_resume_count() == 2
    with pytest.raises(ValueError):
        db.bulk_insert_resumes([])


def test_delete(db):
    db.insert_resume(make_resume())
    result = db.delete_resume('test_resume_001')
    assert result['success'] and result['deleted_count'] == 1
    assert db.get_resume('test_resume_001') is None
    assert db.delete_resume('test_resume_001')['success'] is False


def test_legacy_functions_with_collection(db):
    coll = db.collection
    Db.insert_resume({'_id': 'legacy_001', 'name': 'Legacy User'}, coll)
    assert Db.get_resume('legacy_001', coll)['name'] == 'Legacy User'
    Db.update_resume('legacy_001', {'name': 'Updated'}, coll)
    assert Db.get_resume('legacy_001', coll)['name'] == 'Updated'
    with pytest.raises(DuplicateKeyError):
        Db.insert_resume({'_id': 'legacy_001', 'name': 'Dup'}, coll)
    Db.delete_resume('legacy_001', coll)
    assert Db.get_resume('legacy_001', coll) is None


def test_legacy_functions_without_collection(db):
    Db.insert_resume({'_id': 'legacy_002', 'name': 'Legacy'})
    assert Db.get_resume('legacy_002')['name'] == 'Legacy'
    Db.update_resume('legacy_002', {'name': 'L2'})
    assert Db.get_resume('legacy_002')['name'] == 'L2'
    Db.delete_resume('legacy_002')
    assert Db.get_resume('legacy_002') is None


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
