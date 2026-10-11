"""Multi-agent procurement audit.

    purchase request
          |
          +--> Risk & Compliance agent --+
          +--> Tax & Treasury agent    --+--> CFO synthesis (one LLM call) --> audit memo
          +--> Financial Control agent --+

Each specialist is a LangChain v1 agent (create_agent) with its own prompt, tools and
a shared middleware stack (agent/middleware.py: PII redaction, call limits, retries,
tool-call logging). The ProcurementSupervisor runs them one after another, always in
the same order, and hands their reports to the CFO prompt.
Note: create_agent is built on LangGraph, but we never write graph code.
"""
from langchain.agents import create_agent

from agent.middleware import build_agent_middleware
from agent.prompts import (
    CONTROL_AGENT_PROMPT,
    RISK_AGENT_PROMPT,
    SYNTHESIS_PROMPT_TEMPLATE,
    TAX_AGENT_PROMPT,
)
from agent.tools import (
    calculate_cross_border_tax,
    categorize_expense,
    check_sanctions_list,
    get_vendor_credit_score,
    validate_fx_hedge,
)
from logger import GLOBAL_LOGGER as log
from rag.llm import get_llm


def create_specialized_agent(tools, system_prompt):
    """An agent = the LLM + a set of tools + a system prompt (+ middleware around the loop)."""
    return create_agent(
        model=get_llm(),
        tools=tools,
        system_prompt=system_prompt,
        middleware=build_agent_middleware(),
    )


class ProcurementSupervisor:
    """Runs the three specialist agents in order, then writes the CFO memo.

    One instance is built on the first audit request and shared by later requests
    (see get_supervisor() in api/endpoints.py).
    """

    def __init__(self):
        self.llm = get_llm()
        self.risk_agent = create_specialized_agent(
            [check_sanctions_list, get_vendor_credit_score], RISK_AGENT_PROMPT
        )
        self.tax_agent = create_specialized_agent(
            [calculate_cross_border_tax, validate_fx_hedge], TAX_AGENT_PROMPT
        )
        self.control_agent = create_specialized_agent(
            [categorize_expense], CONTROL_AGENT_PROMPT
        )

    @staticmethod
    def _invoke_agent(agent, request: str) -> str:
        """Run one agent and return the text of its final message."""
        result = agent.invoke({"messages": [{"role": "user", "content": request}]})
        return result["messages"][-1].text  # .text joins Gemini's content blocks

    def run_audit(self, request: str) -> dict:
        """Audit one purchase request and return its four texts.

        Returns a dict with the keys risk_result, tax_result, control_result and cfo_memo.
        The agents run one after another, not in parallel, and only the length of each
        phase result is logged (never its text). Exceptions are not caught here; the API
        route turns them into HTTP 500.
        """
        log.info("Starting audit phase", phase="1 - Risk & Compliance")
        risk_result = self._invoke_agent(self.risk_agent, request)
        log.info("Phase complete", phase="Risk & Compliance", result_chars=len(risk_result))

        log.info("Starting audit phase", phase="2 - Tax & Treasury")
        tax_result = self._invoke_agent(self.tax_agent, request)
        log.info("Phase complete", phase="Tax & Treasury", result_chars=len(tax_result))

        log.info("Starting audit phase", phase="3 - Financial Control")
        control_result = self._invoke_agent(self.control_agent, request)
        log.info("Phase complete", phase="Financial Control", result_chars=len(control_result))

        # Final synthesis by the CFO prompt (a plain LLM call, no tools)
        synthesis_prompt = SYNTHESIS_PROMPT_TEMPLATE.format(
            risk_result=risk_result,
            tax_result=tax_result,
            control_result=control_result,
        )
        log.info("Starting audit phase", phase="4 - CFO Synthesis")
        cfo_memo = self.llm.invoke(synthesis_prompt).text
        log.info("CFO Synthesis complete", memo_chars=len(cfo_memo))

        return {
            "risk_result": risk_result,
            "tax_result": tax_result,
            "control_result": control_result,
            "cfo_memo": cfo_memo,
        }


# Run directly for a quick test:  python -m agent.agents   (from the backend/ folder)
if __name__ == "__main__":
    sample_request = """
    Purchase Request — Aldermoor Industries Global Procurement:
    - Vendor: Takumi Controls Europe B.V. (Netherlands)
    - Item: Industrial PLC Controllers + HMI Panels (Qty: 200) for the Aldermoor filling line
    - Total Cost: 480,000 EUR
    - Origin: JP (Japan)
    - Destination: DE (Aldermoor Industries, Hamburg, Germany)
    - FX Rate quoted: 1 EUR = 163.5 JPY
    """
    memo = ProcurementSupervisor().run_audit(sample_request)
    print(memo["cfo_memo"])
