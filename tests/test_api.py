import pytest

from crumpitmanagerapi import create_app

@pytest.fixture
def app():
    app = create_app()
    yield app

@pytest.fixture
def client(app):
    return app.test_client()

def test_index(client):
    """Test index page"""
    rv = client.get('/')
    assert b'Welcome to crumpit Manager APIs' in rv.data