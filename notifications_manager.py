#!/usr/bin/env -S uv run --quiet --script
# /// script
# requires-python = ">=3.13"
# dependencies = [
# "hive-nectar",
#     "rich",
# ]
#
# [tool.uv.sources]
# hive-nectar = { editable=true, path='/home/thecrazygm/github/hive-nectar/'}
# ///

"""
Hive Notifications Manager

A simple script to view and manage Hive notifications.
"""

import argparse
import os
import sys
from datetime import datetime

from rich import box
from rich.console import Console, Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from nectar import Hive
from nectar.account import Account
from nectar.exceptions import AccountDoesNotExistsException, MissingKeyError
from nectar.wallet import Wallet

# Define the nodes to connect to
NODES = ["https://api.hive.blog", "https://api.syncad.com"]


def get_wif():
    """
    Retrieve the WIF from environment variables.
    Returns None if not set.
    """
    return os.getenv("POSTING_WIF")


def connect_to_hive(wif=None):
    """
    Establish connection to Hive and return the account if WIF is provided.
    Otherwise return just the Hive instance.
    """
    try:
        # Connect to the Hive blockchain
        if wif:
            hive = Hive(keys=wif, node=NODES)
            wallet = Wallet(blockchain_instance=hive)
            account_name = wallet.getAccountFromPrivateKey(wif)
            account = Account(account_name, blockchain_instance=hive)
            return hive, account
        else:
            return Hive(node=NODES), None
    except (AccountDoesNotExistsException, MissingKeyError) as e:
        console = Console()
        console.print(f"[bold red]Error connecting to account:[/bold red] {e}", style="red")
        return None, None


def extract_notification_details(notif):
    """
    Extract detailed information from a notification object.

    Args:
        notif (dict): Notification object

    Returns:
        tuple: (sender, date, data_str)
    """
    # Ensure date is a string
    date = notif.get("date", "N/A")
    if hasattr(date, "strftime"):
        date = date.strftime("%Y-%m-%d %H:%M:%S")

    # Extract sender and data from msg and url
    sender = "N/A"
    data_str = "N/A"
    msg = notif.get("msg", "")
    url = notif.get("url", "")
    notif_type = notif.get("type", "")

    # Parse the message to extract sender
    if "@" in msg:
        # Extract the first @username from the message
        parts = msg.split()
        for part in parts:
            if part.startswith("@") and len(part) > 1:
                sender = part
                break

    # If we couldn't extract from msg, try from url
    if sender == "N/A" and url and url.startswith("@"):
        # Extract username from URL (format: @username/post-title)
        sender = url.split("/")[0]

    # Extract data from message
    if msg:
        # For vote notifications
        if notif_type == "vote":
            if "voted on your post" in msg:
                # Extract the dollar amount if present
                if "($" in msg and ")" in msg:
                    amount = msg.split("($")[1].split(")")[0]
                    data_str = f"voted {amount} on your post"
                else:
                    data_str = "voted on your post"

        # For mention notifications
        elif notif_type == "mention":
            if "mentioned you" in msg:
                if "and" in msg and "others" in msg:
                    # Extract how many others were mentioned
                    others_count = msg.split("and ")[1].split(" others")[0]
                    data_str = f"mentioned you and {others_count} others"
                else:
                    data_str = "mentioned you"

        # For reply notifications
        elif notif_type == "reply":
            if "replied to your" in msg:
                data_str = "replied to your post"
            elif "replied to you" in msg:
                data_str = "replied to you"

        # For reblog notifications
        elif notif_type == "reblog":
            if "reblogged your post" in msg:
                data_str = "reblogged your post"

        # If we couldn't extract specific data, use the whole message
        if data_str == "N/A":
            data_str = msg

    # If we still don't have data but have a URL, use that
    if data_str == "N/A" and url:
        # Format: @username/post-title
        if "/" in url:
            post_title = url.split("/", 1)[1]
            data_str = f"re: {post_title}"

    return sender, date, data_str


