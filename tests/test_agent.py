import unittest

from app.agents.talent_intelligence.agent import TalentIntelligenceAgent
from app.agents.talent_intelligence.config import litellm_settings
from app.agents.talent_intelligence.prompts import SYSTEM_PROMPT
from app.agents.talent_intelligence.tools import (
    get_behavioral_context,
    get_learner_profile,
    get_milestone_history,
    get_skill_proofs,
)

LEARNER_A4_ID = "900353f6-f011-4d31-9a8a-b050b891c69c"
LEARNER_A7_ID = "087a2843-3c98-44d3-8ed1-81eeaccd440a"


class ToolTests(unittest.TestCase):
    def test_profile_lookup(self):
        result = get_learner_profile("Learner A4")
        self.assertEqual(result.status, "ok")
        self.assertEqual(result.data["learner_id"], LEARNER_A4_ID)

    def test_api_skill_proofs_include_citation_fields(self):
        result = get_skill_proofs(LEARNER_A4_ID, "api")
        self.assertEqual(result.status, "ok")
        item = result.data[0]
        self.assertTrue(item["evidence_id"])
        self.assertTrue(item["source_type"])
        self.assertTrue(item["date"])

    def test_missing_skill_is_empty(self):
        result = get_skill_proofs(LEARNER_A4_ID, "kubernetes")
        self.assertEqual(result.status, "insufficient_evidence")
        self.assertEqual(result.data, [])

    def test_behavioral_context_is_contextual(self):
        result = get_behavioral_context(LEARNER_A4_ID)
        self.assertEqual(result.status, "ok")
        self.assertTrue(result.data[0]["context"])
        self.assertIn("behavioral_engagement", result.data[0]["metric_key"])

    def test_milestones_are_chronological(self):
        result = get_milestone_history(LEARNER_A7_ID)
        self.assertEqual(result.status, "ok")
        dates = [item["date"] for item in result.data]
        self.assertEqual(dates, sorted(dates))


class AgentTests(unittest.TestCase):
    def test_agent_renders_evidence(self):
        agent = TalentIntelligenceAgent()
        answer = agent.respond(
            "Did they work with API?", learner_name_or_id="Learner A4"
        )
        self.assertIn("Observed evidence", answer)
        self.assertIn("[", answer)
        self.assertIn("meeting_transcript", answer)

    def test_agent_handles_missing_skill(self):
        agent = TalentIntelligenceAgent()
        answer = agent.respond(
            "Do they know Kubernetes?", learner_name_or_id="Learner A4"
        )
        self.assertIn("Insufficient evidence", answer)
        self.assertNotIn("has an available learner profile", answer)

    def test_agent_remembers_learner_in_follow_up(self):
        agent = TalentIntelligenceAgent()
        agent.respond("Did they work with API?", learner_name_or_id="Learner A4")
        answer = agent.respond("What is their history?")
        self.assertNotIn("Please provide a learner name", answer)
        self.assertIn("Observed evidence", answer)

    def test_reset_removes_active_learner(self):
        agent = TalentIntelligenceAgent()
        agent.respond("Did they work with API?", learner_name_or_id="Learner A4")
        agent.reset_conversation()
        answer = agent.respond("What is their history?")
        self.assertIn("Please provide a learner name", answer)

    def test_prompt_has_core_guardrails(self):
        self.assertIn("Insufficient evidence", SYSTEM_PROMPT)
        self.assertIn("Never invent", SYSTEM_PROMPT)
        self.assertIn("Do not diagnose personality", SYSTEM_PROMPT)

    def test_litellm_settings_are_optional(self):
        # The deterministic MVP must run even when no API credentials exist.
        settings = litellm_settings()
        self.assertTrue(
            settings is None
            or set(settings) == {"AI_AGENT_URL", "AI_API_KEY", "AI_MODEL"}
        )


if __name__ == "__main__":
    unittest.main()
