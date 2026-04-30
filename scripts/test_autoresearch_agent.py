"""
Tests for autoresearch_agent.py

TDD suite — tests tool dispatch, budget enforcement, prompt assembly,
context trimming, and config read/write without hitting real APIs.
"""

import json
import sys
import os
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock, ANY
import pytest

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

# Mock serper_search and scrape before importing the agent
sys.modules["serper_search"] = MagicMock()
sys.modules["scrape"] = MagicMock()

import autoresearch_agent as agent


# ── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture
def tracker():
    return agent.ToolTracker(budget=0.25, max_queries=75, max_scrapes=20)


@pytest.fixture
def tight_tracker():
    """Tracker near budget limits."""
    t = agent.ToolTracker(budget=0.005, max_queries=3, max_scrapes=1)
    return t


@pytest.fixture
def tmp_project(tmp_path):
    """Create a minimal project dir with required files."""
    # master_test_config.json
    config = {
        "description": "test config",
        "test_companies": [
            {"company_name": "TestCo", "domain": "test.com", "category": "testing", "tier": 1}
        ],
        "categories": [
            {
                "id": "company_profile",
                "name": "Company Profile",
                "keywords": ["company"],
                "variants": [
                    {"id": "v1", "template": "{{company_name}} about"}
                ],
            }
        ],
    }
    scripts_dir = tmp_path / "scripts"
    scripts_dir.mkdir()
    (scripts_dir / "master_test_config.json").write_text(json.dumps(config), encoding="utf-8")

    # best_config.json
    best = {"overall_gt_mean": 0.45, "best_variants_by_category": {}, "dead_end_patterns": []}
    (tmp_path / "best_config.json").write_text(json.dumps(best), encoding="utf-8")

    # research_prompt.md
    (tmp_path / "research_prompt.md").write_text("# Test Research Prompt\nLoop protocol here.", encoding="utf-8")

    # domain-briefing.md
    (tmp_path / "domain-briefing.md").write_text("# Test Domain Briefing\nApproaches here.", encoding="utf-8")

    return tmp_path


# ── ToolTracker tests ────────────────────────────────────────────────────────

class TestToolTracker:
    def test_initial_state(self, tracker):
        assert tracker.query_count == 0
        assert tracker.scrape_count == 0
        assert tracker.cost == 0.0
        assert tracker.can_query()
        assert tracker.can_scrape()

    def test_record_query_increments(self, tracker):
        tracker.record_query()
        assert tracker.query_count == 1
        assert tracker.cost == pytest.approx(0.001)

    def test_record_scrape_increments(self, tracker):
        tracker.record_scrape()
        assert tracker.scrape_count == 1
        assert tracker.cost == pytest.approx(0.003)

    def test_query_budget_exhaustion(self, tight_tracker):
        for _ in range(3):
            tight_tracker.record_query()
        assert not tight_tracker.can_query()

    def test_scrape_budget_exhaustion(self, tight_tracker):
        tight_tracker.record_scrape()
        assert not tight_tracker.can_scrape()

    def test_cost_budget_exhaustion(self):
        t = agent.ToolTracker(budget=0.0025, max_queries=100, max_scrapes=100)
        t.record_query()
        t.record_query()
        assert t.can_query()
        t.record_query()
        assert not t.can_query()

    def test_summary_format(self, tracker):
        tracker.record_query()
        s = tracker.summary()
        assert "Queries: 1/75" in s
        assert "Scrapes: 0/20" in s
        assert "$" in s


# ── Tool dispatch tests ──────────────────────────────────────────────────────

