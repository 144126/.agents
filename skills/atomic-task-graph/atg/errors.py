EXIT_OK = 0
EXIT_WARN = 1
EXIT_BLOCK = 2
EXIT_USAGE = 3
EXIT_NOTFOUND = 4
EXIT_FROZEN = 5
EXIT_BUDGET = 6

BLOCKING = "blocking"
WARNING = "warning"


class AtgError(Exception):
    code = "E_UNKNOWN"
    exit_code = EXIT_BLOCK

    def __init__(self, message, code=None, where=None, hint=None, issues=None):
        super().__init__(message)
        self.message = message
        if code is not None:
            self.code = code
        self.where = where
        self.hint = hint
        self.issues = list(issues or [])

    def as_dict(self):
        out = {
            "code": self.code,
            "message": self.message,
            "where": self.where,
            "hint": self.hint,
        }
        if self.issues:
            out["issues"] = [i.as_dict() for i in self.issues]
        return out

    def __str__(self):
        head = "%s: %s" % (self.code, self.message)
        if self.where:
            head = "%s (%s)" % (head, self.where)
        for issue in self.issues:
            head += "\n  %s %s%s: %s" % (issue.severity, issue.code,
                                         " " + issue.node if issue.node else "",
                                         issue.message)
            if issue.hint:
                head += "\n      hint: %s" % issue.hint
        if self.hint:
            head = "%s\n  hint: %s" % (head, self.hint)
        return head


class DslError(AtgError):
    code = "E_DSL_SYNTAX"

    def __init__(self, message, code=None, filename=None, line=None, col=None,
                 text=None, hint=None):
        where = None
        if filename is not None:
            where = "%s:%s" % (filename, line if line is not None else "?")
            if col is not None:
                where = "%s:%s" % (where, col)
        if text is not None:
            message = "%s\n  %s" % (message, text.rstrip())
        super().__init__(message, code=code, where=where, hint=hint)
        self.filename = filename
        self.line = line
        self.col = col


class CycleError(AtgError):
    code = "E_CYCLE"

    def __init__(self, message, nodes=(), hint=None):
        super().__init__(message, hint=hint)
        self.nodes = list(nodes)

    def as_dict(self):
        out = super().as_dict()
        out["nodes"] = self.nodes
        return out


class FrozenError(AtgError):
    code = "E_FROZEN"
    exit_code = EXIT_FROZEN


class BudgetError(AtgError):
    code = "E_BUDGET"
    exit_code = EXIT_BUDGET


class NotFoundError(AtgError):
    code = "E_NOT_FOUND"
    exit_code = EXIT_NOTFOUND


class UsageError(AtgError):
    code = "E_USAGE"
    exit_code = EXIT_USAGE


class Issue(object):
    __slots__ = ("code", "severity", "node", "message", "hint")

    def __init__(self, code, message, node=None, severity=BLOCKING, hint=None):
        self.code = code
        self.message = message
        self.node = node
        self.severity = severity
        self.hint = hint

    def as_dict(self):
        return {
            "class": self.code,
            "severity": self.severity,
            "node": self.node,
            "msg": self.message,
            "hint": self.hint,
        }

    def __repr__(self):
        return "Issue(%s, %s, node=%r)" % (self.code, self.severity, self.node)


def blocking(issues):
    return [i for i in issues if i.severity == BLOCKING]


def raise_if_blocking(issues, message, hint=None):
    hard = blocking(issues)
    if hard:
        raise AtgError(message, code=hard[0].code, hint=hint, issues=issues)


def worst_exit(issues):
    if any(i.severity == BLOCKING for i in issues):
        return EXIT_BLOCK
    if issues:
        return EXIT_WARN
    return EXIT_OK
