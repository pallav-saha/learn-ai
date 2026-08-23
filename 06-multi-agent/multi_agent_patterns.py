"""
Multi-Agent Patterns — Advanced collaboration strategies

This demonstrates 4 patterns:
1. PARALLEL — Multiple agents work simultaneously, results merged
2. MANAGER/WORKER — One agent delegates dynamically
3. DEBATE/CONSENSUS — Agents argue, a judge decides
4. AGENT WITH SUB-AGENTS — Agent uses other agents as tools

Run: python3 multi_agent_patterns.py
"""

import os
import json
import concurrent.futures
from dotenv import load_dotenv
from openai import OpenAI
from utils import retry_on_failure

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

client = OpenAI(
    api_key=os.getenv("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1",
)

MODEL = "openai/gpt-oss-120b"


# ============================================================
# AGENT BASE (same as before)
# ============================================================

class Agent:
    def __init__(self, name: str, role: str, system_prompt: str):
        self.name = name
        self.role = role
        self.system_prompt = system_prompt

    @retry_on_failure(max_retries=3, delay=2.0)
    def run(self, task: str) -> str:
        print(f"   🤖 {self.name} ({self.role}) working...")
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": task},
            ],
            temperature=0.7,
        )
        output = response.choices[0].message.content
        print(f"   ✅ {self.name} done ({len(output)} chars)")
        return output


# ============================================================
# PATTERN 1: PARALLEL AGENTS
# ============================================================
# Multiple agents work on the same question from different angles
# simultaneously, then a merger agent combines their findings.
#
# Real-world use: Search multiple sources at once, get diverse
# perspectives, then synthesize.
# ============================================================

def demo_parallel():
    print("\n" + "=" * 60)
    print("  PATTERN 1: PARALLEL AGENTS")
    print("  Multiple agents work at the same time, results merged")
    print("=" * 60)

    # Three researchers, each with a different focus
    tech_researcher = Agent(
        name="Tech Researcher",
        role="Technology perspective",
        system_prompt="You research topics from a TECHNOLOGY perspective. Focus on tools, platforms, technical innovations. Give 3-4 bullet points. Be concise.",
    )

    business_researcher = Agent(
        name="Business Researcher",
        role="Business perspective",
        system_prompt="You research topics from a BUSINESS perspective. Focus on market size, companies, revenue, adoption rates. Give 3-4 bullet points. Be concise.",
    )

    society_researcher = Agent(
        name="Society Researcher",
        role="Social impact perspective",
        system_prompt="You research topics from a SOCIAL IMPACT perspective. Focus on how it affects people, jobs, ethics, daily life. Give 3-4 bullet points. Be concise.",
    )

    # Merger agent combines all perspectives
    merger = Agent(
        name="Synthesizer",
        role="Combine findings",
        system_prompt="You take research from multiple perspectives and create a unified, comprehensive summary. Organize by theme, not by source. Write 2-3 paragraphs.",
    )

    topic = input("\n   📝 Enter a topic (or press Enter for 'AI in healthcare'): ").strip()
    if not topic:
        topic = "AI in healthcare"

    print(f"\n   🔍 Researching '{topic}' from 3 perspectives simultaneously...")

    # Run all 3 agents in parallel (at the same time!)
    # This is faster than running them one-by-one
    import time
    time.sleep(1)  # Small delay to avoid rate limit
    results = {}

    # Sequential but simulating parallel concept
    # (True parallel would use threads, but rate limits make it tricky)
    print("\n   --- Technology Perspective ---")
    results["tech"] = tech_researcher.run(f"Research from a technology angle: {topic}")
    time.sleep(2)

    print("\n   --- Business Perspective ---")
    results["business"] = business_researcher.run(f"Research from a business angle: {topic}")
    time.sleep(2)

    print("\n   --- Social Impact Perspective ---")
    results["society"] = society_researcher.run(f"Research from a social impact angle: {topic}")
    time.sleep(2)

    # Merge all findings
    print("\n   --- Synthesizing ---")
    combined = merger.run(
        f"Combine these research findings into a unified summary:\n\n"
        f"TECHNOLOGY PERSPECTIVE:\n{results['tech']}\n\n"
        f"BUSINESS PERSPECTIVE:\n{results['business']}\n\n"
        f"SOCIAL IMPACT PERSPECTIVE:\n{results['society']}"
    )

    print(f"\n{'─' * 60}")
    print(f"📄 FINAL SYNTHESIS:\n\n{combined}")


# ============================================================
# PATTERN 2: MANAGER / WORKER
# ============================================================
# One "manager" agent reads the task and DECIDES which specialized
# worker agent to assign it to. The manager doesn't do the work
# itself — it delegates.
#
# Real-world use: Customer support routing, task assignment,
# dynamic workflow orchestration.
# ============================================================

