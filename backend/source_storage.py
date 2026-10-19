"""Publish source bytes before making a source record visible; compensate failures."""
import hashlib
import os
from uuid import uuid4


def save_source(repo, directory, metadata, content):
    directory.mkdir(parents=True, exist_ok=True)
    identifier = uuid4().hex
    temporary = directory / (identifier + '.pending')
    target = directory / (identifier + metadata['extension'])
    try:
        with temporary.open('xb') as output:
            output.write(content)
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, target)
        return repo.create('source', {**metadata, 'sha256': hashlib.sha256(content).hexdigest()}, identifier=identifier)
    except BaseException:
        temporary.unlink(missing_ok=True)
        # create() may have committed before its response/read failed. Preserve
        # published bytes whenever commit status is unknown.
        try:
            with repo.connect() as db:
                committed = db.execute("SELECT 1 FROM objects WHERE id=?", (identifier,)).fetchone()
            if not committed:
                target.unlink(missing_ok=True)
        except Exception:
            pass
        raise


def discard_source(repo, directory, source):
    """Remove a newly created source only if no object references its identifier."""
    with repo.connect() as db:
        db.execute('BEGIN IMMEDIATE')
        if db.execute("SELECT 1 FROM objects WHERE id!=? AND (json_extract(data,'$.source_id')=? OR json_extract(data,'$.input.source_id')=?) LIMIT 1", (source['id'], source['id'], source['id'])).fetchone():
            return
        db.execute("DELETE FROM objects WHERE id=? AND kind='source'", (source['id'],))
    (directory / (source['id'] + source['extension'])).unlink(missing_ok=True)
