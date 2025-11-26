import json
import logging
from typing import Any, Dict, List, Union

log = logging.getLogger(__name__)


def get_query(
    request_id: int,
    api_name: str,
    name: str,
    args: Union[Dict[str, Any], List[Any]],
) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
    query = []
    args = json.loads(json.dumps(args))
    # Handle dict args (most common case for appbase)
    if len(args) > 0 and isinstance(args, dict):
        # For condenser_api broadcast_transaction, wrap in array
        if api_name == "condenser_api" and name == "broadcast_transaction":
            query = {
                "method": "call",
                "params": [api_name, name, [args]],
                "jsonrpc": "2.0",
                "id": request_id,
            }
        # For condenser_api, use the "call" method format
        elif api_name == "condenser_api":
            query = {
                "method": "call",
                "params": [api_name, name, args],
                "jsonrpc": "2.0",
                "id": request_id,
            }
        else:
            # For other appbase APIs, use direct method format
            query = {
                "method": api_name + "." + name,
                "params": args,
                "jsonrpc": "2.0",
                "id": request_id,
            }
    elif len(args) > 0 and isinstance(args, list) and isinstance(args[0], dict):
        # For condenser_api, use the "call" method format
        if api_name == "condenser_api":
            # For broadcast_transaction, wrap in array
            if name == "broadcast_transaction":
                query = {
                    "method": "call",
                    "params": [api_name, name, [args[0]]],
                    "jsonrpc": "2.0",
                    "id": request_id,
                }
            else:
                query = {
                    "method": "call",
                    "params": [api_name, name, args[0]],
                    "jsonrpc": "2.0",
                    "id": request_id,
                }
        else:
            # For other appbase APIs, use direct method format
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
    elif args or api_name == "condenser_api":
        # For condenser_api, always use the "call" method format, even with empty args
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
