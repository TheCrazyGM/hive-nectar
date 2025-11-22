# -*- coding: utf-8 -*-
import json
import logging

log = logging.getLogger(__name__)


def get_query(request_id, api_name, name, args):
    query = []
    args = json.loads(json.dumps(args))
    # Handle dict args (most common case for appbase)
    if len(args) > 0 and isinstance(args, dict):
        query = {
            "method": api_name + "." + name,
            "params": args,
            "jsonrpc": "2.0",
            "id": request_id,
        }
    elif len(args) > 0 and isinstance(args, list) and isinstance(args[0], dict):
        query = {
            "method": api_name + "." + name,
            "params": args[0],
            "jsonrpc": "2.0",
            "id": request_id,
        }
    elif (
        len(args) > 0
        and isinstance(args, list)
        and isinstance(args[0], list)
        and len(args[0]) > 0
        and isinstance(args[0][0], dict)
    ):
        for a in args[0]:
            query.append(
                {
                    "method": api_name + "." + name,
                    "params": a,
                    "jsonrpc": "2.0",
                    "id": request_id,
                }
            )
            request_id += 1
    elif args:
        query = {
            "method": "call",
            "params": [api_name, name, args],
            "jsonrpc": "2.0",
            "id": request_id,
        }
        request_id += 1
    else:
        query = {
            "method": api_name + "." + name,
            "jsonrpc": "2.0",
            "params": {},
            "id": request_id,
        }
    return query
