"""
Mroll specific exceptions
"""

from mroll.migration import Revision

class RevisionOperationError(Exception):
    def __init__(self, rev: Revision, *args):
        super(Exception, self).__init__(*args)
        self.revision = rev
        self.args = args

    def __repr__(self):
        rev = self.revision
        return """Error: @{}:
        {}
        -------
        {}
        -------
        {}
        """.format(rev.id, rev.upgrade_sql, rev.downgrade_sql, self.args)
