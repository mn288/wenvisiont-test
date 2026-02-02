import uuid

import orjson
from langchain_core.runnables import RunnableConfig

from brain.logger import LogHandler, app_logger
from core.database import pool
from crew.agents import llm
from models.state import AgentResult, GraphState
from services.tools import tool_service


async def tool_planning_node(state: GraphState, config: RunnableConfig) -> dict:
    """
    Plan tool execution based on the user request.
    Identifies the best tool and arguments.
    """
    logger = LogHandler(pool)
    thread_id = config["configurable"]["thread_id"]
    checkpoint_id = config["configurable"].get("checkpoint_id")

    await logger.log_step(thread_id, "tool_planning", "info", "Planning Tool Execution...", checkpoint_id)

    # 1. Fetch available tools via Global Service
    # Force refresh to ensure we pick up any newly added or recovered servers (e.g. MCP)
    tools = await tool_service.get_all_tools(force_refresh=True)

    if not tools:
        msg = "No tools available."
        await logger.log_step(thread_id, "tool_planning", "warning", msg, checkpoint_id)
        return {
            "results": [
                AgentResult(
                    task_id=str(uuid.uuid4()), summary=msg, raw_output=msg, metadata={"error": True}
                ).model_dump()
            ]
        }

    # 2. Construct Prompt for Tool Selection
    tools_desc = "\n".join([f"- {t.name}: {t.description} (Args: {t.args_schema.schema()})" for t in tools])

    prompt = f"""You are a Tool Planner.
    User Request: "{state["input_request"]}"
    
    Available Tools:
    {tools_desc}
    
    Select the best tool to likely answer the request.
    Return STRICT JSON ONLY:
    {{
      "tool_name": "exact_tool_name",
      "arguments": {{ "arg_name": "value" }}
    }}
    
    If no tool is relevant, return {{ "tool_name": null }}.
    """

    # 3. Call LLM
    response = await llm.acall(prompt)

    # 4. Parse Decision
    try:
        clean_json = response.replace("```json", "").replace("```", "").strip()
        decision = orjson.loads(clean_json)

        tool_name = decision.get("tool_name")
        if not tool_name:
            await logger.log_step(thread_id, "tool_planning", "thought", "No relevant tool found.", checkpoint_id)
            return {
                "results": [
                    AgentResult(
                        task_id=str(uuid.uuid4()),
                        summary="Tool Planner found no relevant tools.",
                        raw_output="No tools applied.",
                        metadata={"agent": "tool_planner"},
                    ).model_dump()
                ]
            }

        await logger.log_step(
            thread_id, "tool_planning", "output", f"Selected: {tool_name} {decision.get('arguments')}", checkpoint_id
        )

        return {"tool_call": {"name": tool_name, "args": decision.get("arguments", {})}}

    except Exception as e:
        err_msg = f"Failed to parse tool plan: {e}"
        await logger.log_step(thread_id, "tool_planning", "error", err_msg, checkpoint_id)
        return {
            "results": [
                AgentResult(
                    task_id=str(uuid.uuid4()), summary=err_msg, raw_output=err_msg, metadata={"error": True}
                ).model_dump()
            ]
        }


async def tool_execution_node(state: GraphState, config: RunnableConfig) -> dict:
    """
    Execute the planned tool.
    """
    logger = LogHandler(pool)
    thread_id = config["configurable"]["thread_id"]
    checkpoint_id = config["configurable"].get("checkpoint_id")

    tool_call = state.get("tool_call")
    if not tool_call:
        return {}  # Should shouldn't happen if edge routing is correct

    tool_name = tool_call["name"]
    tool_args = tool_call["args"]

    # Use tool name in log instead of generic "tool_execution"
    log_name = f"tool_{tool_name}"
    await logger.log_step(thread_id, log_name, "info", f"Executing {tool_name}...", checkpoint_id)

    # Re-load tools to find the object
    target_tool = await tool_service.get_tool(tool_name)

    if not target_tool:
        err_msg = f"Tool '{tool_name}' not found during execution."
        await logger.log_step(thread_id, log_name, "error", err_msg, checkpoint_id)
        return {
            "results": [
                AgentResult(
                    task_id=str(uuid.uuid4()),
                    summary=err_msg,
                    raw_output=err_msg,
                    metadata={"error": True, "tool": tool_name},
                ).model_dump()
            ]
        }

    try:
        # Execute (Async) using standard LangChain invocation if available, fallback to internal if needed.
        # Most CrewAI/LangChain tools support ainvoke.
        if hasattr(target_tool, "ainvoke"):
            output = await target_tool.ainvoke(tool_args)
        elif hasattr(target_tool, "_arun"):
            # Fallback for older tools (though we should avoid calling private methods)
            output = await target_tool._arun(**tool_args)
        else:
            # Sync tool fallback (run in threadpool usually handled by ainvoke, but manual check here)
            output = target_tool.run(tool_args)

        # Handle Structured Output (e.g. dict with content & citations)
        citations = []
        output_str = str(output)

        # If output is a dict, checks keys
        if isinstance(output, dict):
            output_str = output.get("context") or output.get("result") or output.get("content") or str(output)
            # Try to find citations
            raw_citations = output.get("citations", [])
            for c in raw_citations:
                try:
                    # If it's already a Citation object (unlikely from raw tool but possible if internal)
                    if hasattr(c, "model_dump"):
                        citations.append(c)
                    elif isinstance(c, dict):
                        # Validate against Citation model
                        from models.state import Citation

                        citations.append(Citation(**c))
                except Exception as cit_err:
                    app_logger.warning(f"Warning: Failed to parse citation: {cit_err}")

        # Also check if output is a JSON string containing structure
        elif isinstance(output, str):
            try:
                # Attempt light parsing if it looks like JSON
                if output.strip().startswith("{") and "citations" in output:
                    parsed = orjson.loads(output)
                    if isinstance(parsed, dict) and "citations" in parsed:
                        output_str = parsed.get("context") or parsed.get("result") or parsed.get("content") or output
                        raw_citations = parsed.get("citations", [])
                        from models.state import Citation

                        for c in raw_citations:
                            citations.append(Citation(**c))
            except Exception:
                pass  # Not JSON, treat as raw string

        await logger.log_step(thread_id, log_name, "output", f"Result: {output_str[:200]}...", checkpoint_id)

        # Construct Result
        agent_result = AgentResult(
            task_id=str(uuid.uuid4()),
            summary=f"Tool '{tool_name}' returned: {output_str}",
            raw_output=output_str,
            metadata={"tool": tool_name},
            citations=citations,
        )

        return {
            "results": [agent_result.model_dump()],
            "citations": citations,  # Add to global state list
            "context": f"\n\nTool '{tool_name}' Output:\n{output_str}",
            "tool_call": None,  # Clear it
        }
    except Exception as e:
        err_msg = f"Tool execution failed: {e}"
        await logger.log_step(thread_id, log_name, "error", err_msg, checkpoint_id)
        return {
            "results": [
                AgentResult(
                    task_id=str(uuid.uuid4()),
                    summary=err_msg,
                    raw_output=err_msg,
                    metadata={"error": True, "tool": tool_name},
                ).model_dump()
            ]
        }
