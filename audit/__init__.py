"""
audit/__init__.py
Trace-ID generation and Flask g-context helpers.
"""

import uuid
from flask import g, has_request_context


def generate_trace_id():
    """Generate a unique trace ID for the current request."""
    return str(uuid.uuid4())


def get_trace_id():
    """
    Return the current trace_id from Flask g context.
    If not set or outside request context, generate a new one.
    """
    if has_request_context():
        tid = getattr(g, "trace_id", None)
        if tid:
            return tid
        tid = generate_trace_id()
        g.trace_id = tid
        return tid
    return generate_trace_id()


def set_trace_id(trace_id=None):
    """Pin a trace_id on Flask g (call early in the request)."""
    if has_request_context():
        g.trace_id = trace_id or generate_trace_id()
        return g.trace_id
    return trace_id or generate_trace_id()