def demo_manager_worker():
    print("\n" + "=" * 60)
    print("  PATTERN 2: MANAGER / WORKER")
    print("  Manager decides which specialist to assign the task to")
    print("=" * 60)

    # Specialist workers
    workers = {
        "coder": Agent(
            name="Coder",
            role="Python developer",
            system_prompt="You are an expert Python developer. Write clean, working code with comments. Only write code, no extra explanation.",
        ),
        "writer": Agent(
            name="Writer",
            role="Content writer",
            system_prompt="You are a professional content writer. Write engaging, clear content. Match the tone to the audience.",
        ),
        "analyst": Agent(
            name="Analyst",
            role="Data analyst",
            system_prompt="You are a data analyst. Analyze information, find patterns, provide insights with numbers and conclusions.",
        ),
        "advisor": Agent(
            name="Advisor",
            role="Strategy advisor",
            system_prompt="You are a strategy advisor. Give practical, actionable advice. Consider pros, cons, and alternatives.",
        ),
    }

    # The manager decides who to assign work to
    @retry_on_failure(max_retries=3, delay=2.0)
    def manager_decide(task: str) -> str:
        """Manager reads the task and picks the best worker."""
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a manager who assigns tasks to the right specialist. "
                        "Your team has: coder, writer, analyst, advisor. "
                        "Respond with ONLY the worker name (one word). "
                        "coder = programming tasks. writer = content/emails/docs. "
                        "analyst = data/numbers/trends. advisor = decisions/strategy."
                    ),
                },
                {"role": "user", "content": f"Who should handle this task?\n\n{task}"},
            ],
            temperature=0.0,
        )
        return response.choices[0].message.content.strip().lower()

    print("""
   Available workers:
     💻 Coder   — programming tasks
     ✍️  Writer  — content, emails, docs
     📊 Analyst — data, numbers, trends
     🧠 Advisor — decisions, strategy

   Try:
     • "Write a Python function to find prime numbers"
     • "Draft an email to a client about project delays"
     • "Analyze the pros and cons of moving to microservices"
     • "What should my startup focus on first?"
""")

    task = input("   📝 Your task: ").strip()
    if not task:
        task = "Write a Python function to calculate compound interest"

    # Manager decides
    print(f"\n   👔 Manager analyzing task...")
    assigned = manager_decide(task)

    # Clean up the assignment
    assigned_clean = None
    for worker_name in workers:
        if worker_name in assigned:
            assigned_clean = worker_name
            break

    if not assigned_clean:
        assigned_clean = "coder"  # Default fallback

    print(f"   👔 Manager assigned to: {assigned_clean.upper()}")

    # Worker does the task
    import time
    time.sleep(2)
    print(f"\n   --- {assigned_clean.title()} working ---")
    result = workers[assigned_clean].run(task)

    print(f"\n{'─' * 60}")
    print(f"📄 RESULT (by {assigned_clean.title()}):\n\n{result}")


# ============================================================
# PATTERN 3: DEBATE / CONSENSUS
# ============================================================
# Two agents argue opposing sides, then a judge weighs both
# arguments and makes a final decision.
#
# Real-world use: Decision making, exploring trade-offs,
# ensuring balanced analysis before committing to a choice.
# ============================================================

def demo_debate():
    print("\n" + "=" * 60)
    print("  PATTERN 3: DEBATE / CONSENSUS")
    print("  Two agents argue, a judge decides")
    print("=" * 60)

    pro_agent = Agent(
        name="Pro Agent",
        role="Argues FOR",
        system_prompt=(
            "You argue IN FAVOR of the given position. "
            "Give 3 strong arguments with evidence. Be persuasive but honest. "
            "Acknowledge weaknesses briefly but emphasize strengths."
        ),
    )

    con_agent = Agent(
        name="Con Agent",
        role="Argues AGAINST",
        system_prompt=(
            "You argue AGAINST the given position. "
            "Give 3 strong counterarguments with evidence. Be persuasive but honest. "
            "Acknowledge strengths briefly but emphasize weaknesses."
        ),
    )

    judge = Agent(
        name="Judge",
        role="Makes final decision",
        system_prompt=(
            "You are an impartial judge. You've heard arguments from both sides. "
            "Evaluate both positions fairly, then give your verdict with reasoning. "
            "Structure: Summary of each side → Your analysis → Final verdict. "
            "Be balanced and nuanced."
        ),
    )

    print("""
   Example topics to debate:
     • "Should companies adopt AI for hiring decisions?"
     • "Is remote work better than office work?"
     • "Should startups use microservices from day one?"
     • "Is Python better than JavaScript for backend?"
""")

    topic = input("   📝 Debate topic: ").strip()
    if not topic:
        topic = "Should companies adopt AI for hiring decisions?"

    import time

    # Pro argues
    print(f"\n   --- Pro Agent (FOR) ---")
    pro_args = pro_agent.run(f"Argue IN FAVOR of: {topic}")
    time.sleep(2)

    # Con argues
    print(f"\n   --- Con Agent (AGAINST) ---")
    con_args = con_agent.run(f"Argue AGAINST: {topic}")
    time.sleep(2)

    # Judge decides
    print(f"\n   --- Judge (VERDICT) ---")
    verdict = judge.run(
        f"Topic: {topic}\n\n"
        f"ARGUMENTS FOR:\n{pro_args}\n\n"
        f"ARGUMENTS AGAINST:\n{con_args}\n\n"
        f"Give your verdict:"
    )

    print(f"\n{'─' * 60}")
    print(f"⚖️  DEBATE RESULTS:\n")
    print(f"✅ FOR:\n{pro_args}\n")
    print(f"❌ AGAINST:\n{con_args}\n")
    print(f"⚖️  VERDICT:\n{verdict}")


