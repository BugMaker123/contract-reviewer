import pytest
from backend import main, workspace_api, word_export
from backend.store import Repository


@pytest.fixture(autouse=True)
def isolated_workspace(tmp_path, monkeypatch):
    """Never write synthetic contracts to the user's actual database or source directory."""
    repository = Repository(tmp_path / 'workspace.db')
    monkeypatch.setattr(main, 'repository', repository)
    monkeypatch.setattr(workspace_api, 'repo', repository)
    monkeypatch.setattr(main, 'SOURCES', tmp_path / 'sources')
    monkeypatch.setattr(word_export, 'SOURCES', tmp_path / 'sources')
