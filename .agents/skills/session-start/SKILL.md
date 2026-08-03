# Session Context (GTFS MCP)

You have access to GTFS transit schedule data tools: feed management (add_feed,
list_feeds), stop search (find_stops), departures (get_departures), and stop
details (get_stop_info).

**Before starting work:**
1. List registered feeds: list_feeds()
2. Resolve stops by name: find_stops(feed_id="<id>", query="<station name>", limit=5)

**At end of work:**
- Note the feed_id and stop_ids you used for follow-up queries
