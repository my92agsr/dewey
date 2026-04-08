"""Dewey — AI instructional planning partner for K-12 teachers."""

import json

import anthropic
import click

import config
from memory import Memory
from onboarding import run_onboarding
from prompts import SYSTEM_PROMPT, MEMORY_EXTRACTION_PROMPT
from tools import filesystem, standards, differentiate

# Collect all tool definitions and handlers
ALL_TOOLS = filesystem.TOOLS + standards.TOOLS + differentiate.TOOLS

TOOL_HANDLERS = {
    "save_lesson_plan": filesystem.handle_tool_call,
    "list_lesson_plans": filesystem.handle_tool_call,
    "search_standards": standards.handle_tool_call,
    "search_wida": standards.handle_tool_call,
    "differentiate_lesson": differentiate.handle_tool_call,
}


def ferpa_filter(text: str) -> tuple[str, bool]:
    """Strip potential student PII from text. Returns (cleaned_text, was_modified)."""
    modified = False
    cleaned = text
    for pattern in config.FERPA_PATTERNS:
        if pattern.search(cleaned):
            cleaned = pattern.sub("[REDACTED]", cleaned)
            modified = True
    return cleaned, modified


def build_context(memory: Memory, query: str) -> tuple[str, str]:
    """Build teacher profile and memory context strings for the system prompt."""
    # Teacher profile — always included
    profile_items = memory.get_all(config.PROFILE_COLLECTION)
    if profile_items:
        profile_text = "\n".join(f"- {item['content']}" for item in profile_items)
    else:
        profile_text = "No profile information yet."

    # Relevant past conversations — retrieved by similarity
    memory_items = memory.retrieve(
        query=query,
        collection=config.CONVERSATION_COLLECTION,
        limit=config.MAX_MEMORY_RESULTS,
    )
    if memory_items:
        memory_text = "\n\n".join(
            f"[Relevance: {1 - item['distance']:.2f}]\n{item['content']}"
            for item in memory_items
        )
    else:
        memory_text = "No prior conversations yet."

    return profile_text, memory_text


def extract_and_store_memories(
    client: anthropic.Anthropic,
    memory: Memory,
    teacher_msg: str,
    assistant_msg: str,
):
    """Extract noteworthy facts from the exchange and store them."""
    try:
        response = client.messages.create(
            model=config.CLAUDE_MODEL,
            max_tokens=1024,
            messages=[
                {
                    "role": "user",
                    "content": MEMORY_EXTRACTION_PROMPT.format(
                        teacher_message=teacher_msg,
                        assistant_response=assistant_msg,
                    ),
                }
            ],
        )
        text = response.content[0].text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        facts = json.loads(text)

        for fact in facts:
            content = fact.get("content", "")
            category = fact.get("category", "context")
            if not content:
                continue
            collection = (
                config.PROFILE_COLLECTION
                if category == "profile"
                else config.CONVERSATION_COLLECTION
            )
            memory.store(content=content, collection=collection, category=category)
    except (json.JSONDecodeError, Exception):
        # Memory extraction is best-effort — don't crash the conversation
        pass


@click.command()
@click.option("--reset", is_flag=True, help="Reset all memory and start fresh.")
def main(reset: bool):
    """Dewey — your instructional planning partner."""
    if reset:
        config.DB_PATH.unlink(missing_ok=True)
        click.echo("Memory cleared. Starting fresh.\n")

    memory = Memory()
    client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)

    click.echo("=" * 60)
    click.echo("  Dewey — Instructional Planning Partner")
    click.echo("=" * 60)

    # Onboarding if no profile exists
    if not memory.has_profile():
        click.echo("\nLooks like this is your first time here. Let's get acquainted.\n")
        run_onboarding(memory, ferpa_filter)

    click.echo("Ready to plan. Type 'quit' to exit.\n")

    messages: list[dict] = []

    while True:
        try:
            teacher_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            click.echo("\nSee you next period. ✌️")
            break

        if not teacher_input:
            continue

        if teacher_input.lower() in ("quit", "exit", "q"):
            click.echo("See you next period. ✌️")
            break

        # FERPA filter — strip PII before it hits the API
        cleaned_input, had_pii = ferpa_filter(teacher_input)

        # Build context from memory
        profile_text, memory_text = build_context(memory, cleaned_input)

        system = SYSTEM_PROMPT.format(
            teacher_profile=profile_text,
            memory_context=memory_text,
        )

        # Add to conversation history
        messages.append({"role": "user", "content": cleaned_input})

        # Keep conversation history manageable — last 20 turns
        recent_messages = messages[-40:]  # 40 entries = 20 turns

        # Tool-use loop: keep calling until we get a final text response
        assistant_msg = ""
        tool_log = []
        loop_messages = list(recent_messages)

        while True:
            response = client.messages.create(
                model=config.CLAUDE_MODEL,
                max_tokens=4096,
                system=system,
                tools=ALL_TOOLS,
                messages=loop_messages,
            )

            # Collect text blocks from this response
            text_parts = [b.text for b in response.content if b.type == "text"]

            # Check for tool use
            tool_uses = [b for b in response.content if b.type == "tool_use"]

            if not tool_uses:
                # Final response — no more tools to call
                assistant_msg = "\n".join(text_parts)
                break

            # Process tool calls
            loop_messages.append({"role": "assistant", "content": response.content})

            tool_results = []
            for tool_use in tool_uses:
                handler = TOOL_HANDLERS.get(tool_use.name)
                if handler:
                    result_text = handler(tool_use.name, tool_use.input)
                    tool_log.append(f"[used {tool_use.name}]")
                else:
                    result_text = f"Unknown tool: {tool_use.name}"
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tool_use.id,
                    "content": result_text,
                })

            loop_messages.append({"role": "user", "content": tool_results})

        # Record final assistant message in the conversation history
        messages.append({"role": "assistant", "content": assistant_msg})

        # Display response
        if tool_log:
            click.echo(click.style(f"  {'  '.join(tool_log)}", dim=True))
        output = assistant_msg
        if had_pii:
            output += config.FERPA_REMINDER
        click.echo(f"\n🎓 Dewey: {output}\n")

        # Store the exchange in conversation memory
        memory.store_exchange(cleaned_input, assistant_msg)

        # Extract new facts in the background (best-effort)
        extract_and_store_memories(client, memory, cleaned_input, assistant_msg)

    memory.close()


if __name__ == "__main__":
    main()
