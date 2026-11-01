# ReturnGuard: which tools and which model roles each agent may use (least privilege),
# written as OPA policy.
#
#   input {agent, tool}  -> data.returnguard.authz.allow_tool   (true/false)
#   input {agent, role}  -> data.returnguard.authz.allow_model  (true/false)
#
# The worker asks OPA before every tool call and every model call. This is the check
# that really blocks a call: OSS ContextForge hides tools but does not block calls to
# them, and OSS Bifrost virtual keys are off by default. worker/pipeline/mcp_client.py
# and models_config.py keep a copy of these two maps for when OPA cannot be reached;
# they MUST match this file.

package returnguard.authz

tool_grants := {
	"intake": ["get_order"],
	"policy": ["check_policy"],
	"behavior": ["get_customer_history", "flag_ring"],
	"decision": ["get_order", "check_policy", "get_customer_history"],
	"planner": [],
	"image": [],
	"critic": [],
	"explanation": [],
}

model_grants := {
	"planner": ["fast"],
	"intake": ["fast"],
	"policy": ["reason", "embed"],
	"image": ["vision"],
	"behavior": ["reason"],
	"decision": ["reason", "deep"],
	"critic": ["deep"],
	"explanation": ["deep"],
}

default allow_tool := false

allow_tool if input.tool in object.get(tool_grants, input.agent, [])

default allow_model := false

allow_model if input.role in object.get(model_grants, input.agent, [])