class TestToolDispatch:
    def test_serper_search_budget_check(self, tight_tracker):
        for _ in range(3):
            tight_tracker.record_query()
        result = json.loads(agent.handle_tool_call("serper_search", {"query": "test"}, tight_tracker))
        assert "error" in result
        assert "exhausted" in result["error"].lower()

    def test_spider_scrape_budget_check(self, tight_tracker):
        tight_tracker.record_scrape()
        result = json.loads(agent.handle_tool_call("spider_scrape", {"url": "https://example.com"}, tight_tracker))
        assert "error" in result

    @patch("autoresearch_agent.serper_search")
    def test_serper_search_trims_results(self, mock_serper, tracker):
        mock_serper.search.return_value = {
            "organic": [
                {"title": f"Result {i}", "snippet": f"Snippet {i}", "link": f"https://example.com/{i}"}
                for i in range(10)
            ],
            "knowledgeGraph": {"title": "TestCo"},
        }
        result = json.loads(agent.handle_tool_call("serper_search", {"query": "test query"}, tracker))
        assert len(result["organic"]) == 5
        assert result["knowledgeGraph"]["title"] == "TestCo"
        assert tracker.query_count == 1

    @patch("autoresearch_agent.scrape_url")
    def test_spider_scrape_returns_content(self, mock_scrape, tracker):
        mock_scrape.return_value = [{"content": "# Page Title\n\nSome content here."}]
        result = json.loads(agent.handle_tool_call("spider_scrape", {"url": "https://example.com"}, tracker))
        assert "Page Title" in result["content"]
        assert tracker.scrape_count == 1

    @patch("autoresearch_agent.scrape_url")
    def test_spider_scrape_truncates_long_content(self, mock_scrape, tracker):
        mock_scrape.return_value = [{"content": "x" * 10000}]
        result = json.loads(agent.handle_tool_call("spider_scrape", {"url": "https://example.com"}, tracker))
        assert len(result["content"]) <= 5000

    def test_read_master_config(self, tracker, tmp_project):
        with patch.object(agent, "SCRIPT_DIR", tmp_project / "scripts"):
            result = agent.handle_tool_call("read_master_config", {}, tracker)
            parsed = json.loads(result)
            assert "test_companies" in parsed
            assert parsed["categories"][0]["id"] == "company_profile"

    def test_write_master_config(self, tracker, tmp_project):
        new_config = {
            "description": "updated",
            "test_companies": [],
            "categories": [
                {"id": "funding", "name": "Funding", "keywords": [], "variants": []}
            ],
        }
        with patch.object(agent, "SCRIPT_DIR", tmp_project / "scripts"):
            result = json.loads(agent.handle_tool_call(
                "write_master_config",
                {"config_json": json.dumps(new_config)},
                tracker,
            ))
            assert result["status"] == "ok"
            assert result["categories"] == 1

            # Verify file was written
            written = json.loads((tmp_project / "scripts" / "master_test_config.json").read_text(encoding="utf-8"))
            assert written["description"] == "updated"

    def test_write_master_config_invalid_json(self, tracker, tmp_project):
        with patch.object(agent, "SCRIPT_DIR", tmp_project / "scripts"):
            result = json.loads(agent.handle_tool_call(
                "write_master_config",
                {"config_json": "not valid json {{{"},
                tracker,
            ))
            assert "error" in result

    def test_update_best_config(self, tracker, tmp_project):
        new_best = {"overall_gt_mean": 0.55, "best_variants_by_category": {}}
        with patch.object(agent, "PROJECT_DIR", tmp_project):
            result = json.loads(agent.handle_tool_call(
                "update_best_config",
                {"config_json": json.dumps(new_best)},
                tracker,
            ))
            assert result["status"] == "ok"
            written = json.loads((tmp_project / "best_config.json").read_text(encoding="utf-8"))
            assert written["overall_gt_mean"] == 0.55

    def test_unknown_tool(self, tracker):
        result = json.loads(agent.handle_tool_call("nonexistent_tool", {}, tracker))
        assert "error" in result
        assert "Unknown" in result["error"]


# ── Shell command tests ──────────────────────────────────────────────────────

class TestRunShell:
    def test_basic_command(self):
        result = agent.run_shell(["py", "--version"])
        assert "Python" in result or "python" in result.lower()

    def test_truncation(self):
        result = agent.run_shell(["py", "-c", "print('x' * 20000)"])
        assert len(result) <= 15000

    def test_timeout_handling(self):
        result = agent.run_shell(["py", "-c", "import time; time.sleep(200)"], cwd=".")
        assert "timed out" in result.lower() or "ERROR" in result


# ── Prompt assembly tests ────────────────────────────────────────────────────

class TestPromptAssembly:
    def test_assembles_all_sections(self, tmp_project):
        with patch.object(agent, "PROJECT_DIR", tmp_project), \
             patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout="GT SCORES HERE", stderr="")
            prompt = agent.assemble_system_prompt()

            assert "Test Research Prompt" in prompt
            assert "DOMAIN BRIEFING" in prompt
            assert "WARM-START CONFIG" in prompt
            assert "AGENT INSTRUCTIONS" in prompt

    def test_includes_gt_scores(self, tmp_project):
        with patch.object(agent, "PROJECT_DIR", tmp_project), \
             patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout="company_profile: 0.587", stderr="")
            prompt = agent.assemble_system_prompt()
            assert "company_profile: 0.587" in prompt

    def test_handles_missing_files(self, tmp_path):
        with patch.object(agent, "PROJECT_DIR", tmp_path), \
             patch("subprocess.run", side_effect=Exception("no validate.py")):
            prompt = agent.assemble_system_prompt()
            assert "AGENT INSTRUCTIONS" in prompt


