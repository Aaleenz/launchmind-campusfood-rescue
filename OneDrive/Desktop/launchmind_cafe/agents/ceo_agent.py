import os
import json
import re
import time
import uuid
from datetime import datetime
from dotenv import load_dotenv
from groq import Groq
from groq import RateLimitError
from message_bus import message_bus

load_dotenv()

class CEOAgent:
    def __init__(self):
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY not found in environment variables!")
        
        self.client = Groq(api_key=api_key)
        self.startup_idea = None
        self.previous_scores = []
        self.quality_tracker = {}
        self.revision_count = 0
        self.current_message_id = None
    
    def call_llm_with_retry(self, prompt: str, max_retries: int = 5) -> str:
        """Call Groq API with exponential backoff for rate limits"""
        for attempt in range(max_retries):
            try:
                response = self.client.chat.completions.create(
                    model="llama-3.1-8b-instant",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.3,
                    max_tokens=2000
                )
                return response.choices[0].message.content
            except RateLimitError as e:
                wait_time = 10
                error_msg = str(e)
                import re
                match = re.search(r"try again in ([\d.]+)s", error_msg)
                if match:
                    wait_time = float(match.group(1)) + 1
                
                print(f"   ⚠️ Rate limit hit (attempt {attempt+1}/{max_retries}), waiting {wait_time}s...")
                time.sleep(wait_time)
            except Exception as e:
                print(f"   ⚠️ API error (attempt {attempt+1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(3)
                else:
                    raise e
        
        raise Exception(f"Failed after {max_retries} retries")
    
    def extract_json(self, text: str) -> dict:
        """Extract JSON from text with better error handling"""
        # Remove markdown code blocks
        text = re.sub(r'```json\s*', '', text)
        text = re.sub(r'```\s*', '', text)
        text = text.strip()
        
        # Remove control characters (except newlines and tabs)
        text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)
        
        # Try to find JSON object
        start = text.find('{')
        end = text.rfind('}')
        
        if start != -1 and end != -1:
            json_str = text[start:end+1]
            try:
                return json.loads(json_str)
            except json.JSONDecodeError as e:
                print(f"   ⚠️ JSON decode error: {e}")
                # Try to fix common JSON issues
                json_str = re.sub(r',\s*}', '}', json_str)
                json_str = re.sub(r',\s*]', ']', json_str)
                # Fix unescaped quotes
                json_str = re.sub(r'(?<!\\)"', '\\"', json_str)
                json_str = re.sub(r'\\"([^"]*)\\"', r'"\1"', json_str)
                try:
                    return json.loads(json_str)
                except:
                    # If still failing, try to extract with regex patterns
                    return self.extract_json_fallback(text)
        else:
            raise ValueError(f"No JSON object found in response: {text[:200]}")
    
    def extract_json_fallback(self, text: str) -> dict:
        """Fallback method to extract JSON using regex patterns"""
        result = {}
        
        # Try to extract key-value pairs
        patterns = {
            "acceptable": r'"acceptable":\s*(true|false)',
            "score": r'"score":\s*(\d+)',
            "reasoning": r'"reasoning":\s*"([^"]+)"',
            "feedback": r'"feedback":\s*"([^"]+)"'
        }
        
        for key, pattern in patterns.items():
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                if key == "acceptable":
                    result[key] = match.group(1).lower() == "true"
                elif key == "score":
                    result[key] = int(match.group(1))
                else:
                    result[key] = match.group(1)
        
        # Set defaults if missing
        if "acceptable" not in result:
            result["acceptable"] = False
        if "score" not in result:
            result["score"] = 5
        if "reasoning" not in result:
            result["reasoning"] = "Failed to parse JSON response"
        if "feedback" not in result:
            result["feedback"] = "Please improve the quality of your output"
        if "specific_missing_items" not in result:
            result["specific_missing_items"] = []
        
        return result
    
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
        content = self.call_llm_with_retry(prompt)
        print(f"   Response received, parsing JSON...")
        
        tasks = self.extract_json(content)
        return tasks
    
    def review_output(self, agent_name: str, output: dict, task_context: str, revision_attempt: int = 0, previous_score: int = None) -> tuple:
        """Review output with stricter criteria and improvement tracking"""
        
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
        
        Return ONLY valid JSON (no other text, no control characters, no markdown):
        {{
            "acceptable": true/false,
            "reasoning": "your detailed reasoning",
            "feedback": "specific changes needed if not acceptable (MUST include what's missing and how to fix)",
            "score": 0-10,
            "specific_missing_items": ["item1", "item2"]
        }}
        """
        
        content = self.call_llm_with_retry(prompt)
        review = self.extract_json(content)
        
        score = review.get("score", 0)
        acceptable = review.get("acceptable", False)
        
        MIN_ACCEPTABLE_SCORE = 8
        
        if score < MIN_ACCEPTABLE_SCORE:
            acceptable = False
            review["feedback"] = f"Score {score}/10 is below minimum {MIN_ACCEPTABLE_SCORE}/10. " + review.get("feedback", "")
        
        if previous_score is not None and revision_attempt > 0:
            if score <= previous_score:
                acceptable = False
                review["feedback"] = f"⚠️ NO IMPROVEMENT! Previous score: {previous_score}/10, Current: {score}/10. " + review.get("feedback", "")
                review["feedback"] += " You MUST make SUBSTANTIAL changes, not just rephrasing. Add NEW specific details."
        
        return acceptable, review
    
    def handle_qa_review(self, review_report: dict, revision_count: int, max_qa_iterations: int) -> tuple:
        """Process QA review and decide next steps"""
        
        verdict = review_report.get("verdict", "FAIL")
        overall_score = review_report.get("overall_score", 0)
        
        print(f"\n📊 CEO: Received QA review - {verdict} ({overall_score}/10)")
        
        if verdict == "PASS":
            print(f"✅ CEO: QA passed! Quality check complete.")
            return True, review_report
        else:
            print(f"❌ CEO: QA failed! Need revisions.")
            
            html_issues = review_report.get("html_review", {}).get("issues", [])
            marketing_issues = review_report.get("marketing_review", {}).get("issues", [])
            recommendations = review_report.get("html_review", {}).get("recommendations", []) + \
                             review_report.get("marketing_review", {}).get("recommendations", [])
            
            if html_issues and revision_count < max_qa_iterations - 1:
                self.send_revision_to_engineer(html_issues, recommendations, revision_count)
            
            if marketing_issues and revision_count < max_qa_iterations - 1:
                self.send_revision_to_marketing(marketing_issues, recommendations, revision_count)
            
            return False, review_report
    
    def send_revision_to_engineer(self, issues: list, recommendations: list, revision_round: int):
        """Send revision request to Engineer agent"""
        
        revision_message = {
            "message_id": str(uuid.uuid4()),
            "from_agent": "ceo",
            "to_agent": "engineer",
            "message_type": "revision_request",
            "payload": {
                "issues": issues,
                "recommendations": recommendations,
                "feedback": f"QA review failed. Please fix these issues: {', '.join(issues)}",
                "revision_round": revision_round + 1
            },
            "timestamp": datetime.now().isoformat(),
            "parent_message_id": self.current_message_id
        }
        
        message_bus.send_dict(revision_message)
        print(f"📨 CEO -> ENGINEER: Revision request sent (Round {revision_round + 1})")
    
    def send_revision_to_marketing(self, issues: list, recommendations: list, revision_round: int):
        """Send revision request to Marketing agent"""
        
        revision_message = {
            "message_id": str(uuid.uuid4()),
            "from_agent": "ceo",
            "to_agent": "marketing",
            "message_type": "revision_request",
            "payload": {
                "issues": issues,
                "recommendations": recommendations,
                "feedback": f"QA review failed. Please fix these issues: {', '.join(issues)}",
                "revision_round": revision_round + 1
            },
            "timestamp": datetime.now().isoformat(),
            "parent_message_id": self.current_message_id
        }
        
        message_bus.send_dict(revision_message)
        print(f"📨 CEO -> MARKETING: Revision request sent (Round {revision_round + 1})")
    
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
        while not product_msg and wait_count < 100:
            product_msg = message_bus.receive("ceo")
            if product_msg and product_msg["from_agent"] == "product":
                break
            time.sleep(0.5)
            wait_count += 1
        
        if not product_msg:
            print("\n❌ CEO: Timeout waiting for Product Agent response!")
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
            while not product_msg and wait_count < 50:
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
            try:
                acceptable, review = self.review_output(
                    "product", 
                    product_msg["payload"], 
                    tasks["product_task"]["focus"],
                    revision_attempt,
                    previous_score
                )
            except Exception as e:
                print(f"\n⚠️ CEO: Review failed: {e}")
                print("   Accepting product spec to continue...")
                acceptable = True
                review = {"score": 6, "feedback": "Review failed, accepting spec"}
        
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
        
        time.sleep(5)
        
        timeout_counter = 0
        max_wait = 60
        
        while (not engineer_result or not marketing_result) and timeout_counter < max_wait:
            msg = message_bus.receive("ceo")
            if msg:
                if msg["from_agent"] == "engineer" and msg["message_type"] == "result" and not engineer_result:
                    engineer_result = msg["payload"]
                    print(f"\n✅ CEO: Received Engineer results - PR: {engineer_result.get('pr_url', 'N/A')}")
                    print(f"   HTML content length: {len(engineer_result.get('html_content', ''))} chars")
                elif msg["from_agent"] == "marketing" and msg["message_type"] == "result" and not marketing_result:
                    marketing_result = msg["payload"]
                    print(f"\n✅ CEO: Received Marketing results - Tagline: {marketing_result.get('tagline', 'N/A')}")
            else:
                time.sleep(1)
                timeout_counter += 1
                if timeout_counter % 10 == 0:
                    print(f"   ⏳ Still waiting... ({timeout_counter}s)")
        
        # Fallbacks
        if not engineer_result:
            print("\n⚠️ CEO: Timeout waiting for Engineer results - using fallback")
            engineer_result = {
                "pr_url": "https://github.com/Aaleenz/launchmind-campusfood-rescue",
                "html_content": "<html><body><h1>CampusFood Rescue</h1><p>Real-time food waste alerts</p></body></html>",
                "status": "fallback"
            }
        
        if not marketing_result:
            print("\n⚠️ CEO: Timeout waiting for Marketing results - using fallback")
            marketing_result = {
                "tagline": "Save Food, Save Money on Campus!",
                "description": "Real-time SMS alerts for leftover cafeteria food at discounted prices.",
                "social_posts": ["Post 1", "Post 2", "Post 3"]
            }
        
        # QA REVIEW CYCLE
        print("\n" + "="*60)
        print("🔍 INITIATING QA REVIEW CYCLE")
        print("="*60)
        
        MAX_QA_ITERATIONS = 3
        qa_iteration = 0
        qa_passed = False
        qa_results = None
        all_qa_history = []
        
        current_engineer_result = engineer_result
        current_marketing_result = marketing_result
        
        while not qa_passed and qa_iteration < MAX_QA_ITERATIONS:
            qa_iteration += 1
            print(f"\n🔄 QA Iteration {qa_iteration}/{MAX_QA_ITERATIONS}")
            
            review_task_id = str(uuid.uuid4())
            self.current_message_id = review_task_id
            
            message_bus.send("ceo", "qa", "review_task", {
                "html_content": current_engineer_result.get("html_content", ""),
                "marketing_copy": current_marketing_result,
                "product_spec": product_msg["payload"],
                "pr_url": current_engineer_result.get("pr_url", ""),
                "repo_name": os.getenv("GITHUB_REPO", "Aaleenz/launchmind-campusfood-rescue"),
                "pr_number": current_engineer_result.get("pr_number", ""),
                "qa_iteration": qa_iteration
            }, parent_message_id=review_task_id)
            
            print(f"📨 CEO -> QA: Review task sent (Iteration {qa_iteration})")
            
            qa_report = None
            wait_time = 0
            while not qa_report and wait_time < 45:
                msg = message_bus.receive("ceo")
                if msg and msg["from_agent"] == "qa" and msg["message_type"] == "review_report":
                    qa_report = msg["payload"]
                    break
                time.sleep(1)
                wait_time += 1
            
            if not qa_report:
                print("\n⚠️ CEO: Timeout waiting for QA report")
                print("   Proceeding without QA validation...")
                break
            
            all_qa_history.append({
                "iteration": qa_iteration,
                "verdict": qa_report.get("verdict"),
                "overall_score": qa_report.get("overall_score"),
                "html_score": qa_report.get("html_review", {}).get("score"),
                "marketing_score": qa_report.get("marketing_review", {}).get("score")
            })
            
            qa_passed, qa_results = self.handle_qa_review(qa_report, qa_iteration, MAX_QA_ITERATIONS)
            
            if qa_passed:
                print(f"\n✅ QA PASSED after {qa_iteration} iteration(s)!")
                break
            else:
                print(f"\n❌ QA FAILED - Waiting for revised outputs...")
                time.sleep(5)
                
                revised_engineer = None
                revised_marketing = None
                
                wait_counter = 0
                while (not revised_engineer or not revised_marketing) and wait_counter < 30:
                    msg = message_bus.receive("ceo")
                    if msg:
                        if msg["from_agent"] == "engineer" and msg["message_type"] == "result" and not revised_engineer:
                            revised_engineer = msg["payload"]
                            print(f"   ✅ Received revised Engineer output")
                        elif msg["from_agent"] == "marketing" and msg["message_type"] == "result" and not revised_marketing:
                            revised_marketing = msg["payload"]
                            print(f"   ✅ Received revised Marketing output")
                    else:
                        time.sleep(0.5)
                        wait_counter += 1
                
                if revised_engineer:
                    current_engineer_result = revised_engineer
                if revised_marketing:
                    current_marketing_result = revised_marketing
                
                if qa_iteration >= MAX_QA_ITERATIONS:
                    print(f"\n⚠️ Max QA iterations ({MAX_QA_ITERATIONS}) reached. Proceeding with current state.")
        
        print("\n" + "="*60)
        print("📊 QA SUMMARY:")
        print(f"   • QA iterations completed: {qa_iteration}")
        print(f"   • Final verdict: {'PASSED' if qa_passed else 'MAX ITERATIONS REACHED'}")
        if qa_results:
            print(f"   • Final overall score: {qa_results.get('overall_score', 'N/A')}/10")
        
        if all_qa_history:
            print("\n   QA Iteration History:")
            for hist in all_qa_history:
                print(f"   • Iteration {hist['iteration']}: {hist['verdict']} (Score: {hist['overall_score']}/10)")
        
        print("="*60)
        
        # Send final summary to Marketing
        print("\n📢 CEO: Sending final summary to Marketing agent for Slack...")
        time.sleep(1)
        
        slack_summary = {
            "pr_url": current_engineer_result.get('pr_url', 'https://github.com/Aaleenz/launchmind-campusfood-rescue'),
            "tagline": current_marketing_result.get('tagline', 'Never let good food go to waste'),
            "description": current_marketing_result.get('description', 'Real-time food waste notifications for campus'),
            "qa_passed": qa_passed,
            "qa_score": qa_results.get('overall_score', 0) if qa_results else 0
        }
        
        print(f"📢 CEO: Sending confirmation with PR URL: {slack_summary['pr_url']}")
        message_bus.send("ceo", "marketing", "confirmation", slack_summary)
        
        print("\n⏳ CEO: Waiting for Marketing to confirm Slack post...")
        slack_confirmation = None
        timeout = 30
        start_time = time.time()
        
        while not slack_confirmation and (time.time() - start_time) < timeout:
            msg = message_bus.receive("ceo")
            if msg and msg["from_agent"] == "marketing" and msg["message_type"] == "confirmation":
                slack_confirmation = msg["payload"]
                print(f"\n✅ CEO: Marketing confirmed - Slack posted: {slack_confirmation.get('slack_posted', False)}")
                break
            time.sleep(0.5)
        
        print("\n" + "="*60)
        print("📊 DYNAMIC FEEDBACK LOOP SUMMARY:")
        print(f"   • Product spec revision attempts: {revision_attempt}")
        print(f"   • Product spec final score: {final_score}/10")
        print(f"   • QA iterations: {qa_iteration}")
        print(f"   • QA final verdict: {'PASSED' if qa_passed else 'MAX ITERATIONS'}")
        
        if revision_history:
            print("\n   Product Revision History:")
            for rev in revision_history:
                improvement_indicator = f"(+{rev['improvement']})" if rev['improvement'] > 0 else "(NO IMPROVEMENT)" if rev['improvement'] == 0 else f"({rev['improvement']})"
                print(f"   • Attempt {rev['attempt']}: Score {rev['score']}/10 {improvement_indicator}")
        
        if all_qa_history:
            print("\n   QA Revision History:")
            for hist in all_qa_history:
                print(f"   • Iteration {hist['iteration']}: {hist['verdict']} (Score: {hist['overall_score']}/10)")
        
        if len(self.previous_scores) >= 2:
            if self.previous_scores[-1] > self.previous_scores[0]:
                print(f"\n   ✅ Product score IMPROVED from {self.previous_scores[0]} to {self.previous_scores[-1]}")
            else:
                print(f"\n   ⚠️ Product score did NOT improve significantly")
        
        print("="*60)
        print("✅ CEO AGENT COMPLETE")
        print("="*60)
        
        return {
            "product_spec": product_msg["payload"],
            "engineer_result": current_engineer_result,
            "marketing_result": current_marketing_result,
            "qa_results": {
                "verdict": "PASSED" if qa_passed else "MAX_ITERATIONS",
                "overall_score": qa_results.get('overall_score', 0) if qa_results else 0,
                "qa_iterations": qa_iteration,
                "history": all_qa_history
            },
            "feedback_loop_executed": revision_attempt > 0,
            "revision_history": revision_history,
            "final_score": final_score
        }