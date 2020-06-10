"""
Mroll specific exceptions
"""
class RevisionOperationError(Exception):
    def __init__(self, rev, stmt, *args):
        super(Exception, self).__init__(*args)
        self.revision = rev
        self.stmt = stmt

    def __repr__(self):
        return """Error: revision id={}
        {}
        ===========
        {}
        """.format(self.revision.id, self.stmt, self.args)

class InvalidWorkDirError(Exception):
    """
    Execption raised for invalid, or non-existing work directory
    """
    pass
