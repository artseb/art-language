class Node:
    def __init__(self, token=None):
        self.token = token

    @property
    def line(self):
        return self.token.line if self.token else None

    @property
    def column(self):
        return self.token.column if self.token else None