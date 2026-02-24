
import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
import pytz
import sys
import os

# Add app to path
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from app.services.pr_chat import fetch_repository_prs, filter_prs_by_query

class TestRepoPRChat(unittest.TestCase):

    @patch("app.services.pr_chat.requests.get")
    def test_fetch_repository_prs_pagination_limit(self, mock_get):
        # Mock response with 50 items per page
        # Page 1: 50 items
        # Page 2: 50 items
        # Page 3: 50 items (Should NOT be hit if limit is 100)
        
        def side_effect(url, headers, params):
            page = params.get("page", 1)
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            if page <= 2:
                mock_resp.json.return_value = [{"number": i} for i in range(50)]
            else:
                mock_resp.json.return_value = [{"number": i} for i in range(10)] # Should not theoretically be reached
            return mock_resp

        mock_get.side_effect = side_effect

        prs = fetch_repository_prs("owner/repo", "token", limit=100)
        
        print(f"Fetched {len(prs)} PRs")
        self.assertEqual(len(prs), 100, "Should fetch exactly 100 PRs")
        self.assertEqual(mock_get.call_count, 2, "Should call API exactly 2 times for 100 items (50 per page)")


    def test_filter_prs_by_query_date(self):
        now = datetime.now(pytz.utc)
        week_ago = now - timedelta(days=5)
        month_ago = now - timedelta(days=30)
        
        prs = [
            {"number": 1, "title": "Recent Merge", "state": "closed", "merged_at": week_ago.isoformat()},
            {"number": 2, "title": "Old Merge", "state": "closed", "merged_at": month_ago.isoformat()},
            {"number": 3, "title": "Open PR", "state": "open", "merged_at": None}
        ]
        
        # Query: "merged last week"
        result = filter_prs_by_query(prs, "what PRs were merged last week?", "owner/repo")
        print("\nQuery: merged last week")
        print(result)
        
        self.assertIn("#1 Recent Merge", result)
        self.assertNotIn("#2 Old Merge", result)
        self.assertNotIn("#3 Open PR", result)


    def test_filter_prs_performance_priority(self):
        prs = [
            {"number": 1, "title": "Improve database performance", "body": "Optimized queries", "state": "open"},
            {"number": 2, "title": "Fix typo", "body": "Docs update", "state": "open"},
            {"number": 3, "title": "Reduce latency", "body": "Faster load", "state": "open"},
        ]
        
        # Query: "performance optimization"
        result = filter_prs_by_query(prs, "show me performance optimizations", "owner/repo")
        print("\nQuery: performance")
        print(result)
        
        self.assertIn("#1 Improve database performance", result)
        self.assertIn("#3 Reduce latency", result)
        self.assertNotIn("#2 Fix typo", result)


    def test_filter_prs_by_query_keyword(self):
        prs = [
            {"number": 1, "title": "Fix authentication bug", "body": "Fixed login", "state": "open"},
            {"number": 2, "title": "Update documentation", "body": "Readme update", "state": "open"},
        ]
        
        # Query: "auth"
        result = filter_prs_by_query(prs, "show me auth PRs", "owner/repo")
        print("\nQuery: auth")
        print(result)
        
        self.assertIn("#1 Fix authentication bug", result)
        self.assertNotIn("#2 Update documentation", result)

    @patch("app.services.pr_chat.requests.get")
    def test_filter_prs_deep_fetch_limit(self, mock_get):
        # Setup: Query "touched file" implies deep fetch
        # We pass 50 matching PRs (metadata wise)
        # Verify only 10 deep fetches are made
        
        prs = [{"number": i, "title": "Update file", "state": "open"} for i in range(50)]
        
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = [{"filename": "unknown.txt"}] # No match, but call happens
        mock_get.return_value = mock_resp
        
        result = filter_prs_by_query(prs, "which prs touched unknown.txt?", "owner/repo")
        
        # Check that we called the files endpoint max 10 times
        files_calls = [c for c in mock_get.call_args_list if "/files" in c[0][0]]
        print(f"\nDeep fetch calls: {len(files_calls)}")
        
        self.assertLessEqual(len(files_calls), 10, "Should strict cap deep fetches to 10")


if __name__ == "__main__":
    unittest.main()