def display_notifications(account_name, notifications, page=1, page_size=50, debug=False):
    """
    Display notifications in a Rich table format with pagination.

    Args:
        account_name (str): Hive account name
        notifications (list): List of notifications
        page (int): Page number to display (starting from 1)
        page_size (int): Number of notifications per page
        debug (bool): Whether to show debug information
    """
    # Initialize console
    console = Console()

    # Debug: Print raw notification data
    if debug:
        console.print("\n[bold yellow]Raw Notification Data:[/bold yellow]")
        for i, notif in enumerate(notifications[:3], 1):  # Show first 3 for debugging
            console.print(f"\n[bold cyan]Notification #{i} ({notif['type']}):[/bold cyan]")
            console.print(notif)

    # Calculate pagination
    total_notifications = len(notifications)
    total_pages = max(1, (total_notifications + page_size - 1) // page_size)

    # Adjust page if out of bounds
    if page < 1:
        page = 1
    elif page > total_pages:
        page = total_pages

    # Get notifications for the current page
    start_idx = (page - 1) * page_size
    end_idx = min(start_idx + page_size, total_notifications)
    page_notifications = notifications[start_idx:end_idx]

    # Create header
    header = Text(f"Notifications for @{account_name}", style="bold blue")

    # Create timestamp and pagination info
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    pagination_info = f"Page {page}/{total_pages} · {total_notifications} total"
    footer = Text(f"Updated: {current_time} · {pagination_info}", style="dim italic")

    # Create notifications table
    notification_type = "Unread" if len(notifications) != len(page_notifications) else ""
    table = Table(
        title=f"{notification_type} Notifications ({start_idx + 1}-{end_idx} of {total_notifications})",
        box=box.DOUBLE,
        border_style="cyan",
        header_style="bold magenta",
        padding=(0, 1),
        title_justify="center",
        width=None,
    )

    # Add columns
    table.add_column("#", style="cyan", justify="right")
    table.add_column("Type", style="green")
    table.add_column("From", style="yellow")
    table.add_column("Data", style="blue")
    table.add_column("Date", style="magenta")

    # Add rows to the table
    for idx, notif in enumerate(page_notifications, start_idx + 1):
        # Extract notification details
        sender, date, data_str = extract_notification_details(notif)

        table.add_row(str(idx), notif["type"], sender, data_str, date)

    # Get the console width to help with panel sizing
    console_width = console.width

    # Create a group with the table
    group = Group(
        header,
        Panel(table, border_style="blue", padding=(0, 0)),
        footer,
    )

    # Create the main panel
    panel = Panel(
        group,
        title="[bold blue]Hive Notifications Manager[/bold blue]",
        subtitle="[dim]Powered by Nectar & Rich[/dim]",
        title_align="center",
        subtitle_align="right",
        border_style="cyan",
        padding=(1, 1),
        expand=True,
        width=min(console_width - 2, 120),
    )

    # Print the panel
    console.print(panel)

    return panel


def main():
    # Initialize console
    console = Console()

    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Hive Notifications Manager")
    parser.add_argument(
        "account",
        nargs="?",
        default="thecrazygm",
        help="Hive account name (default: thecrazygm)",
    )
    parser.add_argument(
        "-a",
        "--all",
        action="store_false",
        dest="only_unread",
        help="Show all notifications, not just unread ones",
    )
    parser.add_argument(
        "-c",
        "--clear",
        action="store_true",
        help="Mark notifications as read",
    )
    parser.add_argument(
        "-d",
        "--debug",
        action="store_true",
        help="Show debug information including raw notification data",
    )
    parser.add_argument(
        "-p",
        "--page",
        type=int,
        default=1,
        help="Page number to display (default: 1)",
    )
    parser.add_argument(
        "-s",
        "--size",
        type=int,
        default=50,
        help="Number of notifications per page (default: 50)",
    )

    args = parser.parse_args()
    account_name = args.account

    try:
        # Get WIF from environment if available
        wif = get_wif()

        # Connect to Hive
        if wif:
            hive, authenticated_account = connect_to_hive(wif)
            if not hive or not authenticated_account:
                return 1

            # If no account specified or default, use the authenticated account
            if account_name == "thecrazygm" and authenticated_account.name != account_name:
                account_name = authenticated_account.name
                account = authenticated_account
            else:
                # If a different account was specified, create that account object
                account = Account(account_name, blockchain_instance=hive)
        else:
            # No WIF provided, just connect to Hive
            hive, _ = connect_to_hive()
            if not hive:
                return 1
            account = Account(account_name, blockchain_instance=hive)

        # Get notifications (max 100 as per API limitation)
        with console.status(
            f"[bold blue]Fetching notifications for @{account_name}...[/bold blue]"
        ):
            # Fetch up to 100 notifications (API limit)
            notifications = account.get_notifications(
                only_unread=args.only_unread,
                limit=100,  # Maximum allowed by the API
            )

            # Inform user if we hit the API limit
            if len(notifications) == 100:
                console.print(
                    "[bold yellow]Note:[/bold yellow] Only showing the 100 most recent notifications (API limit)",
                    style="yellow",
                )

        if not notifications:
            console.print(
                Panel(
                    f"[bold]No {'unread ' if args.only_unread else ''}notifications found for @{account_name}![/bold]",
                    border_style="yellow",
                    padding=(1, 2),
                )
            )
            return 0

        # Display notifications with pagination
        display_notifications(
            account_name,
            notifications,
            page=args.page,
            page_size=args.size,
            debug=args.debug,
        )

        # Mark as read if requested with --clear flag
        if args.clear:
            if wif and args.only_unread and authenticated_account.name == account_name:
                with console.status("[bold blue]Marking notifications as read...[/bold blue]"):
                    result = account.mark_notifications_as_read()

                if result and "operations" in result and result["operations"]:
                    console.print(
                        "[bold green]Successfully marked notifications as read![/bold green]"
                    )
                else:
                    console.print("[bold red]Failed to mark notifications as read.[/bold red]")
            elif not wif:
                console.print(
                    "\n[bold yellow]Note:[/bold yellow] Set ACTIVE_WIF environment variable to mark notifications as read"
                )
            elif not args.only_unread:
                console.print(
                    "\n[bold yellow]Note:[/bold yellow] Can only mark unread notifications as read. Use without --all flag."
                )
            elif authenticated_account.name != account_name:
                console.print(
                    f"\n[bold yellow]Note:[/bold yellow] Can only mark notifications as read for your own account ({authenticated_account.name}), not {account_name}."
                )

    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {str(e)}", style="red")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
