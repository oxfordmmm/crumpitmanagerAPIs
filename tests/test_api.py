import pytest

from crumpitmanagerapi import create_app

@pytest.fixture
def app():
    app = create_app(testing=True)
    yield app

@pytest.fixture
def client(app):
    return app.test_client()

def test_index(client):
    """Test index page"""
    rv = client.get('/')
    assert b'Welcome to crumpit Manager APIs' in rv.data

def test_liveRuns(client):
    """Test accessing live runs"""
    rv = client.get('/liveRuns')
    assert b'DFB_R_10' in rv.data

def test_metadataRuns(client):
    """Test accessing metedata runs"""
    rv = client.get('/metadata/runs')
    assert b'DFB_R_10' in rv.data