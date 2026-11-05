"""Offline discovery tests: proposals never verify, crawl, or publish."""
from workers.college_website_candidates import (
    DIRECTORY_API, WIKIDATA_API, match_score, normalized,
    safe_website, wikidata_candidates, run, SourceThrottled,
)


def test_candidate_link_security_and_similarity():
    assert normalized('  DR.   Mahalingam College! ') == 'dr mahalingam college'
    assert match_score('IIT Indore', 'IIT Indore') == 1.0
    assert match_score('Unrelated College', 'IIT Indore') < 0.87
    assert safe_website('https://college.ac.in/events') == 'https://college.ac.in/events'
    for invalid in ('http://college.ac.in', 'javascript:alert(1)',
                    'https://username:secret@college.ac.in',
                    'https://localhost/path', 'https://127.0.0.1/x',
                    'https://college.ac.in/x#fragment',
                    'https://college.ac.in/evil\nheader', None):
        assert safe_website(invalid) is None


def test_wikidata_candidate_is_review_only_and_keeps_evidence():
    college = {
        'identifier': 'AISHE:U-123', 'name': 'Indian Institute of Technology Indore',
        'state': 'Madhya Pradesh', 'district': 'Indore',
    }
    calls = []
    def fake(url, params):
        calls.append((url, params))
        assert url == WIKIDATA_API
        if params['action'] == 'wbsearchentities':
            assert params['limit'] <= 4
            return {'search': [
                {'id':'Q111','label':'Indian Institute of Technology Indore'},
                {'id':'Q222','label':'Unrelated Business'},
            ]}
        assert params['ids'] == 'Q111'
        return {'entities': {'Q111': {'claims': {
            'P17': [{'mainsnak': {'datavalue': {'value': {'id':'Q668'}}}}],
            'P856': [{'mainsnak': {'datavalue': {'value':'https://www.iiti.ac.in/'}}}],
        }}}}
    result = wikidata_candidates(college, fetch=fake)
    assert len(result) == 1
    assert result[0]['identifier'] == college['identifier']
    assert result[0]['state'] == 'Madhya Pradesh'
    assert result[0]['website_candidate'] == 'https://www.iiti.ac.in/'
    assert result[0]['country_claim_india'] is True
    assert result[0]['status'] == 'needs_manual_website_and_terms_review'
    assert result[0]['event_urls'] == []
    assert len(calls) == 2


def test_unknown_country_and_no_website_never_invents_source():
    college = {'identifier':'AISHE:C-1', 'name':'Example Engineering College', 'state':'Delhi'}
    def fake(url, params):
        if params['action'] == 'wbsearchentities':
            return {'search':[{'id':'Q123', 'label':'Example Engineering College'}]}
        return {'entities': {'Q123': {'claims': {}}}}
    assert wikidata_candidates(college, fetch=fake) == []


def test_bounded_public_pages_and_never_mutates_database():
    calls = []
    rows = [
        {'identifier':'AISHE:U-1', 'name':'Test Technology University', 'state':'Delhi','district':'Central', 'website':None},
        {'identifier':'AISHE:C-2', 'name':'A General Arts College','state':'Delhi', 'website':None},
        {'identifier':'AISHE:C-3', 'name':'Existing Engineering Institute','state':'Delhi', 'website':'https://existing.edu.in'},
    ]
    def fake(url, params):
        calls.append((url, params))
        if url == DIRECTORY_API:
            return {'total': 3, 'data': rows}
        if params['action'] == 'wbsearchentities':
            return {'search': [{'id':'Q123','label':'Test Technology University'}]}
        return {'entities': {'Q123': {'claims': {
            'P856':[{'mainsnak': {'datavalue': {'value':'https://testtech.edu.in'}}}]
        }}}}
    report = run(pages=1, max_colleges=2, start_page=1, fetch=fake, delay=0)
    assert report['total_colleges'] == 3
    assert report['colleges_queried'] == 1
    assert len(report['candidates']) == 1
    assert report['candidates'][0]['status'].startswith('needs_manual')
    assert all(url in (DIRECTORY_API, WIKIDATA_API) for url, _ in calls)
    assert sum(1 for url, _ in calls if url == DIRECTORY_API) == 1


def test_throttling_stops_entire_batch():
    calls = []
    rows = [
        {'identifier': 'AISHE:U-1','name':'Test Engineering University','state':'Delhi'},
        {'identifier': 'AISHE:U-2','name':'Next Technology University','state':'Delhi'},
    ]
    def fake(url, params):
        calls.append((url, params))
        if url == DIRECTORY_API:
            return {'total': 2, 'data': rows}
        raise SourceThrottled('stop')
    report = run(pages=1, max_colleges=2, start_page=1, fetch=fake, delay=0)
    assert report['rate_limited'] is True
    assert report['upstream_errors'] == 1
    assert report['colleges_queried'] == 1
    assert len(calls) == 2  # One directory request and a single rejected lookup.
