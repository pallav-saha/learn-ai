"""
Multi-Agent System — Multiple AI agents collaborating on a task

This builds a content creation pipeline with 3 specialized agents:
1. RESEARCHER — Finds facts and information about a topic
2. WRITER — Takes research and writes a blog post
3. REVIEWER — Reviews the blog post and suggests improvements

Each agent has its own role, personality, and job.
They pass work to each other in sequence.

Run: python3 01_multi_agent.py
"""

import os
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
# AGENT BASE — Each agent is defined by its role and system prompt
# ============================================================

class Agent:
    """
    An agent is just an LLM call with a specific personality/role.
    
    The key insight: same LLM, different system prompts = different specialists.
    """

    def __init__(self, name: str, role: str, system_prompt: str):
        self.name = name
        self.role = role
        self.system_prompt = system_prompt

    @retry_on_failure(max_retries=3, delay=1.0)
    def run(self, task: str) -> str:
        """Give the agent a task, get its output."""
        print(f"\n{'─' * 50}")
        print(f"🤖 {self.name} ({self.role})")
        print(f"   Task: {task[:100]}{'...' if len(task) > 100 else ''}")
        print(f"   Working...")

        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": task},
            ],
            temperature=0.7,
        )

        output = response.choices[0].message.content
        print(f"   ✅ Done! ({len(output)} chars)")
        return output


# ============================================================
# DEFINE THE TEAM — 3 specialized agents
# ============================================================

researcher = Agent(
    name="Alex",
    role="Researcher",
    system_prompt=(
        "You are a research specialist. Your job is to find and organize key facts "
        "about a given topic. Return 5-7 bullet points of interesting, accurate facts "
        "that would make a good blog post. Focus on recent developments, statistics, "
        "and surprising insights. Be factual and cite-worthy."
    ),
)

writer = Agent(
    name="Sam",
    role="Writer",
    system_prompt=(
        "You are a skilled blog writer. Your job is to take research notes and turn them "
        "into an engaging blog post. Write in a conversational, approachable tone. "
        "The post should have: a catchy title, an intro hook, 3-4 sections with headers, "
        "and a conclusion. Keep it around 300-400 words. Make it interesting for beginners."
    ),
)

reviewer = Agent(
    name="Maya",
    role="Reviewer",
    system_prompt=(
        "You are an editor and quality reviewer. Your job is to review a blog post and provide: "
        "1. A quality score (1-10) "
        "2. Three specific things done well "
        "3. Three specific improvements needed "
        "4. A revised version of the post with your improvements applied. "
        "Focus on clarity, accuracy, engagement, and flow."
    ),
)


# ============================================================
# THE PIPELINE — Agents pass work to each other
# ============================================================

def run_content_pipeline(topic: str) -> dict:
    """
    Multi-agent pipeline:
    
    User gives topic
         ↓
    [Researcher] → produces research notes
         ↓
    [Writer] → takes notes, produces blog post
         ↓
    [Reviewer] → reviews post, gives final version
         ↓
    Final output
    """
    print("=" * 60)
    print(f"  📝 CONTENT PIPELINE: \"{topic}\"")
    print("=" * 60)

    # Step 1: Researcher finds facts
    research = researcher.run(
        f"Research the following topic and provide 5-7 key facts and insights:\n\n{topic}"
    )

    # Step 2: Writer creates blog post from research
    blog_post = writer.run(
        f"Write a blog post based on these research notes:\n\n{research}"
    )

    # Step 3: Reviewer checks quality and improves
    review = reviewer.run(
        f"Review this blog post and provide your assessment and improved version:\n\n{blog_post}"
    )

    return {
        "topic": topic,
        "research": research,
        "draft": blog_post,
        "review": review,
    }


# ============================================================
# ADVANCED: Agents with back-and-forth (iterative improvement)
# ============================================================

def run_iterative_pipeline(topic: str, max_rounds: int = 2) -> dict:
    """
    Advanced pipeline where agents iterate:
    
    1. Researcher → Writer → Reviewer
    2. If score < 8: Writer revises based on feedback → Reviewer checks again
    3. Repeat until score >= 8 or max_rounds reached
    
    This shows how agents can COLLABORATE, not just pass work linearly.
    """
    print("=" * 60)
    print(f"  🔄 ITERATIVE PIPELINE: \"{topic}\"")
    print(f"  (Will revise until quality score >= 8)")
    print("=" * 60)

    # Step 1: Research
    research = researcher.run(
        f"Research the following topic and provide 5-7 key facts:\n\n{topic}"
    )

    # Step 2: First draft
    blog_post = writer.run(
        f"Write a blog post based on these research notes:\n\n{research}"
    )

    # Step 3: Review loop
    for round_num in range(1, max_rounds + 1):
        print(f"\n{'═' * 50}")
        print(f"  📋 Review Round {round_num}")
        print(f"{'═' * 50}")

        review = reviewer.run(
            f"Review this blog post. Start your response with 'SCORE: X/10' on the first line.\n\n{blog_post}"
        )

        # Check if score is good enough
        try:
            score_line = review.split("\n")[0]
            score = int("".join(c for c in score_line if c.isdigit())[:1])
        except (ValueError, IndexError):
            score = 5  # Default if parsing fails

        print(f"\n   📊 Score: {score}/10")

        if score >= 8:
            print(f"   ✅ Quality threshold met! Done.")
            break
        elif round_num < max_rounds:
            print(f"   🔄 Below threshold. Writer will revise...")
            blog_post = writer.run(
                f"Revise this blog post based on the reviewer's feedback:\n\n"
                f"ORIGINAL POST:\n{blog_post}\n\n"
                f"REVIEWER FEEDBACK:\n{review}\n\n"
                f"Write an improved version:"
            )

    return {
        "topic": topic,
        "research": research,
        "final_post": blog_post,
        "final_review": review,
        "rounds": round_num,
    }


# ============================================================
# INTERACTIVE DEMO
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("  🤖🤖🤖 MULTI-AGENT SYSTEM")
    print("=" * 60)
    print("""
This system has 3 agents working together:

  🔬 Alex (Researcher) — finds facts about a topic
  ✍️  Sam (Writer) — writes a blog post from the research
  📋 Maya (Reviewer) — reviews and improves the post

Two modes:
  1) SIMPLE  — Linear pipeline: Research → Write → Review
  2) ITERATIVE — Agents loop until quality is good enough

Example topics to try:
  • "The rise of AI agents in 2026"
  • "Why Python is still popular"
  • "Remote work pros and cons"
  • "How embeddings work in AI"
""")

    # Choose mode
    print("Mode:")
    print("  1) Simple (one pass)")
    print("  2) Iterative (revises until quality >= 8/10)")
    choice = input("\nChoice (1 or 2): ").strip()

    topic = input("\n📝 Enter a topic: ").strip()
    if not topic:
        topic = "The rise of AI agents in 2026"

    if choice == "2":
        result = run_iterative_pipeline(topic)
    else:
        result = run_content_pipeline(topic)

    # Print final output
    print("\n" + "=" * 60)
    print("  📄 FINAL OUTPUT")
    print("=" * 60)

    print(f"\n--- Research Notes ---\n{result['research']}")
    print(f"\n--- Final Post ---\n{result.get('final_post', result.get('draft', ''))}")
    print(f"\n--- Review ---\n{result.get('final_review', result.get('review', ''))}")