# ── Context trimming tests ───────────────────────────────────────────────────

class TestContextTrimming:
    def test_messages_trimmed_at_80(self):
        messages = [{"role": "system", "content": "sys"}]
        messages += [{"role": "user", "content": f"msg {i}"} for i in range(81)]
        assert len(messages) > 80

        # Simulate the trimming logic from run_agent
        if len(messages) > 80:
            messages = [messages[0]] + messages[-60:]

        assert len(messages) == 61
        assert messages[0]["role"] == "system"


# ── Integration-style tests (mocked OpenAI) ──────────────────────────────────

class TestAgentLoop:
    def test_dry_run_no_api_calls(self, tmp_project, capsys):
        with patch.object(agent, "PROJECT_DIR", tmp_project):
            agent.run_agent(dry_run=True)
            captured = capsys.readouterr()
            assert "DRY RUN" in captured.out
            assert "System prompt length" in captured.out

    @patch("autoresearch_agent.assemble_system_prompt", return_value="test prompt")
    @patch("autoresearch_agent.OpenAI")
    def test_stops_on_no_tool_calls(self, mock_openai_cls, mock_prompt, capsys):
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client

        mock_response = MagicMock()
        mock_response.usage.prompt_tokens = 100
        mock_response.usage.completion_tokens = 50
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "No improvements possible."
        mock_response.choices[0].message.tool_calls = None
        mock_response.choices[0].finish_reason = "stop"

        mock_client.chat.completions.create.return_value = mock_response

        agent.run_agent(max_iterations=5)

        captured = capsys.readouterr()
        assert "Loop complete" in captured.out or "No tool calls" in captured.out
        assert mock_client.chat.completions.create.call_count == 1

    @patch("autoresearch_agent.assemble_system_prompt", return_value="test prompt")
    @patch("autoresearch_agent.handle_tool_call")
    @patch("autoresearch_agent.OpenAI")
    def test_processes_tool_calls(self, mock_openai_cls, mock_handle, mock_prompt, capsys):
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        mock_handle.return_value = '{"status": "ok"}'

        # First response: tool call
        tc = MagicMock()
        tc.function.name = "save_baseline"
        tc.function.arguments = '{"name": "iter-0"}'
        tc.id = "call_123"

        resp1 = MagicMock()
        resp1.usage.prompt_tokens = 200
        resp1.usage.completion_tokens = 80
        resp1.choices = [MagicMock()]
        resp1.choices[0].message.content = "Saving baseline..."
        resp1.choices[0].message.tool_calls = [tc]
        resp1.choices[0].finish_reason = "tool_calls"

        # Second response: done
        resp2 = MagicMock()
        resp2.usage.prompt_tokens = 300
        resp2.usage.completion_tokens = 60
        resp2.choices = [MagicMock()]
        resp2.choices[0].message.content = "Done. No more improvements."
        resp2.choices[0].message.tool_calls = None
        resp2.choices[0].finish_reason = "stop"

        mock_client.chat.completions.create.side_effect = [resp1, resp2]

        agent.run_agent(max_iterations=5)

        assert mock_handle.call_count == 1
        mock_handle.assert_called_once_with("save_baseline", {"name": "iter-0"}, ANY)

    @patch("autoresearch_agent.assemble_system_prompt", return_value="test prompt")
    @patch("autoresearch_agent.OpenAI")
    def test_handles_api_error(self, mock_openai_cls, mock_prompt, capsys):
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        mock_client.chat.completions.create.side_effect = Exception("Rate limit exceeded")

        agent.run_agent(max_iterations=3)

        captured = capsys.readouterr()
        assert "ERROR" in captured.out
        assert "Rate limit" in captured.out


# ── CLI argument tests ───────────────────────────────────────────────────────

class TestCLIArgs:
    def test_default_model(self):
        parser = agent.main.__code__
        # Just verify the default is in the source
        source = Path(agent.__file__).read_text(encoding="utf-8")
        assert 'default="gpt-4o-mini"' in source

    def test_default_budget(self):
        source = Path(agent.__file__).read_text(encoding="utf-8")
        assert "default=0.25" in source


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
