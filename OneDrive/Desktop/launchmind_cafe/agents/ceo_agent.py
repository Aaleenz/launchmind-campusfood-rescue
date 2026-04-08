import os
import json
import re
import time
from dotenv import load_dotenv
from groq import Groq
from message_bus import message_bus

load_dotenv()

class CEOAgent:
    def __init__(self):
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY not found in environment variables!")
        
        self.client = Groq(api_key=api_key)
        self.startup_idea = None
        self.previous_scores = []  # Track improvement
        self.quality_tracker = {}  # Track quality per agent
    
    def extract_json(self, text: str) -> dict:
        text = re.sub(r'```json\s*', '', text)
        text = re.sub(r'```\s*', '', text)
        text = text.strip()
        
        start = text.find('{')
        end = text.rfind('}')
        
        if start != -1 and end != -1:
            json_str = text[start:end+1]
            return json.loads(json_str)
        else:
            raise ValueError(f"No JSON object found in response: {text[:200]}")
    
    def decompose_idea(self, idea: str) -> dict:
        prompt = f"""
        You are the CEO of CampusFood Rescue - a real-time notification system for leftover campus cafeteria food.
        
        Startup Idea: {idea}
        
        Create specific tasks for each agent:
        1. Product Agent: What should they define? (value prop, personas, features, user stories)
        2. Engineer Agent: What should they build? (specific HTML landing page requirements)
        3. Marketing Agent: What should they create? (tagline, email content, Slack message, social posts)
        
        Return ONLY valid JSON with this structure (no other text):
        {{
            "product_task": {{
                "focus": "specific instructions for product spec",
                "key_requirements": ["requirement1", "requirement2"]
            }},
            "engineer_task": {{
                "focus": "what the landing page must include",
                "key_elements": ["element1", "element2"]
            }},
            "marketing_task": {{
                "focus": "marketing angle and target audience",
                "channels": ["email", "slack", "social"]
            }}
        }}
        """
        
        print("   Calling Groq API...")
        response = self.client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3
        )
        
        content = response.choices[0].message.content
        print(f"   Response received, parsing JSON...")
        
        tasks = self.extract_json(content)
        return tasks
    
    def review_output(self, agent_name: str, output: dict, task_context: str, revision_attempt: int = 0, previous_score: int = None) -> tuple:
        """Review output with stricter criteria and improvement tracking"""
        
        # Track improvement status
        improvement_status = ""
        if previous_score is not None:
            if previous_score >= 8:
                improvement_status = f"\nNOTE: Previous score was {previous_score}/10. Maintain this quality."
            elif previous_score >= 6:
                improvement_status = f"\nCRITICAL: Previous score was {previous_score}/10. You MUST improve to at least 8/10."
            else:
                improvement_status = f"\nURGENT: Previous score was {previous_score}/10. This is UNACCEPTABLE. You MUST make SUBSTANTIAL improvements."
        
        prompt = f"""
        You are a STRICT CEO reviewing work from the {agent_name} agent.
        
        Task given: {task_context}
        
        Output received: {json.dumps(output, indent=2)}
        
        Revision attempt: {revision_attempt + 1}
        {improvement_status}
        
        Evaluate if this output is:
        1. Complete (all required fields present)
        2. Specific to CampusFood Rescue (not generic - must mention food waste, campus, students, cafeteria, real-time SMS)
        3. High quality and actionable (specific details, not vague statements)
        
        SCORING GUIDELINES (BE STRICT):
        - 9-10: EXCELLENT - All requirements met, specific details, actionable, shows improvement from previous attempts
        - 7-8: BORDERLINE - Missing some details, could be more specific, needs improvement
        - 5-6: POOR - Vague, missing critical elements, not specific to campus food rescue
        - 0-4: REJECT - Completely inadequate, missing major requirements
        
        MINIMUM ACCEPTABLE SCORE: 8/10
        If score is 7 or below, REJECT with specific feedback.
        If this is a revision attempt and score is not higher than previous, provide STRONGER feedback.
        
        Return ONLY valid JSON (no other text):
        {{
            "acceptable": true/false,
            "reasoning": "your detailed reasoning",
            "feedback": "specific changes needed if not acceptable (MUST include what's missing and how to fix)",
            "score": 0-10,
            "specific_missing_items": ["item1", "item2"]
        }}
        """
        
        response = self.client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3
        )
        
        content = response.choices[0].message.content
        review = self.extract_json(content)
        
        score = review.get("score", 0)
        acceptable = review.get("acceptable", False)
        
        # Stricter acceptance criteria
        MIN_ACCEPTABLE_SCORE = 8
        
        if score < MIN_ACCEPTABLE_SCORE:
            acceptable = False
            review["feedback"] = f"Score {score}/10 is below minimum {MIN_ACCEPTABLE_SCORE}/10. " + review.get("feedback", "")
        
        # Check for improvement on revision attempts
        if previous_score is not None and revision_attempt > 0:
            if score <= previous_score:
                acceptable = False
                review["feedback"] = f"⚠️ NO IMPROVEMENT! Previous score: {previous_score}/10, Current: {score}/10. " + review.get("feedback", "")
                review["feedback"] += " You MUST make SUBSTANTIAL changes, not just rephrasing. Add NEW specific details."
        
        return acceptable, review
    
    def run(self, startup_idea: str):
        print("\n" + "="*60)
        print("🚀 CEO AGENT STARTING")
        print(f"📋 Startup Idea: {startup_idea.strip()}")
        print("="*60)
        
        self.startup_idea = startup_idea
        self.previous_scores = []
        
        # Step 1: Decompose idea into tasks
        print("\n💭 CEO: Decomposing startup idea into tasks...")
        tasks = self.decompose_idea(startup_idea)
        print("   ✅ Tasks created successfully")
        
        # Step 2: Send task to Product Agent ONLY
        print("\n📤 CEO: Sending task to Product Agent...")
        
        message_bus.send("ceo", "product", "task", {
            "idea": startup_idea,
            "focus": tasks["product_task"]["focus"],
            "requirements": tasks["product_task"]["key_requirements"]
        })
        
        # Step 3: Wait for and review product spec (feedback loop)
        print("\n⏳ CEO: Waiting for Product Agent...")
        
        product_msg = None
        wait_count = 0
        while not product_msg and wait_count < 100:  # Increased timeout
            product_msg = message_bus.receive("ceo")
            if product_msg and product_msg["from_agent"] == "product":
                break
            time.sleep(0.5)  # Increased sleep
            wait_count += 1
        
        if not product_msg:
            print("\n❌ CEO: Timeout waiting for Product Agent response!")
            print("   Please check if Product Agent is running properly.")
            return {"error": "Product agent timeout"}
        
        # Review product output
        print("\n🔍 CEO: Reviewing product specification...")
        revision_attempt = 0
        previous_score = None
        acceptable, review = self.review_output(
            "product", 
            product_msg["payload"], 
            tasks["product_task"]["focus"],
            revision_attempt,
            previous_score
        )
        
        # DYNAMIC FEEDBACK LOOP - MAX 3 REVISIONS
        MAX_REVISIONS = 3
        revision_history = []
        
        while not acceptable and revision_attempt < MAX_REVISIONS:
            score = review.get('score', 0)
            print(f"\n❌ CEO: Product spec REJECTED! (Score: {score}/10)")
            print(f"   Feedback: {review['feedback'][:300]}...")
            
            revision_history.append({
                "attempt": revision_attempt + 1,
                "score": score,
                "feedback": review['feedback'],
                "improvement": score - (previous_score or 0)
            })
            
            self.previous_scores.append(score)
            previous_score = score
            
            # Send revision request to Product agent
            message_bus.send("ceo", "product", "revision_request", {
                "feedback": review["feedback"],
                "previous_output": product_msg["payload"],
                "revision_attempt": revision_attempt + 1,
                "previous_score": previous_score,
                "specific_missing_items": review.get("specific_missing_items", [])
            }, parent_message_id=product_msg["message_id"])
            
            print(f"\n📨 CEO -> PRODUCT: revision_request (Attempt {revision_attempt + 1})")
            
            # Wait for revised version with timeout
            product_msg = None
            wait_count = 0
            while not product_msg and wait_count < 50:  # 25 seconds timeout
                product_msg = message_bus.receive("ceo")
                if product_msg and product_msg["from_agent"] == "product":
                    break
                time.sleep(0.5)
                wait_count += 1
            
            if not product_msg:
                print("\n⚠️ CEO: Timeout waiting for revised product spec")
                print("   Proceeding with last received spec...")
                break
            
            revision_attempt += 1
            
            # Review revised output with previous score context
            acceptable, review = self.review_output(
                "product", 
                product_msg["payload"], 
                tasks["product_task"]["focus"],
                revision_attempt,
                previous_score
            )
        
        # Ensure product_msg is not None
        if not product_msg:
            print("\n❌ CEO: No product specification received. Aborting.")
            return {"error": "No product specification"}
        
        # Step 4: APPROVE or force approval after max revisions
        final_score = review.get('score', 0) if review else 6
        final_acceptable = acceptable or revision_attempt >= MAX_REVISIONS
        
        if final_acceptable and final_score >= 8:
            print(f"\n✅ CEO: Product spec APPROVED after {revision_attempt} revision(s)! (Final Score: {final_score}/10)")
        elif final_acceptable and final_score >= 6:
            print(f"\n⚠️ CEO: Product spec APPROVED WITH WARNINGS after {revision_attempt} revision(s) (Score: {final_score}/10)")
            print(f"   Note: Quality is below ideal but proceeding due to max revisions")
        else:
            print(f"\n⚠️ CEO: FORCING APPROVAL after {revision_attempt} revisions (Score: {final_score}/10)")
            print(f"   Warning: Quality issues persist but system will continue")
        
        # Send APPROVAL confirmation to Product agent
        message_bus.send("ceo", "product", "confirmation", {
            "approved": True,
            "final_score": final_score,
            "feedback_loop_count": revision_attempt,
            "warnings": final_score < 8
        }, parent_message_id=product_msg["message_id"])
        
        print("\n📨 CEO -> PRODUCT: APPROVAL confirmation sent")
        print("   Product will now forward spec to Engineer and Marketing")
        
        # Step 5: Wait for Engineer and Marketing results
        print("\n⏳ CEO: Waiting for Engineer and Marketing agents...")
        
        engineer_result = None
        marketing_result = None
        
        # Give agents time to process
        time.sleep(3)
        
        timeout_counter = 0
        while (not engineer_result or not marketing_result) and timeout_counter < 60:  # 30 seconds timeout
            msg = message_bus.receive("ceo")
            if msg:
                if msg["from_agent"] == "engineer" and not engineer_result:
                    engineer_result = msg["payload"]
                    print(f"\n✅ CEO: Received Engineer results - PR: {engineer_result.get('pr_url')}")
                elif msg["from_agent"] == "marketing" and not marketing_result:
                    marketing_result = msg["payload"]
                    print(f"\n✅ CEO: Received Marketing results")
            else:
                time.sleep(0.5)
                timeout_counter += 1
        
        # Check if we got results
        if not engineer_result:
            print("\n⚠️ CEO: Timeout waiting for Engineer results")
            engineer_result = {"pr_url": "https://github.com/Aaleenz/launchmind-campusfood-rescue", "error": "timeout"}
        
        if not marketing_result:
            print("\n⚠️ CEO: Timeout waiting for Marketing results")
            marketing_result = {"tagline": "Save Food, Save Money", "description": "Real-time food waste alerts"}
        
        # Step 6: Send final summary to Marketing agent for Slack posting
        print("\n📢 CEO: Sending final summary to Marketing agent for Slack...")
        time.sleep(1)
        
        slack_summary = {
            "pr_url": engineer_result.get('pr_url', 'https://github.com/Aaleenz/launchmind-campusfood-rescue'),
            "tagline": marketing_result.get('tagline', 'Never let good food go to waste'),
            "description": marketing_result.get('description', 'Real-time food waste notifications for campus')
        }
        
        print(f"📢 CEO: Sending confirmation with PR URL: {slack_summary['pr_url']}")
        message_bus.send("ceo", "marketing", "confirmation", slack_summary)
        
        # Wait for Marketing to confirm Slack post
        print("\n⏳ CEO: Waiting for Marketing to confirm Slack post...")
        slack_confirmation = None
        timeout = 30
        start_time = time.time()
        
        while not slack_confirmation and (time.time() - start_time) < timeout:
            msg = message_bus.receive("ceo")
            if msg and msg["from_agent"] == "marketing":
                slack_confirmation = msg["payload"]
                print(f"\n✅ CEO: Marketing confirmed - Slack posted: {slack_confirmation.get('slack_posted', False)}")
                break
            time.sleep(0.5)
        
        # Print quality summary
        print("\n" + "="*60)
        print("📊 DYNAMIC FEEDBACK LOOP SUMMARY:")
        print(f"   • Total revision attempts: {revision_attempt}")
        print(f"   • Final score: {final_score}/10")
        print(f"   • Final status: {'APPROVED' if final_score >= 8 else 'APPROVED WITH WARNINGS'}")
        
        if revision_history:
            print("\n   Revision History:")
            for rev in revision_history:
                improvement_indicator = f"(+{rev['improvement']})" if rev['improvement'] > 0 else "(NO IMPROVEMENT)" if rev['improvement'] == 0 else f"({rev['improvement']})"
                print(f"   • Attempt {rev['attempt']}: Score {rev['score']}/10 {improvement_indicator}")
        
        # Check if improvement occurred
        if len(self.previous_scores) >= 2:
            if self.previous_scores[-1] > self.previous_scores[0]:
                print(f"\n   ✅ Score IMPROVED from {self.previous_scores[0]} to {self.previous_scores[-1]}")
            else:
                print(f"\n   ⚠️ Score did NOT improve significantly")
        
        print("="*60)
        print("✅ CEO AGENT COMPLETE")
        print("="*60)
        
        return {
            "product_spec": product_msg["payload"],
            "engineer_result": engineer_result,
            "marketing_result": marketing_result,
            "feedback_loop_executed": revision_attempt > 0,
            "revision_history": revision_history,
            "final_score": final_score
        }