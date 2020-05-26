"""
Mroll specific exceptions
"""
class RevisionOperationError(Exception):
    def __init__(self, rev, extra_info:str=None, *args):
        super(Exception, self).__init__(*args)
        self.revision = rev
        self.extra_info = extra_info

    def __repr__(self):
        rev = self.revision
        return """Error: @{}:
        {}
        ------->
        {}
        <-------
        {}
        """.format(rev.id, rev.upgrade_sql, rev.downgrade_sql, self.extra_info)

class InvalidWorkDirError(Exception):
    """
    Execption raised for invalid, or non-existing work directory
    """
    pass