# ============================================================
# PATTERN 4: AGENT WITH SUB-AGENTS (as tools)
# ============================================================
# A main agent has access to other agents as "tools".
# It decides when to call which sub-agent, just like your
# agent_basics.py decides when to use calculator vs Wikipedia.
#
# This is how Kiro works — it can dispatch sub-agents for
# research, code review, etc.
# ============================================================

def demo_agent_with_subagents():
    print("\n" + "=" * 60)
    print("  PATTERN 4: AGENT WITH SUB-AGENTS (as tools)")
    print("  Main agent decides which sub-agent to call")
    print("=" * 60)

    # Sub-agents available as "tools"
    sub_agents = {
        "researcher": Agent(
            name="Researcher",
            role="Finds information",
            system_prompt="You research topics and return concise, factual summaries. 3-5 sentences max.",
        ),
        "coder": Agent(
            name="Coder",
            role="Writes code",
            system_prompt="You write clean Python code. Return only code with comments, no explanation.",
        ),
        "summarizer": Agent(
            name="Summarizer",
            role="Condenses text",
            system_prompt="You summarize text into 2-3 key bullet points. Be extremely concise.",
        ),
    }

    # Main agent with access to sub-agents
    @retry_on_failure(max_retries=3, delay=2.0)
    def main_agent_plan(goal: str) -> list[dict]:
        """
        Main agent breaks down a complex goal into steps,
        assigning each step to a sub-agent.
        """
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a planning agent. Break down a user's goal into 2-3 steps. "
                        "For each step, assign it to one of these sub-agents: researcher, coder, summarizer. "
                        "Return a JSON array of steps. Each step has 'agent' and 'task'. "
                        "Return ONLY valid JSON, nothing else.\n\n"
                        "Example: [{\"agent\": \"researcher\", \"task\": \"Find info about X\"}, "
                        "{\"agent\": \"coder\", \"task\": \"Write a function that does Y\"}]"
                    ),
                },
                {"role": "user", "content": goal},
            ],
            temperature=0.0,
        )

        text = response.choices[0].message.content.strip()
        # Clean up markdown fences
        text = text.replace("```json", "").replace("```", "").strip()

        try:
            steps = json.loads(text)
            return steps
        except json.JSONDecodeError:
            return [{"agent": "researcher", "task": goal}]

    print("""
   The main agent has 3 sub-agents:
     🔬 Researcher — finds information
     💻 Coder     — writes code
     📝 Summarizer — condenses text

   Give a complex goal and watch the main agent
   break it into steps and delegate:

   Examples:
     • "Research what FastAPI is and write a hello world example"
     • "Explain recursion and write a factorial function"
     • "Find out about Docker and summarize the key concepts"
""")

    goal = input("   🎯 Your goal: ").strip()
    if not goal:
        goal = "Research what FastAPI is and write a hello world example"

    import time

    # Main agent creates a plan
    print(f"\n   🧠 Main agent planning...")
    steps = main_agent_plan(goal)

    print(f"   📋 Plan ({len(steps)} steps):")
    for i, step in enumerate(steps, 1):
        print(f"      {i}. [{step['agent']}] {step['task']}")

    # Execute each step
    results = []
    for i, step in enumerate(steps, 1):
        print(f"\n   {'─' * 40}")
        print(f"   Step {i}:")
        time.sleep(2)

        agent_name = step["agent"]
        if agent_name in sub_agents:
            result = sub_agents[agent_name].run(step["task"])
        else:
            result = sub_agents["researcher"].run(step["task"])

        results.append({"step": step, "result": result})

    # Combine results
    print(f"\n{'─' * 60}")
    print(f"📄 FINAL OUTPUT (combined from all sub-agents):\n")
    for i, r in enumerate(results, 1):
        print(f"--- Step {i} ({r['step']['agent']}) ---")
        print(f"{r['result']}\n")


# ============================================================
# INTERACTIVE DEMO
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("  🤖 MULTI-AGENT PATTERNS")
    print("=" * 60)
    print("""
Choose a pattern to try:

  1) PARALLEL     — Multiple researchers, findings merged
  2) MANAGER      — Manager assigns to the right specialist
  3) DEBATE       — Pro vs Con, judge decides
  4) SUB-AGENTS   — Main agent delegates to sub-agents
""")

    choice = input("Choice (1-4): ").strip()

    if choice == "1":
        demo_parallel()
    elif choice == "2":
        demo_manager_worker()
    elif choice == "3":
        demo_debate()
    elif choice == "4":
        demo_agent_with_subagents()
    else:
        print("Invalid choice. Run again.")
