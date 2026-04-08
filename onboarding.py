"""First-run onboarding conversation to build a teacher profile."""

import json

import anthropic

import config
from memory import Memory
from prompts import ONBOARDING_PROMPT, MEMORY_EXTRACTION_PROMPT


def extract_profile_facts(
    client: anthropic.Anthropic,
    teacher_msg: str,
    assistant_msg: str,
) -> list[dict]:
    """Use Claude to extract profile facts from an onboarding exchange."""
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
    # Handle markdown code fences around JSON
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return []


def run_onboarding(memory: Memory) -> None:
    """Run the onboarding conversation to build a teacher profile."""
    client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
    messages: list[dict] = []

    # Get initial greeting
    response = client.messages.create(
        model=config.CLAUDE_MODEL,
        max_tokens=1024,
        system=ONBOARDING_PROMPT,
        messages=[{"role": "user", "content": "Hi, I'm a new teacher using this tool."}],
    )
    greeting = response.content[0].text
    print(f"\n🎓 Dewey: {greeting}\n")
    messages.append({"role": "user", "content": "Hi, I'm a new teacher using this tool."})
    messages.append({"role": "assistant", "content": greeting})

    print("(Type 'done' when you're ready to start planning)\n")

    while True:
        try:
            teacher_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not teacher_input:
            continue

        if teacher_input.lower() == "done":
            print("\n🎓 Dewey: Great — I've got a good picture of your "
                  "teaching context. Let's plan.\n")
            break

        messages.append({"role": "user", "content": teacher_input})

        response = client.messages.create(
            model=config.CLAUDE_MODEL,
            max_tokens=1024,
            system=ONBOARDING_PROMPT,
            messages=messages,
        )
        assistant_msg = response.content[0].text
        messages.append({"role": "assistant", "content": assistant_msg})

        print(f"\n🎓 Dewey: {assistant_msg}\n")

        # Extract and store profile facts from this exchange
        facts = extract_profile_facts(client, teacher_input, assistant_msg)
        for fact in facts:
            memory.store(
                content=fact.get("content", ""),
                collection=config.PROFILE_COLLECTION,
                category=fact.get("category", "profile"),
            )

    # Store the full onboarding conversation too
    full_convo = "\n".join(
        f"{'Teacher' if m['role'] == 'user' else 'Dewey'}: {m['content']}"
        for m in messages
    )
    memory.store(
        content=full_convo,
        collection=config.CONVERSATION_COLLECTION,
        category="onboarding",
        metadata={"type": "onboarding"},
    )
