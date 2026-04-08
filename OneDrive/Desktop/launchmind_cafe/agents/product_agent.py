import os
import json
import re
import time
from groq import Groq
from message_bus import message_bus

class ProductAgent:
    def __init__(self):
        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY not found in environment variables!")
        self.client = Groq(api_key=api_key)
        self.pending_spec = None
        self.improvement_log = []  # Track improvements
        self.previous_specs = []   # Store previous specs for comparison
        self.revision_count = 0
        self.current_idea = None
        self.current_focus = None
        self.current_requirements = None
    
    def extract_json(self, text: str) -> dict:
        """Extract JSON from text that might have markdown formatting"""
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
    
    def generate_product_spec(self, idea: str, focus: str, requirements: list, revision_feedback: str = None, previous_score: int = None, specific_missing: list = None) -> dict:
        """Generate product spec with explicit improvement requirements"""
        
        revision_instruction = ""
        if revision_feedback:
            # Parse feedback to extract explicit requirements
            missing_items_text = ""
            if specific_missing:
                missing_items_text = "\n   SPECIFIC MISSING ITEMS FROM PREVIOUS REJECTION:\n" + "\n".join([f"   - {item}" for item in specific_missing])
            
            revision_instruction = f"""
            ⚠️ CRITICAL - REVISION REQUEST (Attempt {self.revision_count + 1})
            Previous version was REJECTED with score {previous_score}/10.
            
            FEEDBACK FROM CEO:
            {revision_feedback}
            {missing_items_text}
            
            IMPROVEMENTS REQUIRED:
            1. You MUST increase the score to at least 8/10 (from {previous_score}/10)
            2. Address EVERY point in the feedback above
            3. Add NEW, SPECIFIC details that were missing before
            4. DO NOT just rephrase the same content - add substantive new information
            
            SPECIFIC IMPROVEMENTS TO MAKE:
            - Add technical implementation details (how real-time SMS works, which SMS gateway)
            - Include specific metrics (e.g., "reduce waste by 30%", "save students Rs. 500/month")
            - Make user stories testable with acceptance criteria
            - Add more specific campus-related details (Pakistani university context)
            - Specify exact time frames (e.g., "notifications sent within 30 seconds")
            """
        
        prompt = f"""
        Create a HIGH-QUALITY, DETAILED product specification for CampusFood Rescue.
        
        Startup Idea: {idea}
        Focus: {focus}
        Requirements: {requirements}
        {revision_instruction}
        
        CRITICAL REQUIREMENTS (score will be low if missing):
        1. Personas MUST have REAL Pakistani student names (e.g., "Hungry Hamza", "Budget Bilal", "Frugal Fatima")
        2. Features MUST mention real-time/SMS/notifications specifically with technical details
        3. User stories MUST follow exact format: "As a [user], I want to [action] so that [benefit]"
        4. Value proposition MUST mention both "students" and "cafeteria" with specific benefit
        5. Add acceptance criteria for each user story (how to verify it works)
        6. Include specific metrics and KPIs
        
        Return ONLY valid JSON with exactly this structure (no other text, no markdown):
        {{
            "value_proposition": "one sentence describing what the product does and for whom with specific benefit",
            "personas": [
                {{"name": "Real Pakistani Student Name", "role": "student", "pain_point": "specific pain point with campus context"}},
                {{"name": "Real Manager Name", "role": "cafeteria manager", "pain_point": "specific pain point with waste metrics"}}
            ],
            "features": [
                {{"name": "Real-time SMS Alerts", "description": "technical description including SMS gateway, real-time push, location-based filtering, 30-second delivery SLA", "priority": 1}},
                {{"name": "Discounted Food Listings", "description": "description with pricing strategy (30-50% discount)", "priority": 2}},
                {{"name": "Waste Reduction Analytics", "description": "description with specific metrics (track 40% waste reduction, Rs. 50,000 saved monthly)", "priority": 3}},
                {{"name": "Student Preference Profiles", "description": "description of customization options (food types, price range, distance)", "priority": 4}},
                {{"name": "Manager Dashboard", "description": "description of analytics and controls (real-time waste tracking, revenue reports)", "priority": 5}}
            ],
            "user_stories": [
                "As a hungry student, I want to receive SMS alerts within 30 seconds when food is available so that I can save money on meals",
                "As a cafeteria manager, I want to post leftover food deals so that I can reduce waste by 30%",
                "As a student, I want to see discounted food options sorted by distance so that I can eat affordably"
            ],
            "acceptance_criteria": {{
                "story_1": "Given a student is registered, when food becomes available, then they receive SMS within 30 seconds",
                "story_2": "Given a manager has leftover food, when they post a deal, then it appears in student feeds immediately",
                "story_3": "Given a student opens the app, when they view options, then they see discounted items sorted by distance"
            }},
            "success_metrics": [
                "Reduce campus food waste by 40% within 6 months",
                "Save average student Rs. 2,000 per semester",
                "Onboard 10 cafeteria managers in first month",
                "Achieve 95% SMS delivery rate within 30 seconds"
            ]
        }}
        
        Make it VERY SPECIFIC to a Pakistani campus food rescue system with real-time notifications.
        Be creative, realistic, and detailed. Include technical implementation hints.
        """
        
        print("   📋 PRODUCT: Calling Groq API for product spec...")
        
        try:
            response = self.client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7 if revision_feedback else 0.5,
                timeout=30  # Add timeout
            )
            
            content = response.choices[0].message.content
            print(f"   📋 PRODUCT: Received response, extracting JSON...")
            
            spec = self.extract_json(content)
            print(f"   📋 PRODUCT: Successfully parsed product spec")
            
            if revision_feedback:
                spec["_revised"] = True
                spec["_revision_attempt"] = self.revision_count + 1
                spec["_improvements_made"] = "Added technical details, metrics, and acceptance criteria based on feedback"
                
                # Log improvement
                self.improvement_log.append({
                    "attempt": self.revision_count + 1,
                    "feedback_used": revision_feedback[:200],
                    "changes_made": "Added technical implementation details, success metrics, acceptance criteria"
                })
            
            return spec
            
        except Exception as e:
            print(f"   ❌ PRODUCT: API error: {e}")
            # Return a fallback spec
            return {
                "value_proposition": "CampusFood Rescue connects students with discounted campus cafeteria food, reducing waste and saving students money through real-time SMS alerts.",
                "personas": [
                    {"name": "Hungry Hamza", "role": "student", "pain_point": "Spends too much on food, wants affordable meals"},
                    {"name": "Manager Mahmood", "role": "cafeteria manager", "pain_point": "40% of food goes to waste daily"}
                ],
                "features": [
                    {"name": "Real-time SMS Alerts", "description": "Get SMS within 30 seconds when food is available", "priority": 1},
                    {"name": "Discounted Food Listings", "description": "See discounted food (30-50% off)", "priority": 2},
                    {"name": "Waste Analytics Dashboard", "description": "Track waste reduction metrics", "priority": 3},
                    {"name": "Student Preferences", "description": "Customize food type alerts", "priority": 4},
                    {"name": "Manager Controls", "description": "Post deals and track inventory", "priority": 5}
                ],
                "user_stories": [
                    "As a student, I want SMS alerts so that I save money",
                    "As a manager, I want to post deals so that I reduce waste",
                    "As a student, I want to browse deals so that I find affordable food"
                ],
                "acceptance_criteria": {
                    "story_1": "SMS sent within 30 seconds of food becoming available",
                    "story_2": "Deal appears immediately in student feeds",
                    "story_3": "Deals sorted by distance from student"
                },
                "success_metrics": [
                    "Reduce waste by 40%",
                    "Save students Rs. 2,000/semester",
                    "Onboard 10 managers in first month"
                ]
            }
    
    def run(self):
        print("\n📋 PRODUCT AGENT: Waiting for CEO task...")
        
        while True:
            msg = message_bus.receive("product")
            
            if not msg:
                time.sleep(0.5)
                continue
            
            if msg["message_type"] == "task":
                print(f"\n📋 PRODUCT AGENT: Received task from CEO")
                
                payload = msg["payload"]
                print(f"   Idea: {payload['idea'][:100]}...")
                print(f"   Focus: {payload['focus']}")
                
                # Store for revisions
                self.current_idea = payload["idea"]
                self.current_focus = payload["focus"]
                self.current_requirements = payload["requirements"]
                self.revision_count = 0
                
                # Generate product spec (first attempt)
                spec = self.generate_product_spec(
                    payload["idea"],
                    payload["focus"],
                    payload["requirements"],
                    revision_feedback=None,
                    previous_score=None
                )
                
                # Store as pending
                self.pending_spec = spec
                self.previous_specs.append(spec)
                
                # ONLY send back to CEO for approval
                message_bus.send("product", "ceo", "result", spec, msg["message_id"])
                print(f"📋 PRODUCT AGENT: Sent product spec to CEO for approval (waiting...)")
                print(f"   ⚠️ NOT forwarding to Engineer/Marketing until CEO approves")
                
            elif msg["message_type"] == "revision_request":
                self.revision_count += 1
                print(f"\n📋 PRODUCT AGENT: Received REVISION REQUEST #{self.revision_count}")
                print(f"   Feedback: {msg['payload'].get('feedback', '')[:200]}...")
                print(f"   Previous score: {msg['payload'].get('previous_score', 'N/A')}")
                
                # Generate REVISED product spec with improvement focus
                revised_spec = self.generate_product_spec(
                    self.current_idea,
                    f"IMPROVE based on CEO feedback (Attempt {self.revision_count}): {msg['payload'].get('feedback', '')[:100]}",
                    self.current_requirements,
                    revision_feedback=msg["payload"].get("feedback", ""),
                    previous_score=msg["payload"].get("previous_score"),
                    specific_missing=msg["payload"].get("specific_missing_items", [])
                )
                
                # Store as pending
                self.pending_spec = revised_spec
                self.previous_specs.append(revised_spec)
                
                # Send revised spec back to CEO for approval
                message_bus.send("product", "ceo", "result", revised_spec, msg["message_id"])
                print(f"📋 PRODUCT AGENT: Sent REVISED product spec (v{self.revision_count}) to CEO for approval")
                print(f"   ⚠️ STILL waiting for CEO approval before forwarding")
            
            elif msg["message_type"] == "confirmation" and msg["payload"].get("approved"):
                # CEO confirms the spec is approved - NOW forward to Engineer & Marketing
                print(f"\n📋 PRODUCT AGENT: Received APPROVAL from CEO!")
                print(f"   Final score: {msg['payload'].get('final_score', 'N/A')}")
                print(f"   Revision count: {self.revision_count}")
                print(f"   Forwarding approved spec to Engineer and Marketing...")
                
                approved_spec = self.pending_spec
                
                # Add quality metadata
                approved_spec["_quality_metadata"] = {
                    "revision_count": self.revision_count,
                    "final_score": msg["payload"].get("final_score"),
                    "improvement_log": self.improvement_log
                }
                
                message_bus.send("product", "engineer", "task", {
                    "product_spec": approved_spec,
                    "action": "build_landing_page"
                })
                
                message_bus.send("product", "marketing", "task", {
                    "product_spec": approved_spec,
                    "action": "create_marketing_materials"
                })
                
                print(f"📋 PRODUCT AGENT: Forwarded APPROVED spec to Engineer and Marketing")
                print(f"   Value Prop: {approved_spec.get('value_proposition', 'N/A')[:50]}...")
                print(f"   Features: {len(approved_spec.get('features', []))} defined")
                print(f"   Success Metrics: {len(approved_spec.get('success_metrics', []))} defined")
                
                # Print improvement summary
                if self.improvement_log:
                    print(f"\n   📈 Improvement Summary:")
                    for log in self.improvement_log:
                        print(f"      Attempt {log['attempt']}: {log['changes_made'][:60]}...")
                
                # Exit after successful forwarding
                break