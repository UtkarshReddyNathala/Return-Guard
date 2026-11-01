"""The pipeline steps (LangGraph nodes).

All nine agent steps are in `agents.py` (about 250 lines, read top to bottom), with
shared code in `base.py`. The Governance Gate, the only step that finalizes a
decision, is in `pipeline/governance.py`, and the graph wiring is in
`pipeline/graph.py`.

    agents.data_quality   agents.planner   agents.intake   agents.policy
    agents.image          agents.behavior  agents.decision agents.critic
    agents.explanation    governance.run

Each step writes an `agent_runs` row and streams `agent_run_events`, and every model
call checks the agent's model permission (`models_config.assert_grant`).
"""
